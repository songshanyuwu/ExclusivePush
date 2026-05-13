# -*- coding: utf-8 -*-
"""
新闻联播文字稿抓取与推送 - 优化版
功能：异步并发抓取、自动目录、视频链接、美化显示、完整错误处理
注意：所有样式使用内联样式，确保 PushPlus 正常显示
"""

import asyncio
import aiohttp
import logging
import os
import time
import json
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from html import escape
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# ==================== 配置 ====================

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

PUSHPLUSSCKEY = os.environ.get('PUSHPLUSSCKEY')

# 请求配置
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://tv.cctv.com/lm/xwlb/",
    "Accept": "text/html, */*; q=0.01"
}

TIMEOUT = aiohttp.ClientTimeout(total=30)  # 总超时30秒
MAX_CONCURRENT = 5  # 最大并发数
RETRY_TIMES = 3  # 重试次数

# ==================== 内联样式定义 ====================

STYLE_CONTAINER = '''
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
line-height: 1.8;
color: #333;
max-width: 100%;
word-wrap: break-word;
'''.strip()

STYLE_TOC = '''
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
color: white;
padding: 20px;
border-radius: 12px;
margin-bottom: 20px;
'''.strip()

STYLE_TOC_TITLE = '''
font-size: 18px;
font-weight: bold;
margin-bottom: 12px;
'''.strip()

STYLE_TOC_LIST = '''
columns: 2;
column-gap: 20px;
'''.strip()

STYLE_TOC_ITEM = '''
break-inside: avoid;
padding: 6px 0;
font-size: 14px;
'''.strip()

STYLE_NEWS_ITEM = '''
background: #f8f9fa;
border-radius: 10px;
padding: 16px 20px;
margin-bottom: 16px;
border-left: 4px solid #667eea;
'''.strip()

STYLE_NEWS_TITLE = '''
font-size: 16px;
font-weight: bold;
color: #1a1a1a;
margin-bottom: 12px;
display: flex;
align-items: flex-start;
gap: 8px;
flex-wrap: wrap;
'''.strip()

STYLE_NEWS_INDEX = '''
background: #667eea;
color: white;
min-width: 28px;
height: 24px;
border-radius: 50%;
display: inline-flex;
align-items: center;
justify-content: center;
font-size: 12px;
flex-shrink: 0;
padding: 0 4px;
'''.strip()

STYLE_VIDEO_LINK = '''
background: #ff4757;
color: white;
padding: 4px 12px;
border-radius: 20px;
font-size: 12px;
font-weight: normal;
text-decoration: none;
margin-left: auto;
flex-shrink: 0;
'''.strip()

STYLE_NEWS_CONTENT = '''
color: #555;
font-size: 14px;
line-height: 2;
'''.strip()

# ==================== 数据结构 ====================

@dataclass
class NewsItem:
    """单条新闻数据结构"""
    title: str
    content: str
    video_url: str
    index: int = 0  # 目录索引

    def to_html(self) -> str:
        """转换为HTML格式（使用内联样式）"""
        return f'''
<div style="{STYLE_NEWS_ITEM}">
    <div style="{STYLE_NEWS_TITLE}">
        <span style="{STYLE_NEWS_INDEX}">{self.index}️⃣</span>
        <b>{escape(self.title)}</b>
        <a href="{escape(self.video_url)}" style="{STYLE_VIDEO_LINK}" target="_blank">🎬 视频</a>
    </div>
    <div style="{STYLE_NEWS_CONTENT}">{self.content}</div>
</div>
        '''.strip()


@dataclass
class NewsList:
    """新闻列表，管理多条新闻"""
    items: List[NewsItem] = field(default_factory=list)
    date: str = ""

    def to_html(self) -> str:
        """生成完整HTML，包含目录和正文"""
        if not self.items:
            return "<p>暂无新闻内容</p>"

        # 生成目录
        toc = self._generate_toc()
        # 生成正文
        content = self._generate_content()

        return f'''
<div style="{STYLE_CONTAINER}">
    <div style="{STYLE_TOC}">
        <div style="{STYLE_TOC_TITLE}">📋 今日目录（共{len(self.items)}条）</div>
        <div style="{STYLE_TOC_LIST}">
            {toc}
        </div>
    </div>
    {content}
</div>
        '''.strip()

    def _generate_toc(self) -> str:
        """生成目录HTML"""
        toc_items = []
        for item in self.items:
            toc_items.append(f'<div style="{STYLE_TOC_ITEM}">{item.index}️⃣ {escape(item.title)}</div>')
        return '\n'.join(toc_items)

    def _generate_content(self) -> str:
        """生成正文HTML"""
        return '\n'.join([item.to_html() for item in self.items])


# ==================== 工具函数 ====================

async def fetch_url(session: aiohttp.ClientSession, url: str, semaphore: asyncio.Semaphore) -> Optional[str]:
    """异步获取URL内容，带并发控制"""
    async with semaphore:
        try:
            async with session.get(url, headers=HEADERS) as response:
                if response.status == 200:
                    # 自动检测编码
                    content = await response.read()
                    # 尝试多种编码
                    for encoding in ['utf-8', 'gbk', 'gb2312', 'gb18030']:
                        try:
                            return content.decode(encoding)
                        except UnicodeDecodeError:
                            continue
                    # 最后尝试 ignore
                    return content.decode('utf-8', errors='ignore')
                else:
                    logger.warning(f"请求失败 [{response.status}]: {url}")
                    return None
        except asyncio.TimeoutError:
            logger.warning(f"请求超时: {url}")
            return None
        except Exception as e:
            logger.error(f"请求异常: {url}, 错误: {e}")
            return None


def parse_list_page(html: str) -> List[Dict[str, str]]:
    """解析新闻列表页"""
    from lxml import etree
    try:
        etr = etree.HTML(html)
        titles = etr.xpath("//li/a/@title")
        hrefs = etr.xpath("//li/a/@href")

        news_list = []
        for title, href in zip(titles, hrefs):
            if title and href:
                # 处理相对链接
                if href.startswith('/'):
                    href = 'https://tv.cctv.com' + href
                news_list.append({'title': title.strip(), 'href': href})

        logger.info(f"解析到 {len(news_list)} 条新闻标题")
        return news_list
    except Exception as e:
        logger.error(f"解析列表页失败: {e}")
        return []


def parse_content_page(html: str) -> str:
    """解析新闻内容页"""
    from lxml import etree
    try:
        etr = etree.HTML(html)
        div_elements = etr.xpath('//div[@id="content_area"]/p')

        if not div_elements:
            logger.warning("未找到 content_area 元素")
            return "⚠️ 内容获取失败"

        result = []
        for div_element in div_elements:
            strong_elements = div_element.xpath('strong/text()')
            p_elements = div_element.xpath('text()')

            # 处理 strong 元素（加粗标题）
            if strong_elements and strong_elements[0] and strong_elements[0] != "央视网消息":
                result.append(f"<b>{escape(strong_elements[0])}</b>")

            # 处理 p 元素（正文内容）
            if p_elements and p_elements[0] and p_elements[0] != "（新闻联播）：":
                # 在开头添加两个空格
                p_text = "&nbsp;&nbsp;" + escape(p_elements[0].strip())
                result.append(p_text)

        return '<br>'.join(result) if result else "⚠️ 内容获取失败"

    except Exception as e:
        logger.error(f"解析内容页失败: {e}")
        return "⚠️ 内容获取失败"


# ==================== 核心功能 ====================

async def fetch_single_news(session: aiohttp.ClientSession, semaphore: asyncio.Semaphore,
                             title: str, href: str, index: int) -> Optional[NewsItem]:
    """获取单条新闻内容"""
    logger.info(f"正在获取 [{index}] {title[:20]}...")

    # 重试获取内容页
    for attempt in range(RETRY_TIMES):
        html = await fetch_url(session, href, semaphore)
        if html:
            content = parse_content_page(html)
            return NewsItem(
                title=title,
                content=content,
                video_url=href,
                index=index
            )

        if attempt < RETRY_TIMES - 1:
            wait_time = (attempt + 1) * 2  # 指数退避
            logger.warning(f"获取失败，{wait_time}秒后重试...")
            await asyncio.sleep(wait_time)

    logger.error(f"获取失败 [{index}] {title[:20]}")
    # 返回带错误提示的新闻
    return NewsItem(
        title=title,
        content="⚠️ 内容获取失败，请查看视频",
        video_url=href,
        index=index
    )


async def hq_news_async(date_str: str) -> NewsList:
    """异步并发获取新闻联播"""
    logger.info(f"开始获取 {date_str} 日新闻联播...")

    # 获取列表页
    list_url = f'https://tv.cctv.com/lm/xwlb/day/{date_str}.shtml'
    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        list_html = await fetch_url(session, list_url, asyncio.Semaphore(1))

        if not list_html:
            logger.error("获取列表页失败")
            return NewsList(date=date_str)

        # 解析新闻列表
        news_list = parse_list_page(list_html)

        if not news_list:
            logger.warning("未解析到任何新闻")
            return NewsList(date=date_str)

        # 并发获取所有新闻内容
        semaphore = asyncio.Semaphore(MAX_CONCURRENT)
        tasks = [
            fetch_single_news(session, semaphore, item['title'], item['href'], i + 1)
            for i, item in enumerate(news_list)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 整理结果
        news_items = []
        for result in results:
            if isinstance(result, NewsItem):
                news_items.append(result)
            elif isinstance(result, Exception):
                logger.error(f"获取异常: {result}")

        logger.info(f"成功获取 {len(news_items)}/{len(news_list)} 条新闻")

        return NewsList(items=news_items, date=date_str)


def PushPlus(newstitle: str, newscontext: str) -> bool:
    """PushPlus推送"""
    try:
        PushPlus_url = 'http://www.pushplus.plus/send'
        data = {
            "token": PUSHPLUSSCKEY,
            "title": newstitle,
            "content": newscontext,
            "template": "html"
        }
        body = json.dumps(data).encode(encoding='utf-8')
        headers = {
            "Content-Type": "application/json"
        }

        import requests
        response = requests.post(url=PushPlus_url, data=body, headers=headers, timeout=10)

        if response.status_code == 200:
            result = response.json()
            if result.get('code') == 200:
                logger.info("PushPlus推送成功")
                return True
            else:
                logger.error(f"PushPlus推送失败: {result.get('msg')}")
                return False
        else:
            logger.error(f"PushPlus请求失败 [{response.status_code}]")
            return False

    except Exception as e:
        logger.error(f"PushPlus推送异常: {e}")
        return False


def split_and_push(newstitle: str, news_list: NewsList, max_length: int = 8800) -> bool:
    """分批推送超长内容 - 按新闻项完整分割，每批都有美化效果（使用内联样式）"""
    if not news_list.items:
        logger.warning("没有新闻内容需要推送")
        return False

    # 计算总文本长度
    total_html = news_list.to_html()
    text_only = re.sub(r'<[^>]+>', '', total_html)

    # 如果总长度在限制内，直接推送完整版
    if len(text_only) < max_length:
        return PushPlus(newstitle, total_html)

    # 需要分批推送 - 按新闻项完整分割
    logger.info(f"内容较长（{len(text_only)}字符），开始按新闻项分批推送...")

    # 收集每条新闻的 HTML 和长度
    news_htmls = []
    for item in news_list.items:
        news_htmls.append({
            'html': item.to_html(),
            'length': len(re.sub(r'<[^>]+>', '', item.to_html()))
        })

    # 将新闻分配到各批次（确保每条新闻完整不拆分）
    batches = []  # 每个元素是一个列表，包含该批次的新闻索引
    current_batch = []
    current_length = 0

    for i, news in enumerate(news_htmls):
        # 检查如果加上这条新闻会不会超限
        # 留一些余量给样式和包装
        needed_length = current_length + news['length'] + 500

        if needed_length > max_length and current_batch:
            # 保存当前批次，开始新批次
            batches.append(current_batch)
            current_batch = [i]
            current_length = news['length']
        else:
            current_batch.append(i)
            current_length += news['length']

    # 添加最后一批
    if current_batch:
        batches.append(current_batch)

    logger.info(f"将分为 {len(batches)} 批推送")

    # 后续批次的标题样式
    STYLE_TOC_CONTINUE = '''
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
color: white;
padding: 15px 20px;
border-radius: 12px;
margin-bottom: 20px;
font-size: 16px;
font-weight: bold;
    '''.strip()

    # 推送所有批次
    success = True
    for batch_idx, batch_indices in enumerate(batches):
        batch_title = f"{newstitle} ({batch_idx + 1}/{len(batches)}) 📺"
        logger.info(f"推送第 {batch_idx + 1}/{len(batches)} 批，包含 {len(batch_indices)} 条新闻...")

        # 构建该批次的 HTML
        if batch_idx == 0:
            # 第一批：包含完整目录
            batch_items = [news_list.items[i] for i in batch_indices]
            toc = _generate_toc_for_batch(batch_items)
            content = '\n'.join([news_list.items[i].to_html() for i in batch_indices])

            batch_html = f'''
<div style="{STYLE_CONTAINER}">
    <div style="{STYLE_TOC}">
        <div style="{STYLE_TOC_TITLE}">📋 今日目录（共{len(news_list.items)}条，第{len(batches)}批）</div>
        <div style="{STYLE_TOC_LIST}">
            {toc}
        </div>
    </div>
    {content}
</div>
            '''.strip()
        else:
            # 后续批次：只包含标题和正文
            content = '\n'.join([news_list.items[i].to_html() for i in batch_indices])

            batch_html = f'''
<div style="{STYLE_CONTAINER}">
    <div style="{STYLE_TOC_CONTINUE}">📰 续-{batch_idx + 1}（共{len(batches)}批，第{batch_idx + 1}批）</div>
    {content}
</div>
            '''.strip()

        if not PushPlus(batch_title, batch_html):
            success = False
            logger.error(f"第 {batch_idx + 1} 批推送失败")

    return success


def _generate_toc_for_batch(items: List[NewsItem]) -> str:
    """为一批新闻生成目录HTML"""
    toc_items = []
    for item in items:
        toc_items.append(f'<div style="{STYLE_TOC_ITEM}">{item.index}️⃣ {escape(item.title)}</div>')
    return '\n'.join(toc_items)


# ==================== 主程序 ====================

async def main():
    """主函数"""
    start_time = time.time()

    # 获取日期（昨天）
    timeStruct = time.localtime()
    strTime = time.strftime("%Y%m%d", timeStruct)
    date_str = str(int(strTime) - 1)  # 昨天的日期

    logger.info("=" * 50)
    logger.info("新闻联播文字稿抓取程序启动")
    logger.info(f"日期: {date_str}")
    logger.info("=" * 50)

    # 检查Token
    if not PUSHPLUSSCKEY:
        logger.error("未设置 PUSHPLUSSCKEY 环境变量")
        return

    # 异步获取新闻
    news_list = await hq_news_async(date_str)

    if not news_list.items:
        logger.warning("没有获取到任何新闻内容")
        return

    # 推送（使用按新闻项分割的方式，每批都有美化效果）
    newstitle = f"{date_str} 新闻联播文字稿"
    success = split_and_push(newstitle, news_list)

    # 统计
    elapsed = time.time() - start_time
    logger.info("=" * 50)
    logger.info(f"执行完成，耗时: {elapsed:.2f}秒")
    logger.info(f"新闻条数: {len(news_list.items)}")
    logger.info(f"推送结果: {'成功' if success else '失败'}")
    logger.info("=" * 50)


# ==================== 入口 ====================

if __name__ == '__main__':
    # 腾讯云SCF入口
    def main_handler(event, context):
        asyncio.run(main())
        return '执行完成'

    # 本地/服务器入口
    asyncio.run(main())
