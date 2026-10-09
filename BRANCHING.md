# 分支协作说明

## 分支职责

| 分支 | 用途 |
| --- | --- |
| `main` | 稳定版本，准备给用户使用的代码 |
| `develop` | 日常开发汇总分支 |
| `feature/具体任务` | 只在开始一项修改时创建，例如 `feature/us-homepage` |
| `release/版本号` | 需要准备发布时创建，例如 `release/v0.1.0` |

## 修改流程

1. 在 VS Code 中打开项目文件夹，进入“源代码管理”，确认当前是 `develop`。
2. 开始一项具体工作时，从 `develop` 创建一个 `feature/*` 分支。
3. 在功能分支完成一项相对完整的修改并检查。
4. 合并回 `develop`，确认各功能能一起运行。
5. 准备发布时创建 `release/*`，验收后合并到 `main`。

示例：

```text
main
└── develop
    ├── feature/us-homepage（按需创建）
    ├── feature/ai-provider（按需创建）
    └── feature/cloud-deploy（按需创建）
```

在 VS Code 左下角点击分支名称可以切换或新建分支；左侧“源代码管理”可查看改动并提交。每次只处理一个具体任务，修改网页时通常在 `apps/dsa-web/`，修改模型时通常在 `src/` 与设置配置中。

`main` 目前仍保留最初的演示首页。完整原项目源码在本地 `develop`，尚未推送至 GitHub。
