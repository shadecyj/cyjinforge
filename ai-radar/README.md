# AI Radar — 前沿 AI 资讯自动聚合站

每日自动收集最前沿 AI 技术论文、GitHub 热门项目、新闻资讯和技术讨论，特别聚焦 AI 伴侣相关（情感计算、对话系统、自我意识、自我进化等）内容。

## 数据来源

| 来源 | 类型 |
|------|------|
| arXiv (cs.AI, cs.CL, cs.HC) | 论文 |
| Semantic Scholar | 论文 |
| Hugging Face Daily Papers | 论文 |
| Papers With Code | 论文 |
| GitHub Trending | 开源项目 |
| Hacker News | 技术讨论 |
| Reddit r/MachineLearning, r/artificial | 讨论 |
| MIT Technology Review | 新闻 |
| TechCrunch AI | 新闻 |
| 机器之心 | 中文资讯 |
| 量子位 | 中文资讯 |

## 快速开始

### 本地运行

```bash
pip install -r requirements.txt
python fetch.py
# 用浏览器打开 index.html 查看结果
```

### 自动更新

推送到 GitHub 仓库后，GitHub Actions 每天 UTC 0:00 自动运行采集脚本，更新 `data.json`。

开启 GitHub Pages：
1. Settings → Pages
2. Source: Deploy from a branch → main → / (root)
3. Save

## 项目结构

```
ai-radar/
├── fetch.py              # 数据采集脚本
├── requirements.txt      # Python 依赖
├── index.html            # 静态站点
├── data.json             # 最新采集数据
├── archive/              # 每日历史快照
├── .github/workflows/
│   └── daily-fetch.yml   # GitHub Actions 定时任务
└── README.md
```

## 伴侣聚焦关键词

覆盖情感计算、对话系统、个性化、人机交互、AI 意识、自我进化、自我思考、自我反省等领域的关键词，自动标记高亮。

## License

MIT
