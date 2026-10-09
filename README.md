# 金融分析的实力辅助

这是一个面向美股的金融分析辅助工具，采用白色极简风格，帮助用户整理行情、新闻和分析结果。

## 项目定位

- **主要市场**：美股
- **界面风格**：白色、简洁、易读
- **开发方式**：基于开源股票智能分析项目进行二次开发

## 项目结构

- `index.html`、`styles.css`、`app.js`：早期白色极简首页演示，供设计参考。
- `apps/dsa-web/`：原项目完整网页版源码，以后正式修改网页从这里开始。
- `api/`、`src/`、`data_provider/`：接口、分析流程与行情数据。
- `apps/dsa-desktop/`：原项目桌面客户端代码。
- `docs/upstream/README-original.md`：原项目使用说明。

当前完整源码已放入本地 `develop` 分支，后续按 [分支协作说明](BRANCHING.md) 开发。

## 本地网页版

安装 Python 与 Node.js 依赖并构建网页后，可以用 `python main.py --webui-only` 启动，浏览器访问 `http://127.0.0.1:8000`。当前演示首页与正式网页版是两套页面；正式网页版由 `apps/dsa-web` 构建并由 Python 服务提供。

## 开源来源

本项目参考并基于 [ZhuLinsen/daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis) 进行二次开发，原项目遵循 MIT License。
