# 分支协作说明

## 分支职责

| 分支 | 用途 |
| --- | --- |
| `main` | 稳定版本，准备给用户使用的代码 |
| `develop` | 日常开发汇总分支 |
| `feature/web-ui` | 网页界面和页面样式 |
| `feature/backend` | FastAPI 后端和接口 |
| `feature/data-sources` | 美股行情、新闻和数据源 |
| `feature/ai-models` | AI 模型、提示词和分析流程 |
| `feature/settings` | 设置、密钥和用户配置 |
| `feature/deployment` | 本地启动、服务器和部署 |
| `release/v0.1.0` | 第一个可运行版本的发布准备 |

## 修改流程

1. 从 `develop` 创建对应的功能分支。
2. 在功能分支完成一项相对完整的修改。
3. 在本地运行和检查后合并回 `develop`。
4. 多项功能合并并确认可用后，再合并到 `main`。
5. 发布前从 `develop` 创建 `release/*` 分支。

示例：

```text
main
└── develop
    ├── feature/web-ui
    ├── feature/backend
    ├── feature/data-sources
    ├── feature/ai-models
    ├── feature/settings
    └── feature/deployment
```

分支名称表示工作方向，真正的修改仍然要在对应分支的提交中完成。网页、后端和数据源需要联调时，再把相关功能分支合并到 `develop` 一起运行。
