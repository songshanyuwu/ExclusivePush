# -*- coding: utf-8 -*-
"""
天气推送脚本

功能：获取多城市天气（itboy 为主数据源，心知天气免费版作补充），
生成精美 HTML 卡片，通过 PushPlus / Server 酱推送，并附带每日英语。
所有网络请求失败时优雅降级，不中断整体流程。
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, Optional

import requests

# ==================== 配置 ====================

# 日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 推送通道（从环境变量读取，未配置则跳过对应通道）
PUSHPLUSSCKEY = os.environ.get('PUSHPLUSSCKEY')   # PushPlus 令牌
SERVERSCKEY = os.environ.get('SERVERSCKEY')         # Server 酱令牌

# 心知天气（免费版）补充数据源
# 私钥从环境变量读取，切勿明文写入文件或提交仓库
SENIVERSE_API_KEY = os.environ.get('SENIVERSE_API_KEY')
# itboy 城市编码 -> 心知查询位置（拼音/城市）。
# 蓬莱在心知免费版无数据权限(AP010006)，映射至所属地级市烟台。
SENIVERSE_CITY_MAP = {
    '101120101': 'jinan',     # 济南
    '101120504': 'yantai',    # 蓬莱（心知无该城市，用烟台）
    '101121201': 'dongying',  # 东营
    '101010300': 'beijing',   # 北京
}

# 默认城市列表（济南/蓬莱(映射烟台)/东营/北京），可用环境变量 WEATHER_CITY_CODES 覆盖
DEFAULT_CITY_CODES = '101120101,101120504,101121201,101010300'

# ==================== 内联样式（兼容 PushPlus 邮件渲染） ====================
# 仅保留实际使用的样式，避免冗余；均为内联，无需外部 CSS。

# 城市名称头部：紫蓝渐变背景条
STYLE_CONTAINER = '''
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
padding: 12px 14px;
border-radius: 10px;
color: white;
margin-bottom: 10px;
'''.strip()

# 单个城市卡片容器：白底圆角 + 轻阴影
STYLE_CITY_CARD = '''
background: white;
border-radius: 8px;
padding: 12px 14px;
margin-bottom: 8px;
box-shadow: 0 2px 6px rgba(0,0,0,0.06);
color: #333;
'''.strip()

# 温馨提示：暖色渐变块
STYLE_NOTICE = '''
background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
padding: 8px 10px;
border-radius: 6px;
margin-top: 8px;
color: #8b4513;
font-size: 10px;
line-height: 1.3;
'''.strip()

# 每日英语区块
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

# ==================== 通用工具 ====================

def _weekday_cn(date_str: str) -> str:
    """由 'YYYY-MM-DD' 计算中文星期，如 '周四'；解析失败返回空串。"""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return "周" + "一二三四五六日"[dt.weekday()]
    except (ValueError, TypeError):
        return ""


def _chip(text: str) -> str:
    """统一风格的圆形 tag，风力/空气/湿度、生活指数共用。"""
    return (f'<span style="display:inline-block;background:#f5f7ff;color:#667eea;'
            f'border:1px solid #c7d0f5;border-radius:12px;'
            f'padding:2px 9px;margin:2px;font-size:10px;line-height:1.6;">{text}</span>')


# ==================== 数据源：itboy 天气 + 每日英语 ====================

def fetch_weather(city_code: str) -> Optional[Dict]:
    """获取单个城市天气（itboy 主数据源，同步请求）。失败返回 None。"""
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
    """获取每日英语（金山词霸开放接口）。失败返回 None。"""
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


# ==================== 数据源：心知天气（免费版补充） ====================

# 生活指数键名 -> 中文名（用于展示，未知键回退为原键名）
SUGGESTION_NAMES = {
    "car_washing": "洗车", "dressing": "穿衣", "comfort": "舒适度",
    "sport": "运动", "uv": "紫外线", "travel": "旅游",
    "fishing": "钓鱼", "air_pollution": "空气污染扩散", "allergy": "过敏",
    "umbrella": "雨伞", "flu": "感冒", "air_conditioner": "空调",
    "sunscreen": "防晒", "makeup": "化妆", "traffic": "交通",
    "spiritual": "心情",
}

# 生活指数键名 -> emoji 图标，与风力行(💨/🌫️/💧)风格保持一致
SUGGESTION_EMOJI = {
    "car_washing": "🚗", "dressing": "👕", "comfort": "😌",
    "sport": "🏃", "uv": "☀️", "travel": "🧳",
    "fishing": "🎣", "air_pollution": "🏭", "allergy": "🤧",
    "umbrella": "☂️", "flu": "🤒", "air_conditioner": "❄️",
    "sunscreen": "🧴", "makeup": "💄", "traffic": "🚦",
    "spiritual": "💗",
}


def fetch_seniverse(location: str) -> Optional[Dict]:
    """获取心知天气（免费版）数据：实况 + 3天预报 + 生活指数。

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
                result['location_name'] = res[0].get('location', {}).get('name')
        # 逐日预报（免费版 3 天）
        r = requests.get(f"{base}/weather/daily.json", params={**common, "days": 3}, timeout=10)
        if r.status_code == 200:
            res = r.json().get('results')
            if res:
                result['daily'] = res[0].get('daily', [])
                result.setdefault('location_name', res[0].get('location', {}).get('name'))
        # 生活指数
        r = requests.get(f"{base}/life/suggestion.json", params=common, timeout=10)
        if r.status_code == 200:
            res = r.json().get('results')
            if res:
                result['suggestion'] = res[0].get('suggestion', {})
                result.setdefault('location_name', res[0].get('location', {}).get('name'))
        if not result:
            logger.warning(f"心知天气无返回数据: {location}")
            return None
        logger.info(f"心知天气获取成功: {location}")
        return result
    except Exception as e:
        logger.error(f"心知天气获取异常: {location}, 错误: {e}")
        return None


# ==================== HTML 渲染 ====================

def city_block_html(itboy: Optional[Dict], seniverse: Optional[Dict], city_label: str) -> str:
    """将单个城市双源数据(itboy + 心知)整合为紧凑卡片。

    布局顺序（按用户指定）：
      头部(城市名单行 + 换行显示 itboy天气 | 心知当前)
      → 风力/空气/湿度(圆形 chip·名称：值·无外围带圈)
      → itboy 近三天(逐行) → 心知未来三天(逐行·与近三天格式一致·含星期)
      → 生活指数(圆形 chip + emoji·名称：值·无外围带圈) → 温馨提示
    itboy 温度保留原始 '高温 33℃' / '低温 25℃' 文本，不做裁剪。
    风力块、生活指数块均不套外围圆角边框，仅保留各自圆形 chip。
    """
    # ---------- itboy 解析 ----------
    ib_ok = isinstance(itboy, Dict) and bool(itboy)
    if ib_ok:
        city_info = itboy.get("cityInfo", {})
        wd = itboy.get("data", {})
        fc = wd.get("forecast", [])
        today = fc[0] if len(fc) > 0 else {}
        tomorrow = fc[1] if len(fc) > 1 else {}
        yesterday = wd.get("yesterday", {})
        city_name = f"{city_info.get('parent', '')} {city_info.get('city', '')}".strip() or city_label
        t_type = today.get("type", "")
        t_high = today.get("high", "")   # 原始: '高温 33℃'
        t_low = today.get("low", "")     # 原始: '低温 25℃'
        y_type = yesterday.get("type", "")
        y_high = yesterday.get("high", "")
        y_low = yesterday.get("low", "")
        mo_type = tomorrow.get("type", "")
        mo_high = tomorrow.get("high", "")
        mo_low = tomorrow.get("low", "")
        fx, fl = today.get("fx", ""), today.get("fl", "")
        quality = wd.get("quality", "")
        shidu = wd.get("shidu", "")
        notice = today.get("notice", "")
    else:
        city_name = city_label
        t_type = t_high = t_low = y_type = y_high = y_low = ""
        mo_type = mo_high = mo_low = fx = fl = quality = shidu = notice = ""

    # ---------- 头部：城市名 + itboy天气 + 分隔 + 心知当前 ----------
    ib_weather = f'{t_type} {t_high} / {t_low}' if (t_type or t_high) else '无数据'
    sx_now = seniverse.get('now') if isinstance(seniverse, Dict) else None
    if isinstance(sx_now, Dict) and sx_now:
        sx_temp = sx_now.get('temperature')
        sx_now_str = (f'🛰️ {sx_now.get("text", "—")} {sx_temp}℃'
                      if sx_temp is not None else f'🛰️ {sx_now.get("text", "—")}')
    else:
        sx_now_str = '🛰️ 无数据'
    header = (f'<div style="{STYLE_CONTAINER}font-size:16px;font-weight:bold;">'
              f'📍 {city_name}</div>'
              f'<div style="font-size:13px;color:#333;margin-bottom:6px;">'
              f'{ib_weather} &nbsp;|&nbsp; '
              f'<span style="font-weight:normal;color:#333;">{sx_now_str}</span></div>')

    # ---------- 风力/空气/湿度：圆形 chip（无外围带圈）----------
    if ib_ok:
        wx_chips = ''.join([
            _chip(f'💨 风力：{fx} {fl}'),
            _chip(f'🌫️ 空气：{quality}'),
            _chip(f'💧 湿度：{shidu}'),
        ])
        wx_block = f'<div style="margin-bottom:6px;line-height:1.8;">{wx_chips}</div>'
    else:
        wx_block = ('<div style="margin-bottom:6px;font-size:10px;color:#999;">'
                    'itboy 天气获取失败，无法展示风力/空气/湿度</div>')

    # ---------- itboy 近三天（逐行，与未来三天格式一致）----------
    if ib_ok:
        near3 = (f'<div style="font-size:10px;color:#777;line-height:1.8;margin:4px 0;">'
                 f'昨日&nbsp;&nbsp;&nbsp;&nbsp;{y_type} {y_high} / {y_low}<br>'
                 f'今日&nbsp;&nbsp;&nbsp;&nbsp;{t_type} {t_high} / {t_low}<br>'
                 f'明日&nbsp;&nbsp;&nbsp;&nbsp;{mo_type} {mo_high} / {mo_low}</div>')
    else:
        near3 = '<div style="font-size:10px;color:#999;margin:4px 0;">itboy 天气获取失败</div>'

    # ---------- 心知未来三天（逐行，与近三天格式一致，含日期星期）----------
    sx_daily = seniverse.get('daily') if isinstance(seniverse, Dict) else None
    if isinstance(sx_daily, list) and sx_daily:
        flines = []
        for d in sx_daily:
            e = []
            if d.get('wind_speed'):
                e.append(f"风{d.get('wind_speed')}km/h")
            if d.get('humidity'):
                e.append(f"湿{d.get('humidity')}%")
            if d.get('rainfall'):
                e.append(f"降水{d.get('rainfall')}mm")
            detail = f" [{''.join(e)}]" if e else ""
            wk = _weekday_cn(d.get('date', ''))
            date_cell = f"{d.get('date', '')[-5:]} {wk}".strip()  # '07-16 周四'
            flines.append(
                f'📅 {date_cell} &nbsp; {d.get("text_day", "")}/{d.get("text_night", "")} '
                f'&nbsp; {d.get("low", "")}~{d.get("high", "")}℃{detail}'
            )
        seniverse_future = (f'<div style="font-size:10px;color:#555;line-height:1.8;margin:4px 0;">'
                            f'{"<br>".join(flines)}</div>')
    else:
        seniverse_future = '<div style="font-size:10px;color:#999;margin:4px 0;">🛰️ 未来三天：无数据</div>'

    # ---------- 生活指数：圆形 chip + emoji（无外围带圈，风格对齐风力行）----------
    sx_sug = seniverse.get('suggestion') if isinstance(seniverse, Dict) else None
    sug_chips = []
    if isinstance(sx_sug, Dict):
        for key, val in sx_sug.items():
            name = SUGGESTION_NAMES.get(key, key)
            emoji = SUGGESTION_EMOJI.get(key, "•")
            brief = val.get('brief', '') if isinstance(val, Dict) else ''
            if brief:
                sug_chips.append(_chip(f'{emoji} {name}：{brief}'))
    if sug_chips:
        sug_block = f'<div style="margin-bottom:6px;line-height:1.8;">{"".join(sug_chips)}</div>'
    else:
        sug_block = ('<div style="margin-bottom:6px;font-size:10px;color:#999;">'
                     '🛰️ 生活指数：无数据</div>')

    # ---------- 温馨提示 ----------
    notice_block = f'<div style="{STYLE_NOTICE}">💡 {notice}</div>' if (ib_ok and notice) else ''

    return f'''
<div style="{STYLE_CITY_CARD}">
    {header}
    {wx_block}
    {near3}
    {seniverse_future}
    {sug_block}
    {notice_block}
</div>
        '''.strip()


def iciba_to_html(data: Dict) -> str:
    """将每日英语转换为美化 HTML。无数据返回空串。"""
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


# ==================== 推送通道 ====================

def push_plus(title: str, content: str) -> bool:
    """PushPlus 推送（HTML 模板）。未配置令牌返回 False。"""
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
    """Server 酱推送。未配置令牌返回 False。"""
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
    """主流程：拉取天气 -> 组装 HTML -> 推送。"""
    start_time = time.time()

    logger.info("=" * 50)
    logger.info("天气推送脚本启动")
    logger.info("=" * 50)

    # 城市列表：默认济南/蓬莱(映射烟台)/东营/北京，可用环境变量 WEATHER_CITY_CODES 覆盖
    city_codes_str = os.environ.get('WEATHER_CITY_CODES', DEFAULT_CITY_CODES)
    city_codes = [code.strip() for code in city_codes_str.split(',')]

    logger.info(f"将获取 {len(city_codes)} 个城市的天气: {city_codes}")

    # 顺序获取所有城市天气（城市少，同步足够）；并行补充心知数据源
    weather_results = []
    seniverse_results = []
    for code in city_codes:
        result = fetch_weather(code)
        weather_results.append(result)
        # 按城市编码映射心知查询位置
        sen_loc = SENIVERSE_CITY_MAP.get(code)
        seniverse_results.append(fetch_seniverse(sen_loc) if sen_loc else None)

    # 获取每日英语
    iciba_result = fetch_iciba()

    # 构建 HTML：每个城市整合为单块（itboy + 心知双源并列）
    weather_htmls = []
    for i, result in enumerate(weather_results):
        ci = result.get("cityInfo", {}) if isinstance(result, Dict) else {}
        city_label = f"{ci.get('parent', '')} {ci.get('city', '')}".strip() or city_codes[i]
        if not isinstance(result, Dict) or not result:
            logger.error(f"获取城市 {city_codes[i]} 天气失败")
        weather_htmls.append(city_block_html(result, seniverse_results[i], city_label))

    # 组装完整 HTML（标题块已移除，渐变样式用于各城市名称头部）
    full_html = f'''
{' '.join(weather_htmls)}

{iciba_to_html(iciba_result)}
    '''.strip()

    # 推送
    title = f"🌤️ 今日天气播报"

    success = True
    if PUSHPLUSSCKEY:
        if not push_plus(title, full_html):
            success = False

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
    # 腾讯云 SCF 入口（部署为云函数时由平台调用此 handler）
    def main_handler(event, context):
        main()
        return '执行完成'

    # 本地 / 服务器 / GitHub Actions 入口
    main()
