# VibeStock Project Context (GEMINI)

本文档定义了 VibeStock 项目的核心上下文、开发规范及架构概览。AI 助手在开始任务前应优先读取此文件。

## 1. 环境与基础配置 (Environment) 
*   **Operating System**: Windows (win32)
*   **Project Root**: `D:\vibeStock\vibeStock\vibeStock`
*   **UI Framework**: Vue3 + ECharts + SortableJS (Single File: `ui/index.html`)
*   **Backend Framework**: Python (FastAPI + WebSocket)

## 2. 核心开发规范 (Core Mandates)

*   **语言要求 (Language)**:
    *   代码注释必须使用 **中文 (Chinese)**。
    *   Commit Message 建议使用中文或清晰的英文。
    *   与用户交流使用 **中文**。
*   **代码风格 (Style)**:
    *   遵循 PEP8 规范。
    *   类型提示 (Type Hinting) 是必须的。
    *   **架构职责 (Architecture Responsibility)**:
     *  Module(模块) ，位于 `modules/core/`，`modules/prod/` 或 `modules/beta/`
    *   **Data Module (数据模块)**: 封装外部数据源 (如 AKShare)。提供标准化的数据服务和状态监控。
    *   **Strategy Module (策略模块)**: 负责业务逻辑。**严禁**直接调用外部 API，必须通过 `self.context.data` 或订阅数据模块。
*   **错误处理**:
    *   所有外部 API 调用必须包含 `try-except` 块并记录日志。

## 3. 快速开始 (Quick Start)

### 常用命令
```bash
# 启动系统 (开启 Web 服务与调度器)
python vibe.py run

# 启动调试模式 (更详细的日志)
python vibe.py run --debug

# 运行测试
python -m pytest tests/
```

### 模块开发
*   **指南**: 详见 `modules/GEMINI.md` (必读：创建新UI/策略/数据模块的标准流程)。
*   **目录规范**:
    *   `modules/core/`: 系统级模块 (数据源、底层服务)，随系统启动，不可热卸载。
    *   `modules/prod/`: 经过验证的稳定策略/功能。
    *   `modules/beta/`: 开发测试中的模块，支持热重载。

## 4. 系统架构 (Architecture)

系统采用 **微内核 + 插件式** 架构，核心功能已整合至 `vibe_core` 包内：

*   **核心层 (`vibe_core/`)**: 
    *   `context.py`, `module.py`: 定义了核心基类与上下文环境。
    *   `data/`: 数据层 (Hybrid Facade)，负责数据路由与聚合。
    *   `server/`: 服务层，包含 FastAPI 与 WebSocket 接口。
    *   `services/`: 业务服务，负责模块加载 (`loader`) 与调度 (`scheduler`)。
    *   `driver/`: 驱动层，处理底层触发机制。
*   **模块层 (`modules/`)**: 动态加载的业务逻辑，分为系统核心 (`core`)、稳定版 (`prod`) 和实验版 (`beta`)。

## 5. 目录结构索引 (File Structure)

```text
vibeStock/
├── vibe.py                 # [Entry] 系统入口 (CLI)
├── tray_monitor.py         # [Monitor] 托盘监控程序
├── run_monitor_service.py  # [Service] 监控服务运行脚本
├── config/                 # [Config] 配置文件
│   ├── config.yaml         # 主配置 (端口, Key)
│   ├── instances.yaml      # 实例管理配置
│   ├── dashboard_layout.json # UI 布局持久化
│   └── modules/            # 模块独立配置
├── modules/                # [Plugins] 业务模块化目录
│   ├── core/               # -> 系统核心模块 (Data Providers)
│   ├── prod/               # -> 生产级模块
│   ├── beta/               # -> 实验性模块
│   └── GEMINI.md           # -> 模块开发指南
├── vibe_core/              # [Kernel] 框架核心
│   ├── data/               # -> 数据路由与聚合层
│   ├── server/             # -> Web 服务 (FastAPI/WS)
│   ├── services/           # -> 核心服务 (Loader/Scheduler)
│   ├── crawler/            # -> 爬虫子系统
│   └── backtest/           # -> 回测引擎
├── ui/                     # [Frontend] 前端资源 (Vue3 + ECharts)
├── data/                   # [Storage] 本地数据 (CSV/JSON/DB)
├── logs/                   # [Logs] 系统与监控日志
├── module_templates/       # [Templates] 模块开发模板
└── tests/                  # [Tests] 测试用例
```
