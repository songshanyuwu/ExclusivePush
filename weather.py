# -*- coding: utf-8 -*-
"""
天气推送脚本 - 优化版 V2.0
功能：获取多城市天气、精美HTML展示、气温折线图、多日预报、完整错误处理
新增：气温折线图展示、前天+未来3天天气
注意：使用同步请求（城市数量少，无需异步）
"""

import logging
import os
import time
import requests
import json
import re
import matplotlib
matplotlib.use('Agg')  # 使用非GUI后端
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from io import BytesIO
import base64

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
# 预览模式：设为1则不推送，只生成HTML到本地文件
PREVIEW_MODE = os.environ.get('PREVIEW_MODE', '0')
# 输出目录
OUTPUT_DIR = os.environ.get('OUTPUT_DIR', '.')

# matplotlib中文字体配置（适配不同环境）
def setup_chinese_font():
    """配置matplotlib中文字体"""
    font_paths = [
        '/System/Library/Fonts/PingFang.ttc',  # macOS
        '/System/Library/Fonts/STHeiti Light.ttc',  # macOS备选
        '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',  # Linux
        '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',  # Linux备选
        'C:\\Windows\\Fonts\\msyh.ttc',  # Windows
    ]

    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                font_prop = FontProperties(fname=font_path)
                logger.info(f"成功加载中文字体: {font_path}")
                return font_prop
            except Exception as e:
                logger.warning(f"字体加载失败 {font_path}: {e}")
                continue

    logger.warning("未找到中文字体，折线图可能显示方框")
    return None

# 全局字体属性
FONT_PROP = setup_chinese_font()

# 设置matplotlib中文字体（解决坐标轴等默认字体）
if FONT_PROP:
    plt.rcParams['font.family'] = FONT_PROP.get_name()
    plt.rcParams['axes.unicode_minus'] = False

# ==================== 样式定义（内联样式，兼容PushPlus）====================

STYLE_CONTAINER = '''
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
padding: 14px 16px;
border-radius: 12px;
color: white;
margin-bottom: 12px;
'''.strip()

STYLE_CITY_CARD = '''
background: white;
border-radius: 10px;
padding: 14px 16px;
margin-bottom: 10px;
box-shadow: 0 2px 8px rgba(0,0,0,0.08);
color: #333;
'''.strip()

STYLE_CITY_HEADER = '''
display: flex;
align-items: center;
justify-content: space-between;
margin-bottom: 10px;
padding-bottom: 8px;
border-bottom: 1px solid #f0f0f0;
'''.strip()

STYLE_CITY_NAME = '''
font-size: 16px;
font-weight: bold;
color: #667eea;
'''.strip()

STYLE_WEATHER_ICON = '''
font-size: 28px;
'''.strip()

STYLE_TEMP = '''
font-size: 24px;
font-weight: bold;
color: #ff6b6b;
margin: 8px 0;
'''.strip()

STYLE_INFO_GRID = '''
display: grid;
grid-template-columns: 1fr 1fr;
gap: 8px;
margin-top: 8px;
'''.strip()

STYLE_INFO_ITEM = '''
background: #f8f9fa;
padding: 8px 10px;
border-radius: 6px;
font-size: 12px;
color: #555;
'''.strip()

STYLE_LABEL = '''
color: #999;
font-size: 11px;
margin-bottom: 3px;
'''.strip()

STYLE_VALUE = '''
color: #333;
font-weight: 500;
font-size: 12px;
'''.strip()

STYLE_NOTICE = '''
background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
padding: 10px 12px;
border-radius: 8px;
margin-top: 10px;
color: #8b4513;
font-size: 13px;
line-height: 1.4;
'''.strip()

STYLE_ENGLISH = '''
background: #f0f4ff;
padding: 12px;
border-radius: 8px;
margin-top: 12px;
border-left: 3px solid #667eea;
'''.strip()

STYLE_ENGLISH_TITLE = '''
font-size: 13px;
font-weight: bold;
color: #667eea;
margin-bottom: 6px;
'''.strip()

STYLE_ENGLISH_CONTENT = '''
color: #555;
font-size: 13px;
line-height: 1.5;
'''.strip()

# ==================== 工具函数 ====================

def extract_temp(temp_str: str) -> int:
    """从温度字符串提取数值（如 '高温 25℃' -> 25）"""
    match = re.search(r'(-?\d+)', temp_str)
    return int(match.group(1)) if match else 0


def get_day_before_yesterday_date() -> str:
    """获取前天的日期字符串（YYYY-MM-DD）"""
    day_before = datetime.now() - timedelta(days=2)
    return day_before.strftime('%Y-%m-%d')


def generate_temperature_chart(weather_data: Dict) -> str:
    """
    生成气温折线图并返回base64编码的图片
    显示前天、昨日、今日、明日、后日、大后日的最高气温、最低气温和天气类型
    使用月日格式，今日样式突出
    """
    try:
        # 提取预报数据
        forecast = weather_data["forecast"]
        yesterday = weather_data["yesterday"]

        # 准备数据
        dates = []
        high_temps = []
        low_temps = []
        weather_types = []
        today_index = 2  # 今日在数组中的索引

        # 获取今日日期作为基准
        today_date = datetime.now()

        # 生成日期标签（月日格式）
        def format_date(delta_days):
            date = today_date + timedelta(days=delta_days)
            return f"{date.month}/{date.day}"

        # 前天数据估算
        yesterday_high = extract_temp(yesterday["high"])
        yesterday_low = extract_temp(yesterday["low"])
        today_high = extract_temp(forecast[0]["high"])
        today_low = extract_temp(forecast[0]["low"])

        day_before_yesterday_high = yesterday_high - (today_high - yesterday_high)
        day_before_yesterday_low = yesterday_low - (today_low - yesterday_low)

        # 简化天气文字映射
        weather_texts = {
            '晴': '晴', '多云': '多云', '阴': '阴', '小雨': '小雨', '中雨': '中雨',
            '大雨': '大雨', '暴雨': '暴雨', '雷阵雨': '雷雨', '雪': '雪', '雾': '雾', '霾': '霾'
        }

        # 构建6天数据：前天到后3天
        # [日期偏移, 最高温, 最低温, 天气]
        all_data = [
            (-2, day_before_yesterday_high, day_before_yesterday_low, "--"),
            (-1, yesterday_high, yesterday_low, yesterday["type"]),
        ]
        # 添加今日和未来3天
        for i in range(min(4, len(forecast))):
            all_data.append((i, extract_temp(forecast[i]["high"]), extract_temp(forecast[i]["low"]), forecast[i]["type"]))

        # 填充数据数组
        for delta, high, low, wtype in all_data:
            dates.append(format_date(delta))
            high_temps.append(high)
            low_temps.append(low)
            weather_types.append(weather_texts.get(wtype, '多云'))

        # 创建紧凑型图表
        plt.figure(figsize=(9, 4.8))
        plt.style.use('seaborn-v0_8-whitegrid')

        ax = plt.gca()
        ax.set_facecolor('#fafafa')

        non_today_indices = [i for i in range(len(dates)) if i != today_index]

        # 绘制连接线（非今日为浅色）
        plt.plot(range(len(dates)), high_temps, '-', color='#ffb3b3', linewidth=1.5, alpha=0.4)
        plt.plot(range(len(dates)), low_temps, '-', color='#a3e4e0', linewidth=1.5, alpha=0.4)

        # 今日高亮背景区域
        plt.axvspan(today_index - 0.45, today_index + 0.45, alpha=0.12, color='#667eea', zorder=0)

        # 绘制数据点（非今日）
        for i in non_today_indices:
            plt.plot(i, high_temps[i], 'o', color='#ff6b6b', markersize=7, alpha=0.6, zorder=3)
            plt.plot(i, low_temps[i], 's', color='#4ecdc4', markersize=7, alpha=0.6, zorder=3)

        # 绘制今日数据点（大标记、白边、高亮）
        plt.plot(today_index, high_temps[today_index], 'o', color='#ff4757', markersize=12,
                markeredgecolor='white', markeredgewidth=2.5, zorder=6)
        plt.plot(today_index, low_temps[today_index], 's', color='#2ed573', markersize=12,
                markeredgecolor='white', markeredgewidth=2.5, zorder=6)

        # 温度标注
        for i, (high, low) in enumerate(zip(high_temps, low_temps)):
            is_today = (i == today_index)
            offset_y_high = 10 if is_today else 7
            offset_y_low = -12 if is_today else -9
            fontsize = 11 if is_today else 9
            fontweight = 'bold' if is_today else 'normal'

            plt.annotate(f'{high}°', (i, high), textcoords="offset points",
                        xytext=(0, offset_y_high), ha='center', fontsize=fontsize,
                        color='#ff4757' if is_today else '#ff6b6b', fontweight=fontweight, zorder=7)
            plt.annotate(f'{low}°', (i, low), textcoords="offset points",
                        xytext=(0, offset_y_low), ha='center', fontsize=fontsize,
                        color='#2ed573' if is_today else '#4ecdc4', fontweight=fontweight, zorder=7)

            # 天气文字标注（在高低温度之间）
            weather_text = weather_types[i]
            plt.annotate(weather_text, (i, (high + low) / 2), textcoords="offset points",
                        xytext=(0, 0), ha='center', fontsize=8, color='#888', zorder=8)

        # 标题和标签
        title_color = '#333'
        label_color = '#666'

        if FONT_PROP:
            plt.title('6日天气气温趋势', fontproperties=FONT_PROP, fontsize=14, fontweight='bold',
                     pad=10, color=title_color)
        else:
            plt.title('6日天气气温趋势', fontsize=14, fontweight='bold', pad=10, color=title_color)

        plt.grid(True, alpha=0.25, linestyle='-', linewidth=0.5)
        plt.xticks(range(len(dates)), dates, fontsize=10, color=label_color)

        # 设置y轴范围
        y_min = min(low_temps) - 5
        y_max = max(high_temps) + 8
        plt.ylim(y_min, y_max)
        plt.yticks(fontsize=9, color=label_color)

        # 今日温差区域填充
        plt.fill_between([today_index - 0.45, today_index + 0.45],
                        [low_temps[today_index]] * 2, [high_temps[today_index]] * 2,
                        alpha=0.25, color='#667eea', zorder=1)

        # 去除多余边框
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#d0d0d0')
        ax.spines['bottom'].set_color('#d0d0d0')

        plt.tight_layout(pad=1.2)

        # 保存为base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=115, bbox_inches='tight',
                   facecolor='#fafafa', edgecolor='none')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close()

        return image_base64

    except Exception as e:
        logger.error(f"生成气温折线图失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return ""


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
    """将天气数据转换为美化HTML（含气温折线图）"""
    try:
        city_info = data["cityInfo"]
        weather_data = data["data"]
        today = weather_data["forecast"][0]
        yesterday = weather_data["yesterday"]

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

        # 生成气温折线图（天气直接显示在图上）
        chart_base64 = generate_temperature_chart(weather_data)
        chart_html = ""
        if chart_base64:
            chart_html = f'''
<div style="margin-top: 12px; text-align: center;">
    <img src="data:image/png;base64,{chart_base64}"
         style="width: 100%; max-width: 600px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);"
         alt="6日天气气温趋势"/>
</div>
            '''

        html = f'''
<div style="{STYLE_CITY_CARD}">
    <div style="{STYLE_CITY_HEADER}">
        <div style="{STYLE_CITY_NAME}">📍 {city_info["parent"]} {city_info["city"]}</div>
        <div style="color: #ff6b6b; font-size: 14px; font-weight: bold;">{today["type"]}</div>
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

    <div style="{STYLE_NOTICE}">💡 {today["notice"]}</div>

    {chart_html}
</div>
        '''.strip()

        return html

    except Exception as e:
        logger.error(f"天气数据转换失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
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
    logger.info("天气推送脚本启动 V2.0（含气温折线图）")
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
    <div style="font-size: 18px; font-weight: bold; margin-bottom: 4px;">🌤️ 今日天气播报</div>
    <div style="font-size: 12px; opacity: 0.85;">{current_time}</div>
</div>

{' '.join(weather_htmls)}

{iciba_to_html(iciba_result)}
    '''.strip()

    # 推送
    title = f"🌤️ 今日天气播报"

    # 预览模式：保存HTML到本地文件
    if PREVIEW_MODE == '1':
        preview_file = os.path.join(OUTPUT_DIR, 'weather_preview.html')
        with open(preview_file, 'w', encoding='utf-8') as f:
            f.write(full_html)
        logger.info(f"预览模式：HTML已保存到 {preview_file}")
        return True

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
