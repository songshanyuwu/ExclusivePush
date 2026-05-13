# 📺 新闻联播 + 天气 每日推送

定时抓取央视新闻联播文字稿和天气信息，通过 PushPlus 推送至微信。

## 功能特性

### 📰 新闻联播文字稿
- **异步并发抓取**：使用 aiohttp 异步获取，速度更快
- **自动目录生成**：每条新闻带编号目录，便于快速浏览
- **视频链接直达**：标题旁附视频链接，可直接观看
- **智能分批推送**：内容过长自动分批，保持阅读体验
- **精美排版**：渐变标题栏、卡片式内容、内联样式确保兼容

### 🌤️ 每日天气推送
- **多城市支持**：可配置多个城市同时查询
- **精美天气卡片**：温度、湿度、空气质量一目了然
- **每日英语**：附带英语美文，提升学习

## 项目结构

```
├── news_plus_optimized.py   # 新闻联播抓取脚本
├── weather_optimized.py     # 天气查询脚本
├── EP-daily-task.yml       # GitHub Actions 工作流配置
├── requirements.txt        # Python 依赖
└── README.md               # 本文件
```

## 快速开始

### 1. 准备工作

#### 获取 PushPlus Token
1. 访问 [PushPlus 官网](https://pushplus.plus/)，微信扫码登录
2. 在个人中心获取 Token

#### 获取天气 API Key（可选）
如需天气功能，需申请心知天气 API：
1. 注册 [心知天气](https://www.seniverse.com/)
2. 获取 API Key

### 2. 配置 GitHub Secrets

在 GitHub 仓库 Settings → Secrets and variables → Actions 中添加：

| Secret 名称 | 说明 |
|------------|------|
| `PUSHPLUSSCKEY` | PushPlus Token（必填） |
| `SENIVERSE_KEY` | 心知天气 API Key（可选） |

### 3. 启用 GitHub Actions

推送代码到 GitHub 后，Workflow 会自动运行：
- 每天早上 8:00（北京时间）自动执行
- 可在 Actions 页面手动触发测试

## 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `PUSHPLUSSCKEY` | PushPlus Token | 必填 |
| `SENIVERSE_KEY` | 心知天气 API Key | 可选 |
| `PUSHPLUS_MAX_LENGTH` | 单批最大字符数 | 19000 |

### 自定义配置

#### 修改推送时间
编辑 `.github/workflows/EP-daily-task.yml` 中的 cron 表达式：
```yaml
schedule:
  - cron: '0 0 * * *'  # 北京时间每天 8:00
```

#### 修改天气城市
编辑 `weather_optimized.py` 中的 `CITY_CODES` 列表：
```python
CITY_CODES = {
    '北京': '101010100',
    '上海': '101020100',
    # 添加更多城市...
}
```

#### 调整分批长度
如果推送失败或分批过多，可调整 `PUSHPLUS_MAX_LENGTH`：
```yaml
env:
  PUSHPLUS_MAX_LENGTH: '18000'  # 减小可减少每批长度
```

## 依赖

```
aiohttp>=3.9.0      # 异步 HTTP 客户端
lxml>=4.9.0         # HTML 解析
tenacity>=8.2.0     # 重试机制
requests>=2.28.0    # HTTP 请求（用于推送）
```

## 运行日志

查看 GitHub Actions 运行日志，可了解：
- 抓取的新闻条数
- 各批次 HTML 长度
- 推送成功/失败状态

## 常见问题

### Q: 推送显示"服务端验证错误"
A: HTML 内容过长，减少 `PUSHPLUS_MAX_LENGTH` 值，或检查是否超出 PushPlus 限制（~20000字符）

### Q: 部分新闻抓取失败
A: 网络波动导致，脚本会自动重试 3 次

### Q: 如何本地测试？
A:
```bash
pip install -r requirements.txt
export PUSHPLUSSCKEY='你的Token'
python news_plus_optimized.py
```

## 免责声明

- 本项目仅供个人学习使用
- 新闻内容版权归央视新闻所有
- 请勿用于商业用途

## License

MIT License
