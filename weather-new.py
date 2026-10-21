# -*- coding: utf-8 -*-
"""
天气推送脚本（重新设计版 · v2）

设计目标：
  1. 移动端优先、科技现代视觉（渐变 Hero + 玻璃卡片 + 等宽数字 + 柔和阴影）。
  2. 微信 WebView 兼容：全部内联样式，不用 class/<style>/JS；flex 用 margin 兜底兼容旧版。
  3. 单条推送字符 ≤ 20000（PushPlus 限制）：标记紧凑、minify 去空白、生活指数精简。
  4. 代码精简复用：删除旧版未使用的 STYLE_* 常量，统一芯片/卡片组件，渲染逻辑收敛。

数据源：itboy（主，含多日预报/昨日/空气质量/湿度/风力） + 心知天气（补充实况温度与生活指数）。
"""

import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

import requests

# ==================== 配置 ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 推送通道（环境变量读取，未配置则跳过对应通道）
PUSHPLUSSCKEY = os.environ.get('PUSHPLUSSCKEY')
SERVERSCKEY = os.environ.get('SERVERSCKEY')

# 心知天气（免费版）补充数据源，私钥从环境变量读取，切勿明文写入文件
SENIVERSE_API_KEY = os.environ.get('SENIVERSE_API_KEY')
# itboy 城市编码 -> 心知查询位置。蓬莱在心知免费版无权限(AP010006)，映射至烟台。
SENIVERSE_CITY_MAP = {
    '101120101': 'jinan',     # 济南
    '101120504': 'yantai',    # 蓬莱（心知无该城市，用烟台）
    '101121201': 'dongying',  # 东营
    '101010300': 'beijing',   # 北京
}

DEFAULT_CITY_CODES = '101120101,101120504,101121201,101010300'
# 预报展示天数上限（含昨天/今天/未来三天 = 5 行）。实测 4 城 5 行约 1.9 万字符，仍在 2 万限制内。
MAX_FORECAST_DAYS = 5

# ==================== 通用工具 ====================

def _weekday_cn(date_str: str) -> str:
    """'YYYY-MM-DD' -> '周四'，失败返回空串。"""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return "周" + "一二三四五六日"[dt.weekday()]
    except (ValueError, TypeError):
        return ""


def _temp_num(s: str) -> str:
    """从 '高温 15℃' 提取数字，失败返回空串。"""
    if not s:
        return ''
    m = re.search(r'(\d+)', s)
    return m.group(1) if m else ''


def _md(date_str: str) -> str:
    """'YYYY-MM-DD' -> 'M月D日'，失败返回空串。"""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return f"{dt.month}月{dt.day}日"
    except (ValueError, TypeError):
        return ""


def cond_emoji(cond: str) -> str:
    """天气文字 -> emoji 图标。"""
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
    """天气文字 -> (渐变起始色, 渐变结束色)，按天气类型区分配色（科技冷调为主）。"""
    c = cond or ''
    if '雷' in c:
        return ('#3a4a6b', '#5b6b9e')
    if '冰雹' in c or '雹' in c:
        return ('#2b6cb0', '#4a9bd5')
    if '雪' in c:
        return ('#2b6cb0', '#6fb1e0')
    if '雨' in c:
        return ('#2563a8', '#3b82c4')
    if '沙' in c or '尘' in c:
        return ('#9a7b4f', '#c2a878')
    if '雾' in c or '霾' in c:
        return ('#5a6b7a', '#8e9eab')
    if '阴' in c:
        return ('#5a6b82', '#8696ad')
    if '多云' in c:
        return ('#3b7bd5', '#74a9e8')
    if '晴' in c:
        return ('#f59e0b', '#f97316')
    return ('#4f5bd5', '#7b5bf0')


# ==================== 数据源：itboy + 每日英语 ====================

def fetch_weather(city_code: str) -> Optional[Dict]:
    """获取单个城市天气（itboy 主数据源）。失败返回 None。"""
    try:
        url = f'http://t.weather.itboy.net/api/weather/city/{city_code}'
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 200:
                logger.info(f"获取成功: {city_code}")
                return data
            logger.warning(f"API返回错误: {city_code}, status={data.get('status')}")
            return None
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
        logger.warning(f"获取每日英语失败 [{response.status_code}]")
        return None
    except Exception as e:
        logger.error(f"获取每日英语异常: {e}")
        return None


# ==================== 数据源：心知天气（免费版补充） ====================

SUGGESTION_NAMES = {
    "car_washing": "洗车", "dressing": "穿衣", "comfort": "舒适度",
    "sport": "运动", "uv": "紫外线", "travel": "旅游",
    "fishing": "钓鱼", "air_pollution": "空气污染", "allergy": "过敏",
    "umbrella": "雨伞", "flu": "感冒", "air_conditioner": "空调",
    "sunscreen": "防晒", "makeup": "化妆", "traffic": "交通",
    "spiritual": "心情",
}
SUGGESTION_EMOJI = {
    "car_washing": "🚗", "dressing": "👕", "comfort": "😌",
    "sport": "🏃", "uv": "☀️", "travel": "🧳",
    "fishing": "🎣", "air_pollution": "🏭", "allergy": "🤧",
    "umbrella": "☂️", "flu": "🤒", "air_conditioner": "❄️",
    "sunscreen": "🧴", "makeup": "💄", "traffic": "🚦",
    "spiritual": "💗",
}
# 生活指数展示优先级（免费版仅返回部分，按此顺序取前 N 个，保证关键信息靠前）
SUGGESTION_PRIORITY = [
    "dressing", "umbrella", "car_washing", "sport", "flu",
    "uv", "comfort", "travel", "air_pollution", "allergy",
    "traffic", "makeup", "sunscreen", "air_conditioner", "spiritual", "fishing",
]


def fetch_seniverse(location: str) -> Optional[Dict]:
    """获取心知天气（免费版）：实况 + 3天预报 + 生活指数。未配置/失败返回 None。"""
    if not SENIVERSE_API_KEY:
        logger.warning("未配置 SENIVERSE_API_KEY，跳过心知数据源")
        return None
    if not location:
        return None
    base = "https://api.seniverse.com/v3"
    common = {"key": SENIVERSE_API_KEY, "location": location, "language": "zh-Hans", "unit": "c"}
    result = {}
    try:
        r = requests.get(f"{base}/weather/now.json", params=common, timeout=10)
        if r.status_code == 200:
            res = r.json().get('results')
            if res:
                result['now'] = res[0].get('now', {})
                result['location_name'] = res[0].get('location', {}).get('name')
        r = requests.get(f"{base}/weather/daily.json", params={**common, "days": 3}, timeout=10)
        if r.status_code == 200:
            res = r.json().get('results')
            if res:
                result['daily'] = res[0].get('daily', [])
                result.setdefault('location_name', res[0].get('location', {}).get('name'))
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


# ==================== HTML 渲染（科技现代 · 移动端优先） ====================

# 组件：芯片（Hero 上的玻璃质感标签 / 内容区的浅色标签）
def _chip(text: str, dark: bool = False) -> str:
    if not text:
        return ''
    if dark:
        bg = 'rgba(255,255,255,.16)'
        border = '1px solid rgba(255,255,255,.3)'
        color = '#fff'
    else:
        bg = '#eef1f8'
        border = '1px solid #e4e8f2'
        color = '#5b6172'
    return (f'<span style="background:{bg};border:{border};color:{color};'
            f'padding:2px 8px;border-radius:20px;font-size:10px;'
            f'margin:0 5px 0 0;display:inline-block;">{text}</span>')


def _build_forecast(itboy: Optional[Dict], seniverse: Optional[Dict], n_days: int) -> List[Dict]:
    """构建近期天气：昨天 / 今天 / 未来三天（明天、后天、大后天）。

    优先 itboy（forecast[0] 为今天），itboy 数据不足时用心知 daily 兜底。
    返回 [{'label','type','emoji','high','low','today'}, ...]，最多 n_days 行。
    """
    out = []
    wd = itboy.get('data', {}) if isinstance(itboy, Dict) else {}
    fc = wd.get('forecast', []) or []
    yest = wd.get('yesterday', {}) or {}
    labels = ['今天', '明天', '后天', '大后天']

    if isinstance(yest, Dict) and yest:
        out.append({
            'label': '昨天', 'type': yest.get('type', ''),
            'emoji': cond_emoji(yest.get('type', '')),
            'high': _temp_num(yest.get('high', '')), 'low': _temp_num(yest.get('low', '')),
            'today': False,
        })
    for i in range(0, 4):
        if i < len(fc):
            t = fc[i]
            out.append({
                'label': labels[i], 'type': t.get('type', ''),
                'emoji': cond_emoji(t.get('type', '')),
                'high': _temp_num(t.get('high', '')), 'low': _temp_num(t.get('low', '')),
                'today': (i == 0),
            })

    # itboy 数据不足（如仅当日）时，用心知 daily 补足未来天数
    if len(out) < n_days and isinstance(seniverse, Dict):
        sx_daily = seniverse.get('daily') or []
        for d in sx_daily:
            if len(out) >= n_days:
                break
            date = d.get('date', '')
            label = _weekday_cn(date) or _md(date)
            out.append({
                'label': label, 'type': d.get('text_day', ''),
                'emoji': cond_emoji(d.get('text_day', '')),
                'high': d.get('high', ''), 'low': d.get('low', ''),
                'today': (len(out) == 0),
            })

    return out[:n_days]


def city_block_html(itboy: Optional[Dict], seniverse: Optional[Dict], city_label: str,
                    n_sug: int = 4, n_days: int = MAX_FORECAST_DAYS) -> str:
    """单城市卡片：渐变 Hero（城市/大温度/元信息）+ 白卡（多日预报 + 生活指数 + 贴士）。

    n_sug：生活指数展示条数（0 表示不展示）；n_days：预报行数上限。用于超限时降级。
    """
    ib_ok = isinstance(itboy, Dict) and bool(itboy)
    if ib_ok:
        city_info = itboy.get("cityInfo", {})
        wd = itboy.get("data", {})
        fc = wd.get("forecast", [])
        today = fc[0] if len(fc) > 0 else {}
        city_name = f"{city_info.get('parent', '')} {city_info.get('city', '')}".strip() or city_label
        t_type = today.get("type", "")
        quality = wd.get("quality", "")
        shidu = wd.get("shidu", "")
        fx, fl = today.get("fx", ""), today.get("fl", "")
        notice = today.get("notice", "")
    else:
        city_name = city_label
        t_type = quality = shidu = fx = fl = notice = ""

    sx_now = seniverse.get('now') if isinstance(seniverse, Dict) else None
    sx_temp = sx_now.get('temperature') if isinstance(sx_now, Dict) else None

    # Hero 渐变（科技冷调，按天气着色）
    gs, ge = weather_theme(t_type)
    hero_bg = f"linear-gradient(135deg, {gs} 0%, {ge} 100%)"

    # Hero 大温度：优先心知实况，否则 itboy 今日高温
    hero_temp = sx_temp if sx_temp is not None else _temp_num(today.get('high', '') if ib_ok else '')
    hero_temp = hero_temp if hero_temp != '' else '—'

    # 元信息芯片（风力/湿度/空气；大温度已含实况，故不再重复）
    chips = []
    if fx or fl:
        chips.append(f"💨 {fx} {fl}".strip())
    if shidu:
        chips.append(f"💧 湿度 {shidu}")
    if quality:
        chips.append(f"🌫️ {quality}")
    meta_html = ''.join(_chip(c, dark=True) for c in chips) or '<span style="opacity:0.85;font-size:10px;">数据获取中…</span>'

    hero = f'''
<div style="background:{hero_bg};border-radius:18px 18px 0 0;padding:16px 18px;color:#fff;overflow:hidden;">
    <div style="display:flex;align-items:baseline;justify-content:space-between;">
        <div style="font-size:13px;font-weight:600;flex:1;">📍 {city_name}</div>
        <div style="font-size:34px;font-weight:700;line-height:1;font-family:-apple-system,'SF Mono',Consolas,monospace;">{hero_temp}°</div>
        <div style="font-size:34px;font-weight:700;line-height:1;margin-left:10px;white-space:nowrap;"><span style="font-size:26px;">{cond_emoji(t_type)}</span> {t_type or '—'}</div>
    </div>
    <div style="display:flex;flex-wrap:wrap;margin-top:10px;">{meta_html}</div>
</div>'''.strip()

    # ---------- 近期天气（精致表格，今天行高亮，紧凑省字符）----------
    forecast = _build_forecast(itboy, seniverse, n_days)
    if forecast:
        rows = []
        for d in forecast:
            if d['today']:
                tr_style = 'background:#eef2ff;color:#4f46e5;font-weight:700;border-top:1px solid #c7d2fe;'
            else:
                tr_style = 'border-top:1px solid #f0f0f0;'
            rows.append(
                f'<tr align="center" style="{tr_style}">'
                f'<td style="padding:7px 0;">{d["label"]}</td>'
                f'<td>{d["emoji"]} {d["type"] or "—"}</td>'
                f'<td style="color:#e74c3c;font-weight:600;">{d["high"] or "—"}°</td>'
                f'<td style="color:#3498db;">{d["low"] or "—"}°</td>'
                f'</tr>')
        section_forecast = (
            f'<div style="display:flex;align-items:center;margin-bottom:8px;">'
            f'<span style="width:3px;height:13px;background:linear-gradient(180deg,#667eea,#764ba2);'
            f'border-radius:2px;margin-right:7px;"></span>'
            f'<span style="font-size:12px;font-weight:600;color:#1f2433;">近期天气</span></div>'
            f'<table cellpadding="0" style="width:100%;border-collapse:collapse;font-size:11px;color:#444;">'
            f'<tr align="center" style="color:#9aa0ad;font-weight:500;font-size:10px;">'
            f'<th style="padding:4px 0;">日期</th><th>天气</th>'
            f'<th style="color:#e74c3c;">高温</th><th style="color:#3498db;">低温</th></tr>'
            f'{"" .join(rows)}</table>')
    else:
        section_forecast = '<div style="font-size:12px;color:#999;padding:8px 0;">近期天气：暂无数据</div>'

    # ---------- 今日贴士（itboy notice）----------
    notice_html = ''
    if notice:
        notice_html = (f'<div style="display:flex;align-items:flex-start;margin-top:12px;'
                       f'background:#fff7ed;border:1px solid #ffe2bf;border-radius:10px;padding:8px 10px;">'
                       f'<span style="font-size:13px;margin-right:5px;">💡</span>'
                       f'<span style="font-size:11px;color:#b45309;line-height:1.5;">{notice}</span></div>')

    # ---------- 生活指数（胶囊标签行，按优先级取前 n_sug 个，紧凑省字符）----------
    sx_sug = seniverse.get('suggestion') if isinstance(seniverse, Dict) else None
    sug_chips = []
    if isinstance(sx_sug, Dict) and n_sug > 0:
        ordered = sorted(sx_sug.keys(), key=lambda k: SUGGESTION_PRIORITY.index(k)
                         if k in SUGGESTION_PRIORITY else 999)
        for key in ordered[:n_sug]:
            val = sx_sug[key]
            brief = val.get('brief', '') if isinstance(val, Dict) else ''
            if not brief:
                continue
            name = SUGGESTION_NAMES.get(key, key)
            emoji = SUGGESTION_EMOJI.get(key, "•")
            sug_chips.append(
                f'<span style="background:#eef1f8;border:1px solid #e4e8f2;color:#5b6172;'
                f'padding:3px 8px;border-radius:9px;font-size:10px;margin:0 5px 5px 0;'
                f'display:inline-block;white-space:nowrap;">{emoji} {name}·{brief}</span>')
    if sug_chips:
        section_sug = (f'<div style="display:flex;align-items:center;margin:4px 0 8px;">'
                       f'<span style="width:3px;height:13px;background:linear-gradient(180deg,#667eea,#764ba2);'
                       f'border-radius:2px;margin-right:7px;"></span>'
                       f'<span style="font-size:12px;font-weight:600;color:#1f2433;">生活指数</span></div>'
                       f'<div style="display:flex;flex-wrap:wrap;">{"".join(sug_chips)}</div>')
    else:
        section_sug = '' if n_sug <= 0 else ('<div style="font-size:12px;color:#999;margin-top:10px;">'
                                            '🧭 生活指数：暂无数据</div>')

    content = f'''
<div style="background:#fff;border-radius:0 0 18px 18px;padding:14px 16px;">
    {section_forecast}
    {notice_html}
    {section_sug}
</div>'''.strip()

    return f'''
<div style="background:#fff;border-radius:18px;overflow:hidden;box-shadow:0 6px 18px rgba(20,30,60,0.08);margin-bottom:14px;">
    {hero}
    {content}
</div>'''.strip()


def header_html() -> str:
    """顶部科技感标题条。"""
    now = datetime.now()
    date_line = f"{now.month}月{now.day}日 {_weekday_cn(now.strftime('%Y-%m-%d'))}"
    return f'''
<div style="background:linear-gradient(135deg,#1e293b 0%,#0f172a 100%);border-radius:18px;padding:16px 18px;color:#fff;margin-bottom:14px;box-shadow:0 6px 18px rgba(15,23,42,0.15);">
    <div style="font-size:16px;font-weight:700;letter-spacing:1px;">🌤️&nbsp; {date_line} 天气播报</div>
</div>'''.strip()


def iciba_to_html(data: Dict) -> str:
    """每日英语 -> 渐变引用卡。无数据返回空串。"""
    if not data:
        return ""
    return f'''
<div style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);border-radius:18px;padding:16px 18px;color:#fff;box-shadow:0 6px 18px rgba(102,126,234,0.18);">
    <div style="font-size:11px;font-weight:600;opacity:0.85;margin-bottom:6px;letter-spacing:1px;">📖 DAILY ENGLISH</div>
    <div style="font-size:14px;font-weight:600;line-height:1.5;">{data.get("content", "")}</div>
    <div style="font-size:11px;opacity:0.80;margin-top:6px;line-height:1.5;">{data.get("note", "")}</div>
</div>'''.strip()


def minify_html(html: str) -> str:
    """压缩 HTML：仅折叠标签间空白，不改变标签内样式与文本（视觉不变，压到 2 万字内）。"""
    return re.sub(r'>\s+<', '><', html)


# ==================== 推送通道 ====================

def push_plus(title: str, content: str) -> bool:
    """PushPlus 推送（HTML 模板）。未配置令牌返回 False。"""
    try:
        if not PUSHPLUSSCKEY:
            logger.error("未设置 PUSHPLUSSCKEY")
            return False
        url = 'http://www.pushplus.plus/send'
        body = json.dumps({
            "token": PUSHPLUSSCKEY, "title": title,
            "content": content, "template": "html"
        }).encode('utf-8')
        response = requests.post(url, data=body,
                                headers={"Content-Type": "application/json"}, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('code') == 200:
                logger.info("PushPlus推送成功")
                return True
            logger.error(f"PushPlus推送失败: {result.get('msg')}")
            return False
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
        response = requests.post(
            f"https://sc.ftqq.com/{SERVERSCKEY}.send",
            data={"text": title, "desp": content.replace('\n', '\n\n')}, timeout=10)
        if response.status_code == 200:
            logger.info("Server酱推送成功")
            return True
        logger.error(f"Server酱推送失败 [{response.status_code}]")
        return False
    except Exception as e:
        logger.error(f"Server酱推送异常: {e}")
        return False


# ==================== 主程序 ====================

# PushPlus 单条推送内容上限（字符）
PUSH_CHAR_LIMIT = 20000
# 安全余量：留 300 字符缓冲，避免边界抖动导致截断
CHAR_SAFE_MARGIN = 300


def _compose(weather_results: List, seniverse_results: List, city_codes: List[str],
             iciba_result: Optional[Dict], n_sug: int, n_days: int) -> str:
    """按给定的「生活指数条数 / 预报天数」组装完整 HTML。"""
    weather_htmls = []
    for i, result in enumerate(weather_results):
        ci = result.get("cityInfo", {}) if isinstance(result, Dict) else {}
        city_label = f"{ci.get('parent', '')} {ci.get('city', '')}".strip() or city_codes[i]
        if not isinstance(result, Dict) or not result:
            logger.error(f"获取城市 {city_codes[i]} 天气失败")
        weather_htmls.append(city_block_html(result, seniverse_results[i], city_label, n_sug, n_days))
    return f'''
<div style="background:linear-gradient(180deg,#eef1f8 0%,#f5f6fa 100%);padding:12px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
{header_html()}
{''.join(weather_htmls)}
{iciba_to_html(iciba_result)}
</div>'''.strip()


def build_html() -> str:
    """拉取数据并组装完整 HTML（不推送），供预览/测试复用。

    内置超限保护：若组装结果超出 PushPlus 字符上限，按「先减生活指数、再减预报天数」
    的顺序逐级降级，确保永不超限。
    """
    city_codes_str = os.environ.get('WEATHER_CITY_CODES', DEFAULT_CITY_CODES)
    city_codes = [c.strip() for c in city_codes_str.split(',') if c.strip()]
    logger.info(f"将获取 {len(city_codes)} 个城市的天气: {city_codes}")

    weather_results, seniverse_results = [], []
    for code in city_codes:
        result = fetch_weather(code)
        weather_results.append(result)
        sen_loc = SENIVERSE_CITY_MAP.get(code)
        seniverse_results.append(fetch_seniverse(sen_loc) if sen_loc else None)

    iciba_result = fetch_iciba()

    # 降级阶梯：(生活指数条数, 预报天数)，从最完整到最精简
    ladder = [(4, 5), (3, 5), (2, 5), (0, 5), (0, 4), (0, 3), (0, 2)]
    budget = PUSH_CHAR_LIMIT - CHAR_SAFE_MARGIN
    for n_sug, n_days in ladder:
        html = minify_html(_compose(weather_results, seniverse_results,
                                    city_codes, iciba_result, n_sug, n_days))
        if len(html) <= budget:
            if (n_sug, n_days) != ladder[0]:
                logger.warning(f"内容超限，已降级：生活指数={n_sug}条 预报={n_days}天")
            return html
    # 极端兜底：全部降级后仍超限，直接返回最小版本
    logger.error("内容严重超限，已降级至最小版本")
    return minify_html(_compose(weather_results, seniverse_results,
                                city_codes, iciba_result, 0, 2))


def main():
    start_time = time.time()
    logger.info("=" * 50)
    logger.info("天气推送脚本启动")
    logger.info("=" * 50)

    full_html = minify_html(build_html())

    # PREVIEW=1 时只写本地预览文件、不推送（用于设计校验）
    if os.environ.get('PREVIEW') == '1':
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'weather_preview.html')
        with open(out, 'w', encoding='utf-8') as f:
            f.write(full_html)
        logger.info(f"[PREVIEW] 已写入 {out}，字符数={len(full_html)}")
        return True

    title = "🌤️ 今日天气播报"
    success = True
    if PUSHPLUSSCKEY and not push_plus(title, full_html):
        success = False
    if SERVERSCKEY and not server_push(title, full_html):
        success = False

    elapsed = time.time() - start_time
    logger.info("=" * 50)
    logger.info(f"执行完成，耗时: {elapsed:.2f}秒，字符数: {len(full_html)}")
    logger.info(f"推送结果: {'成功' if success else '失败'}")
    logger.info("=" * 50)
    return success


if __name__ == '__main__':
    def main_handler(event, context):
        main()
        return '执行完成'

    main()
