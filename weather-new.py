# -*- coding: utf-8 -*-
"""
天气推送脚本

功能：获取多城市天气（itboy 为主数据源，心知天气免费版作补充），
生成移动端优化的精美 HTML 卡片，通过 PushPlus / Server 酱推送，并附带每日英语。
所有网络请求失败时优雅降级，不中断整体流程。
"""

import json
import logging
import os
import re
import time
from datetime import datetime
from typing import Dict, List, Optional

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

# ==================== 内联样式（兼容 PushPlus / 微信 WebView 渲染） ====================
# 全部内联；优先使用 inline-block / flex（现代微信 WebView 均支持），间距用 margin 而非 gap
# 以保证旧版安卓 WebView 兼容。

# 温馨提示：暖色块
STYLE_NOTICE = '''
background: #fff7ed;
padding: 10px 12px;
border-radius: 10px;
margin-top: 12px;
color: #b45309;
font-size: 12px;
line-height: 1.5;
'''.strip()

# 每日英语区块
STYLE_ENGLISH = '''
background: #f0f4ff;
padding: 10px 12px;
border-radius: 10px;
margin-top: 14px;
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
line-height: 1.5;
'''.strip()

# ==================== 通用工具 ====================

def _weekday_cn(date_str: str) -> str:
    """由 'YYYY-MM-DD' 计算中文星期，如 '周四'；解析失败返回空串。"""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return "周" + "一二三四五六日"[dt.weekday()]
    except (ValueError, TypeError):
        return ""


def _temp_num(s: str) -> str:
    """从 '高温 15℃' / '低温 7℃' 中提取数字，失败返回空串。"""
    if not s:
        return ''
    m = re.search(r'(\d+)', s)
    return m.group(1) if m else ''


def _md(date_str: str) -> str:
    """由 'YYYY-MM-DD' 取 'M月D日'，失败返回空串。"""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return f"{dt.month}月{dt.day}日"
    except (ValueError, TypeError):
        return ""


def cond_emoji(cond: str) -> str:
    """天气文字 -> emoji 图标。匹配顺序：雷/雹/雪/雨/沙尘/雾/阴/多云/晴。"""
    c = cond or ''
    if '雷' in c:
        return '⛈️'
    if '冰雹' in c or '雹' in c:
        return '🌨️'
    if '雪' in c:
        return '🌨️'
    if '雨' in c:
        return '🌧️'
    if '沙' in c or '尘' in c:
        return '🌫️'
    if '雾' in c or '霾' in c:
        return '🌫️'
    if '阴' in c:
        return '☁️'
    if '多云' in c:
        return '⛅'
    if '晴' in c:
        return '☀️'
    return '🌡️'


def weather_theme(cond: str):
    """天气文字 -> (渐变起始色, 渐变结束色)。用于 Hero 头部着色，按天气类型区分配色。"""
    c = cond or ''
    if '雷' in c:
        return ('#3a4a6b', '#5b6b9e')          # 雷阵雨：深蓝紫
    if '冰雹' in c or '雹' in c:
        return ('#5b9bd5', '#8ec5fc')          # 冰雹：冰蓝
    if '雪' in c:
        return ('#5b9bd5', '#8ec5fc')          # 雪：冰蓝
    if '雨' in c:
        return ('#3b7ddd', '#2c5fb0')          # 雨：蓝
    if '沙' in c or '尘' in c:
        return ('#c2a878', '#a1885f')          # 沙尘：褐黄
    if '雾' in c or '霾' in c:
        return ('#8e9eab', '#b0bec5')          # 雾/霾：灰
    if '阴' in c:
        return ('#7b8aa0', '#9aa7b8')          # 阴：灰蓝
    if '多云' in c:
        return ('#5b9bd5', '#7bb0e0')          # 多云：天蓝
    if '晴' in c:
        return ('#f6b73c', '#f48c3a')          # 晴：暖金
    return ('#667eea', '#764ba2')              # 默认：紫蓝


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

# 生活指数键名 -> emoji 图标
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

def _build_forecast(itboy: Optional[Dict]) -> List[Dict]:
    """构建最近五天：昨天 / 今天 / 未来三天(+1,+2,+3)，今天列高亮。

    数据全部取自 itboy（forecast 含多日、yesterday 含昨日）。
    返回 [{'label','emoji','high','low','today':bool}, ...]
    """
    out = []
    if not isinstance(itboy, Dict):
        return out
    wd = itboy.get('data', {})
    fc = wd.get('forecast', [])
    yest = wd.get('yesterday', {})
    labels = ['今天', '明天', '后天', '大后天']

    # 昨天
    if isinstance(yest, Dict) and yest:
        out.append({
            'label': '昨天',
            'emoji': cond_emoji(yest.get('type', '')),
            'high': _temp_num(yest.get('high', '')),
            'low': _temp_num(yest.get('low', '')),
            'today': False,
        })
    # 今天 + 未来三天
    for i in range(0, 4):
        if i < len(fc):
            t = fc[i]
            ymd = t.get('ymd') or t.get('date')
            if i == 0:
                label = '今天'
            else:
                label = _weekday_cn(ymd) or labels[i]
            out.append({
                'label': label,
                'emoji': cond_emoji(t.get('type', '')),
                'high': _temp_num(t.get('high', '')),
                'low': _temp_num(t.get('low', '')),
                'today': (i == 0),
            })
    return out


def city_block_html(itboy: Optional[Dict], seniverse: Optional[Dict], city_label: str) -> str:
    """将单个城市双源数据整合为移动端优化卡片（单城紧凑，不超一屏）。

    结构：
      [渐变 Hero] 城市 + 日期星期 + 大号温度 + 天气图标 + 一行元信息(风力/湿度/空气/实况)
      [白色卡片] 最近五天横排(昨天/今天高亮/未来三天) + 生活指数两列对齐网格 + 温馨提示
    """
    # ---------- itboy 解析 ----------
    ib_ok = isinstance(itboy, Dict) and bool(itboy)
    if ib_ok:
        city_info = itboy.get("cityInfo", {})
        wd = itboy.get("data", {})
        fc = wd.get("forecast", [])
        today = fc[0] if len(fc) > 0 else {}
        yesterday = wd.get("yesterday", {})
        city_name = f"{city_info.get('parent', '')} {city_info.get('city', '')}".strip() or city_label
        t_type = today.get("type", "")
        t_high = _temp_num(today.get("high", ""))   # 取数字，如 '15'
        t_low = _temp_num(today.get("low", ""))      # 取数字，如 '7'
        y_type = yesterday.get("type", "")
        y_high = _temp_num(yesterday.get("high", ""))
        y_low = _temp_num(yesterday.get("low", ""))
        fx, fl = today.get("fx", ""), today.get("fl", "")
        quality = wd.get("quality", "")
        shidu = wd.get("shidu", "")
        notice = today.get("notice", "")
        today_ymd = today.get("ymd") or today.get("date")
    else:
        city_name = city_label
        t_type = t_high = t_low = y_type = y_high = y_low = ""
        fx = fl = quality = shidu = notice = today_ymd = ""

    # ---------- Hero 头部 ----------
    grad_start, grad_end = weather_theme(t_type)
    hero_emoji = cond_emoji(t_type)

    # 日期星期：优先 itboy 今日 ymd，其次心知 daily[0]
    date_md = _md(today_ymd) if today_ymd else ""
    sx_daily = seniverse.get('daily') if isinstance(seniverse, Dict) else None
    if not date_md and isinstance(sx_daily, list) and sx_daily:
        date_md = _md(sx_daily[0].get('date', ''))
    wk = _weekday_cn(today_ymd) if today_ymd else (
        _weekday_cn(sx_daily[0].get('date', '')) if isinstance(sx_daily, list) and sx_daily else "")
    date_line = f"{date_md} {wk}".strip()

    # 大号温度：优先 itboy 今日高温数字，缺失用心知实况
    sx_now = seniverse.get('now') if isinstance(seniverse, Dict) else None
    sx_temp = sx_now.get('temperature') if isinstance(sx_now, Dict) else None
    hero_temp = t_high or (str(sx_temp) if sx_temp is not None else '--')
    cond_text = t_type or (sx_now.get('text', '') if isinstance(sx_now, Dict) else '')

    # 元信息 chips（风力/湿度/空气/实况；昨日已在五天预报列展示，此处不再重复）
    meta_items = []
    if fx or fl:
        meta_items.append(f"💨 {fx} {fl}".strip())
    if shidu:
        meta_items.append(f"💧 湿度{shidu}")
    if quality:
        meta_items.append(f"🌫️ {quality}")
    if sx_temp is not None:
        meta_items.append(f"📡 实况 {sx_temp}°")
    meta_html = ''.join(
        f'<span style="margin-right:10px;margin-bottom:3px;">{m}</span>' for m in meta_items
    ) if meta_items else '<span style="opacity:0.85;">数据获取中…</span>'

    hero = f'''
<div style="background:linear-gradient(135deg,{grad_start} 0%,{grad_end} 100%);
            border-radius:14px 14px 0 0; padding:12px 14px; color:#fff;">
    <div style="display:flex; justify-content:space-between; align-items:center;
                font-size:12px; opacity:0.95;">
        <span>📍 {city_name}</span>
        <span>{date_line}</span>
    </div>
    <div style="display:flex; align-items:center; margin-top:8px;">
        <div style="font-size:32px; line-height:1; margin-right:10px;">{hero_emoji}</div>
        <div>
            <div style="font-size:32px; font-weight:700; line-height:1;">{hero_temp}°</div>
            <div style="font-size:13px; opacity:0.95; margin-top:2px;">{cond_text} · 低温 {t_low}°</div>
        </div>
    </div>
    <div style="display:flex; flex-wrap:wrap; margin-top:10px; font-size:11px; opacity:0.95;">
        {meta_html}
    </div>
</div>
    '''.strip()

    # ---------- 最近五天（昨天/今天/未来三天），今天高亮 ----------
    forecast = _build_forecast(itboy)
    if forecast:
        cols = []
        for i, d in enumerate(forecast):
            border = '' if i == 0 else 'border-left:1px solid #eee;'
            if d['today']:
                cell = 'background:#fff8e1; border-radius:8px; box-shadow:inset 0 0 0 1px #ffd54f;'
                lbl = 'color:#f57c00; font-weight:700;'
            else:
                cell = ''
                lbl = 'color:#999;'
            cols.append(f'''
<div style="flex:1; {border}">
    <div style="padding:3px 2px; {cell}">
        <div style="font-size:10px; {lbl}">{d['label']}</div>
        <div style="font-size:18px; margin:2px 0; line-height:1;">{d['emoji']}</div>
        <div style="font-size:13px; color:#333; font-weight:600;">{d['high']}°</div>
        <div style="font-size:10px; color:#999;">{d['low']}°</div>
    </div>
</div>'''.strip())
        forecast_html = f'''
<div style="border-top:1px solid #f0f0f0; border-bottom:1px solid #f0f0f0;
            padding:8px 0; display:flex; text-align:center;">
    {''.join(cols)}
</div>'''
        section_forecast = (f'<div style="font-size:12px; font-weight:600; color:#333; '
                            f'margin-bottom:2px;">📅 最近五天</div>{forecast_html}')
    else:
        section_forecast = ('<div style="font-size:12px; color:#999; padding:10px 0;">'
                            '最近五天：暂无数据</div>')

    # ---------- 生活指数（两列网格，图标/分类/内容对齐）----------
    sx_sug = seniverse.get('suggestion') if isinstance(seniverse, Dict) else None
    sug_items = []
    if isinstance(sx_sug, Dict):
        for key, val in sx_sug.items():
            name = SUGGESTION_NAMES.get(key, key)
            emoji = SUGGESTION_EMOJI.get(key, "•")
            brief = val.get('brief', '') if isinstance(val, Dict) else ''
            if brief:
                sug_items.append(f'''
<div style="width:50%; box-sizing:border-box; display:flex; align-items:center;
            padding:4px 4px; font-size:11px;">
    <span style="width:18px; text-align:center; flex:none; margin-right:5px;">{emoji}</span>
    <span style="width:46px; flex:none; color:#333; font-weight:600;">{name}</span>
    <span style="color:#666; flex:1; text-align:left;">{brief}</span>
</div>'''.strip())
    if sug_items:
        section_sug = (f'<div style="font-size:12px; font-weight:600; color:#333; '
                       f'margin:12px 0 2px;">🧭 生活指数</div>'
                       f'<div style="display:flex; flex-wrap:wrap;">{"".join(sug_items)}</div>')
    else:
        section_sug = ('<div style="font-size:12px; color:#999; margin-top:12px;">'
                       '🧭 生活指数：暂无数据</div>')

    # ---------- 温馨提示 ----------
    notice_html = f'<div style="{STYLE_NOTICE}">💡 {notice}</div>' if (ib_ok and notice) else ''

    # ---------- 组装卡片（紧凑，单城不超一屏）----------
    return f'''
<div style="background:#fff; border-radius:14px; overflow:hidden;
            box-shadow:0 2px 8px rgba(0,0,0,0.08); margin-bottom:12px;">
    {hero}
    <div style="padding:12px 14px;">
        {section_forecast}
        {section_sug}
        {notice_html}
    </div>
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

    # 组装完整 HTML（外层容器背景，避免卡片在纯白页面上发飘）
    full_html = f'''
<div style="background:#f5f6fa; padding:12px; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
{''.join(weather_htmls)}

{iciba_to_html(iciba_result)}
</div>
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
