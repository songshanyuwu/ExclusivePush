# -*- coding: utf-8 -*-
"""
天气推送脚本 - 优化版
功能：获取多城市天气、精美HTML展示、完整错误处理、兼容PushPlus
注意：使用同步请求（城市数量少，无需异步）
"""

import logging
import os
import time
import requests
import json
from typing import List, Dict, Optional

# ==================== 配置 ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 推送配置
PUSHPLUSSCKEY = os.environ.get('PUSHPLUSSCKEY')
SERVERSCKEY = os.environ.get('SERVERSCKEY')
COOLSCKEY = os.environ.get('COOLSCKEY')

# ==================== 样式定义（内联样式，兼容PushPlus）====================

STYLE_CONTAINER = '''
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
padding: 20px;
border-radius: 16px;
color: white;
margin-bottom: 20px;
'''.strip()

STYLE_CITY_CARD = '''
background: white;
border-radius: 12px;
padding: 20px;
margin-bottom: 16px;
box-shadow: 0 4px 12px rgba(0,0,0,0.1);
color: #333;
'''.strip()

STYLE_CITY_HEADER = '''
display: flex;
align-items: center;
justify-content: space-between;
margin-bottom: 16px;
padding-bottom: 12px;
border-bottom: 2px solid #f0f0f0;
'''.strip()

STYLE_CITY_NAME = '''
font-size: 18px;
font-weight: bold;
color: #667eea;
'''.strip()

STYLE_WEATHER_ICON = '''
font-size: 32px;
'''.strip()

STYLE_TEMP = '''
font-size: 28px;
font-weight: bold;
color: #ff6b6b;
margin: 12px 0;
'''.strip()

STYLE_INFO_GRID = '''
display: grid;
grid-template-columns: 1fr 1fr;
gap: 10px;
margin-top: 12px;
'''.strip()

STYLE_INFO_ITEM = '''
background: #f8f9fa;
padding: 10px 12px;
border-radius: 8px;
font-size: 13px;
color: #555;
'''.strip()

STYLE_LABEL = '''
color: #999;
font-size: 12px;
margin-bottom: 4px;
'''.strip()

STYLE_VALUE = '''
color: #333;
font-weight: 500;
'''.strip()

STYLE_NOTICE = '''
background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
padding: 12px 16px;
border-radius: 10px;
margin-top: 16px;
color: #8b4513;
font-size: 14px;
'''.strip()

STYLE_ENGLISH = '''
background: #f0f4ff;
padding: 16px;
border-radius: 10px;
margin-top: 20px;
border-left: 4px solid #667eea;
'''.strip()

STYLE_ENGLISH_TITLE = '''
font-size: 14px;
font-weight: bold;
color: #667eea;
margin-bottom: 8px;
'''.strip()

STYLE_ENGLISH_CONTENT = '''
color: #555;
font-size: 14px;
line-height: 1.6;
'''.strip()

# ==================== 数据获取 ====================

def fetch_weather(city_code: str) -> Optional[Dict]:
    """获取单个城市天气（同步）"""
    try:
        url = f'http://t.weather.itboy.net/api/weather/city/{city_code}'
        response = requests.get(url, timeout=15)

        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 200:
                logger.info(f"获取成功: {city_code}")
                return data
            else:
                logger.warning(f"API返回错误: {city_code}, status={data.get('status')}")
                return None
        else:
            logger.warning(f"请求失败 [{response.status_code}]: {city_code}")
            return None
    except Exception as e:
        logger.error(f"获取天气异常: {city_code}, 错误: {e}")
        return None


def fetch_iciba() -> Optional[Dict]:
    """获取每日英语"""
    try:
        url = 'http://open.iciba.com/dsapi/'
        response = requests.get(url, timeout=15)

        if response.status_code == 200:
            data = response.json()
            logger.info("获取每日英语成功")
            return data
        else:
            logger.warning(f"获取每日英语失败 [{response.status_code}]")
            return None
    except Exception as e:
        logger.error(f"获取每日英语异常: {e}")
        return None


def weather_to_html(data: Dict) -> str:
    """将天气数据转换为美化HTML"""
    try:
        city_info = data["cityInfo"]
        weather_data = data["data"]
        today = weather_data["forecast"][0]
        yesterday = weather_data["yesterday"]
        tomorrow = weather_data["forecast"][1]

        # 天气图标映射
        weather_icons = {
            '晴': '☀️',
            '多云': '⛅',
            '阴': '☁️',
            '小雨': '🌧️',
            '中雨': '🌧️',
            '大雨': '🌧️',
            '暴雨': '⛈️',
            '雷阵雨': '⛈️',
            '雪': '❄️',
            '雾': '🌫️',
            '霾': '🌫️'
        }
        weather_icon = weather_icons.get(today["type"], '🌤️')

        html = f'''
<div style="{STYLE_CITY_CARD}">
    <div style="{STYLE_CITY_HEADER}">
        <div style="{STYLE_CITY_NAME}">📍 {city_info["parent"]} {city_info["city"]}</div>
        <div style="color: #ff6b6b; font-size: 16px; font-weight: bold; margin-bottom: 12px;">{today["type"]}</div>
        <div style="{STYLE_WEATHER_ICON}">{weather_icon}</div>
    </div>
    
    <div style="{STYLE_TEMP}">{today["high"]} / {today["low"]}</div>
    
    <div style="{STYLE_INFO_GRID}">
        <div style="{STYLE_INFO_ITEM}">
            <div style="{STYLE_LABEL}">💨 风力风向</div>
            <div style="{STYLE_VALUE}">{today["fx"]} {today["fl"]}</div>
        </div>
        <div style="{STYLE_INFO_ITEM}">
            <div style="{STYLE_LABEL}">🌫️ 空气质量</div>
            <div style="{STYLE_VALUE}">{weather_data["quality"]}</div>
        </div>
        <div style="{STYLE_INFO_ITEM}">
            <div style="{STYLE_LABEL}">💧 湿度</div>
            <div style="{STYLE_VALUE}">{weather_data["shidu"]}</div>
        </div>
        <div style="{STYLE_INFO_ITEM}">
            <div style="{STYLE_LABEL}">🤧 感冒指数</div>
            <div style="{STYLE_VALUE}">{weather_data["ganmao"]}</div>
        </div>
    </div>
    
    <div style="{STYLE_NOTICE}">
        💡 {today["notice"]}
    </div>
    
    <div style="margin-top: 12px; font-size: 12px; color: #999; text-align: right;">
        昨日: {yesterday["high"]} / {yesterday["low"]} {yesterday["type"]}
    </div>
    <div style="margin-top: 12px; font-size: 12px; color: #999; text-align: right;">
        今日日: {today["high"]} / {today["low"]} {today["type"]}
    </div>
    <div style="margin-top: 12px; font-size: 12px; color: #999; text-align: right;">
        明日: {tomorrow["high"]} / {tomorrow["low"]} {tomorrow["type"]}
    </div>
</div>
        '''.strip()

        return html

    except Exception as e:
        logger.error(f"天气数据转换失败: {e}")
        return f'<div style="{STYLE_CITY_CARD}">⚠️ 天气数据解析失败</div>'


def iciba_to_html(data: Dict) -> str:
    """将每日英语转换为美化HTML"""
    if not data:
        return ""

    return f'''
<div style="{STYLE_ENGLISH}">
    <div style="{STYLE_ENGLISH_TITLE}">📖 每日一句</div>
    <div style="{STYLE_ENGLISH_CONTENT}">
        <div style="margin-bottom: 8px;"><b>{data.get("content", "")}</b></div>
        <div style="color: #888; font-size: 13px;">{data.get("note", "")}</div>
    </div>
</div>
    '''.strip()


# ==================== 推送功能 ====================

def push_plus(title: str, content: str) -> bool:
    """PushPlus推送"""
    try:
        if not PUSHPLUSSCKEY:
            logger.error("未设置 PUSHPLUSSCKEY")
            return False

        url = 'http://www.pushplus.plus/send'
        data = {
            "token": PUSHPLUSSCKEY,
            "title": title,
            "content": content,
            "template": "html"
        }
        body = json.dumps(data).encode('utf-8')
        headers = {"Content-Type": "application/json"}

        response = requests.post(url=url, data=body, headers=headers, timeout=10)

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


def server_push(title: str, content: str) -> bool:
    """Server酱推送"""
    try:
        if not SERVERSCKEY:
            logger.warning("未设置 SERVERSCKEY，跳过Server酱推送")
            return False

        api = f"https://sc.ftqq.com/{SERVERSCKEY}.send"
        data = {
            "text": title,
            "desp": content.replace('\n', '\n\n')
        }

        response = requests.post(api, data=data, timeout=10)

        if response.status_code == 200:
            logger.info("Server酱推送成功")
            return True
        else:
            logger.error(f"Server酱推送失败 [{response.status_code}]")
            return False

    except Exception as e:
        logger.error(f"Server酱推送异常: {e}")
        return False


# ==================== 主程序 ====================

def main():
    """主函数"""
    start_time = time.time()

    logger.info("=" * 50)
    logger.info("天气推送脚本启动")
    logger.info("=" * 50)

    # 城市列表（可以从环境变量读取，方便配置）
    city_codes_str = os.environ.get('WEATHER_CITY_CODES', '101120101,101120504,101121201,101010300')
    city_codes = [code.strip() for code in city_codes_str.split(',')]

    logger.info(f"将获取 {len(city_codes)} 个城市的天气: {city_codes}")

    # 顺序获取所有城市天气（城市少，同步足够）
    weather_results = []
    for code in city_codes:
        result = fetch_weather(code)
        weather_results.append(result)

    # 获取每日英语
    iciba_result = fetch_iciba()

    # 构建HTML内容
    weather_htmls = []
    for i, result in enumerate(weather_results):
        if isinstance(result, Dict) and result:
            weather_htmls.append(weather_to_html(result))
        else:
            logger.error(f"获取城市 {city_codes[i]} 天气失败")
            weather_htmls.append(f'<div style="{STYLE_CITY_CARD}">⚠️ {city_codes[i]} 天气获取失败</div>')

    # 组装完整HTML
    current_time = time.strftime("%Y-%m-%d %H:%M", time.localtime())

    full_html = f'''
<div style="{STYLE_CONTAINER}">
    <div style="font-size: 20px; font-weight: bold; margin-bottom: 8px;">🌤️ 今日天气播报</div>
    <div style="font-size: 14px; opacity: 0.9;">{current_time}</div>
</div>

{' '.join(weather_htmls)}

{iciba_to_html(iciba_result)}
    '''.strip()

    # 推送
    title = f"🌤️ 今日天气播报"

    success = True
    # PushPlus推送
    if PUSHPLUSSCKEY:
        if not push_plus(title, full_html):
            success = False

    # Server酱推送（如果配置了）
    if SERVERSCKEY:
        if not server_push(title, full_html):
            success = False

    # 统计
    elapsed = time.time() - start_time
    logger.info("=" * 50)
    logger.info(f"执行完成，耗时: {elapsed:.2f}秒")
    logger.info(f"推送结果: {'成功' if success else '失败'}")
    logger.info("=" * 50)

    return success


if __name__ == '__main__':
    # 腾讯云SCF入口
    def main_handler(event, context):
        main()
        return '执行完成'

    # 本地/服务器/GitHub Actions入口
    main()
