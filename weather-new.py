# -*- coding: utf-8 -*-
"""
天气推送脚本 - 紧凑版
功能：获取多城市天气、精美HTML展示、完整错误处理、兼容PushPlus
优化：紧凑排版设计
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

# 心知天气(免费版) 补充数据源配置
# 私钥从环境变量读取，切勿明文写入文件或提交仓库
SENIVERSE_API_KEY = os.environ.get('SENIVERSE_API_KEY')
# itboy城市编码 -> 心知查询位置(拼音/城市)。蓬莱心知免费版无该城市(AP010006)，映射至所属地级市烟台
SENIVERSE_CITY_MAP = {
    '101120101': 'jinan',     # 济南
    '101120504': 'yantai',    # 蓬莱(心知无该城市, 用烟台)
    '101121201': 'dongying',  # 东营
    '101010300': 'beijing',   # 北京
}

# ==================== 样式定义（内联样式，兼容PushPlus）- 紧凑版 ====================

STYLE_CONTAINER = '''
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
padding: 12px 14px;
border-radius: 10px;
color: white;
margin-bottom: 10px;
'''.strip()

STYLE_CITY_CARD = '''
background: white;
border-radius: 8px;
padding: 12px 14px;
margin-bottom: 8px;
box-shadow: 0 2px 6px rgba(0,0,0,0.06);
color: #333;
'''.strip()

STYLE_CITY_HEADER = '''
display: flex;
align-items: center;
justify-content: space-between;
margin-bottom: 8px;
padding-bottom: 6px;
border-bottom: 1px solid #f0f0f0;
'''.strip()

STYLE_CITY_NAME = '''
font-size: 15px;
font-weight: bold;
color: #667eea;
'''.strip()

STYLE_WEATHER_ICON = '''
font-size: 24px;
'''.strip()

STYLE_TEMP = '''
font-size: 20px;
font-weight: bold;
color: #ff6b6b;
margin: 6px 0;
'''.strip()

STYLE_INFO_GRID = '''
display: grid;
grid-template-columns: 1fr 1fr 1fr;
gap: 5px;
margin-top: 6px;
'''.strip()

STYLE_INFO_ITEM = '''
background: #f8f9fa;
padding: 4px 6px;
border-radius: 4px;
font-size: 10px;
color: #555;
'''.strip()

STYLE_LABEL = '''
color: #999;
font-size: 9px;
margin-bottom: 1px;
'''.strip()

STYLE_VALUE = '''
color: #333;
font-weight: 500;
font-size: 10px;
'''.strip()

STYLE_NOTICE = '''
background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
padding: 8px 10px;
border-radius: 6px;
margin-top: 8px;
color: #8b4513;
font-size: 10px;
line-height: 1.3;
'''.strip()

STYLE_FORECAST = '''
margin-top: 6px;
font-size: 10px;
color: #999;
line-height: 1.5;
'''.strip()

STYLE_ENGLISH = '''
background: #f0f4ff;
padding: 10px;
border-radius: 6px;
margin-top: 10px;
border-left: 3px solid #667eea;
'''.strip()

STYLE_ENGLISH_TITLE = '''
font-size: 12px;
font-weight: bold;
color: #667eea;
margin-bottom: 4px;
'''.strip()

STYLE_ENGLISH_CONTENT = '''
color: #555;
font-size: 12px;
line-height: 1.4;
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


def weather_to_html(data: Dict, seniverse: Optional[Dict] = None) -> str:
    """将天气数据转换为美化HTML（紧凑版）。seniverse 为心知补充数据源(可选)。"""
    try:
        city_info = data["cityInfo"]
        weather_data = data["data"]
        today = weather_data["forecast"][0]
        yesterday = weather_data["yesterday"]
        tomorrow = weather_data["forecast"][1]

        # 天气图标映射
        weather_icons = {
            '晴': '☀️', '多云': '⛅', '阴': '☁️', '小雨': '🌧️', '中雨': '🌧️',
            '大雨': '🌧️', '暴雨': '⛈️', '雷阵雨': '⛈️', '雪': '❄️', '雾': '🌫️', '霾': '🌫️'
        }
        weather_icon = weather_icons.get(today["type"], '🌤️')

        html = f'''
<div style="{STYLE_CITY_CARD}">
    <div style="{STYLE_CITY_HEADER}">
        <div style="{STYLE_CITY_NAME}">📍 {city_info["parent"]} {city_info["city"]}</div>
        <div style="color: #ff6b6b; font-size: 13px; font-weight: bold;">{today["type"]}</div>
        <div style="{STYLE_WEATHER_ICON}">{weather_icon}</div>
    </div>

    <div style="{STYLE_TEMP}">{today["high"]} / {today["low"]}</div>

    <div style="{STYLE_INFO_GRID}">
        <div style="{STYLE_INFO_ITEM}">
            <div style="{STYLE_LABEL}">💨 风力</div>
            <div style="{STYLE_VALUE}; font-size: 13px;">{today["fx"]} {today["fl"]}</div>
        </div>
        <div style="{STYLE_INFO_ITEM}">
            <div style="{STYLE_LABEL}">🌫️ 空气</div>
            <div style="{STYLE_VALUE}; font-size: 13px;">{weather_data["quality"]}</div>
        </div>
        <div style="{STYLE_INFO_ITEM}">
            <div style="{STYLE_LABEL}">💧 湿度</div>
            <div style="{STYLE_VALUE}; font-size: 13px;">{weather_data["shidu"]}</div>
        </div>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 5px; margin-top: 6px;">
        <div style="{STYLE_INFO_ITEM}">
            <div style="{STYLE_LABEL}">🤧 感冒</div>
            <div style="{STYLE_VALUE}">{weather_data["ganmao"][:15]}...</div>
        </div>
        <div style="{STYLE_NOTICE}">💡 {today["notice"]}</div>
    </div>

    <div style="margin-top: 8px; font-size: 10px; color: #999; text-align: center; display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 4px;">
        <span>昨日: {yesterday["type"]} {yesterday["high"][3:]} / {yesterday["low"][3:]}</span>
        <span>今日: {today["type"]} {today["high"][3:]} / {today["low"][3:]}</span>
        <span>明日: {tomorrow["type"]} {tomorrow["high"][3:]} / {tomorrow["low"][3:]}</span>
    </div>
    {seniverse_to_html(seniverse)}
</div>
        '''.strip()

        return html

    except Exception as e:
        logger.error(f"天气数据转换失败: {e}")
        return f'<div style="{STYLE_CITY_CARD}">⚠️ 天气数据解析失败</div>'


def iciba_to_html(data: Dict) -> str:
    """将每日英语转换为美化HTML（紧凑版）"""
    if not data:
        return ""

    return f'''
<div style="{STYLE_ENGLISH}">
    <div style="{STYLE_ENGLISH_TITLE}">📖 每日一句</div>
    <div style="{STYLE_ENGLISH_CONTENT}">
        <div style="margin-bottom: 4px;"><b>{data.get("content", "")}</b></div>
        <div style="color: #888; font-size: 11px;">{data.get("note", "")}</div>
    </div>
</div>
    '''.strip()


# ==================== 心知天气(免费版) 补充数据源 ====================

SUGGESTION_NAMES = {
    "car_washing": "洗车", "dressing": "穿衣", "comfort": "舒适度",
    "sport": "运动", "uv": "紫外线", "travel": "旅游",
    "fishing": "钓鱼", "air_pollution": "空气污染扩散", "allergy": "过敏",
    "umbrella": "雨伞", "flu": "感冒", "air_conditioner": "空调",
    "sunscreen": "防晒", "makeup": "化妆", "traffic": "交通",
    "spiritual": "心情",
}


def fetch_seniverse(location: str) -> Optional[Dict]:
    """获取心知天气(免费版)数据：实况 + 3天预报 + 生活指数。

    免费版限制：实况仅返回 text/code/temperature 三项；部分城市(如蓬莱)无数据权限(AP010006)。
    需配置环境变量 SENIVERSE_API_KEY（私钥）。返回 None 表示未配置或获取失败。
    """
    if not SENIVERSE_API_KEY:
        logger.warning("未配置 SENIVERSE_API_KEY，跳过心知数据源")
        return None
    if not location:
        return None
    base = "https://api.seniverse.com/v3"
    common = {"key": SENIVERSE_API_KEY, "location": location, "language": "zh-Hans", "unit": "c"}
    result = {}
    try:
        # 实况
        r = requests.get(f"{base}/weather/now.json", params=common, timeout=10)
        if r.status_code == 200:
            res = r.json().get('results')
            if res:
                result['now'] = res[0].get('now', {})
        # 逐日预报(免费版3天)
        r = requests.get(f"{base}/weather/daily.json", params={**common, "days": 3}, timeout=10)
        if r.status_code == 200:
            res = r.json().get('results')
            if res:
                result['daily'] = res[0].get('daily', [])
        # 生活指数
        r = requests.get(f"{base}/life/suggestion.json", params=common, timeout=10)
        if r.status_code == 200:
            res = r.json().get('results')
            if res:
                result['suggestion'] = res[0].get('suggestion', {})
        if not result:
            logger.warning(f"心知天气无返回数据: {location}")
            return None
        logger.info(f"心知天气获取成功: {location}")
        return result
    except Exception as e:
        logger.error(f"心知天气获取异常: {location}, 错误: {e}")
        return None


def seniverse_to_html(seniverse: Optional[Dict]) -> str:
    """将心知生活指数渲染为标签块，作为 itboy 主数据源的补充。"""
    if not seniverse:
        return ""
    sug = seniverse.get('suggestion')
    if not sug:
        return ""
    chips = []
    for key, val in sug.items():
        name = SUGGESTION_NAMES.get(key, key)
        brief = val.get('brief', '') if isinstance(val, dict) else ''
        if brief:
            chips.append(
                f'<span style="background:#eef2ff;color:#667eea;padding:2px 6px;'
                f'border-radius:4px;font-size:10px;margin:2px;display:inline-block;">'
                f'{name}·{brief}</span>'
            )
    if not chips:
        return ""
    return f'''
    <div style="margin-top:8px;padding-top:6px;border-top:1px dashed #e0e0e0;">
        <div style="font-size:10px;color:#999;margin-bottom:4px;">🛰️ 心知天气 · 生活指数</div>
        <div style="line-height:1.6;">{"".join(chips)}</div>
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
    logger.info("天气推送脚本启动（紧凑版）")
    logger.info("=" * 50)

    # 城市列表（可以从环境变量读取，方便配置）
    city_codes_str = os.environ.get('WEATHER_CITY_CODES', '101120101,101120504,101121201,101010300')
    city_codes = [code.strip() for code in city_codes_str.split(',')]

    logger.info(f"将获取 {len(city_codes)} 个城市的天气: {city_codes}")

    # 顺序获取所有城市天气（城市少，同步足够）
    weather_results = []
    seniverse_results = []
    for code in city_codes:
        result = fetch_weather(code)
        weather_results.append(result)
        # 并行获取心知天气(免费版)作为补充数据源；按城市编码映射其查询位置
        sen_loc = SENIVERSE_CITY_MAP.get(code)
        seniverse_results.append(fetch_seniverse(sen_loc) if sen_loc else None)

    # 获取每日英语
    iciba_result = fetch_iciba()

    # 构建HTML内容
    weather_htmls = []
    for i, result in enumerate(weather_results):
        if isinstance(result, Dict) and result:
            weather_htmls.append(weather_to_html(result, seniverse_results[i]))
        else:
            logger.error(f"获取城市 {city_codes[i]} 天气失败")
            weather_htmls.append(f'<div style="{STYLE_CITY_CARD}">⚠️ {city_codes[i]} 天气获取失败</div>')

    # 组装完整HTML
    current_time = time.strftime("%Y-%m-%d %H:%M", time.localtime())

    full_html = f'''
<div style="{STYLE_CONTAINER}">
    <div style="font-size: 16px; font-weight: bold; margin-bottom: 2px;">🌤️ 今日天气</div>
    <div style="font-size: 11px; opacity: 0.85;">{current_time}</div>
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
