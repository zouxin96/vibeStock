# vibeStock 

vibeStock 是一个基于 Python 的模块化量化交易与行情监控系统。它提供了从实时行情抓取、模块化策略运行、回测引擎到可视化 Web 面板的全套工具。

## 🌟 核心特性

- **模块化设计**: 轻松创建、调试和热加载交易/图表/提醒模块。
- **动态 Web 面板**: 
  - 实时行情监控（Watchlist）。
  - **自由排列**: 支持拖拽排列面板布局（Edit Mode），并自动保存配置。
  - **健康度监控**: UI 实时显示数据采集状态与延迟。
- **多源数据支持**: 
  - 内置 **Sina (免费实时)** 接口，适用于盘中监控。
  - 支持 **Tushare** 历史与专业数据接口。
- **自动化流转**: 
  - 基于 Cron/Interval 的自动触发机制。
  - 自动化的模块扫描与热重载。
- **完善的调试与回测**:
  - 交互式模块调试 CLI。
  - 内置简易回测引擎。

## 📁 项目结构

```text
vibeStock/
├── vibe.py                 # 系统入口 (CLI) - 负责启动、调试、回测及模块管理
├── config/                 # 配置文件目录
│   ├── config.yaml         # 主配置文件 (服务端口、数据源、API Key)
│   ├── dashboard_layout.json # 前端 Dashboard 布局缓存 (自动生成)
│   └── modules/            # 各个模块的独立配置文件
├── data/                   # 本地数据存储
│   ├── daily/              # 日线行情数据 (CSV)
│   ├── financial/          # 财务报表数据
│   └── concepts/           # 概念/行业板块数据
├── modules/                # 策略与监控模块目录 (热加载)
│   ├── core/               # 系统核心模块 (建议保留)
│   ├── prod/               # 生产环境策略 (稳定)
│   └── beta/               # 测试/开发中策略
├── vibe_core/              # 框架核心层
│   ├── context.py          # Context 上下文对象 (API, Logger, EventBus)
│   ├── event.py            # 事件定义 (Event-Driven 核心)
│   ├── module.py           # VibeModule 基类 (所有策略需继承此通过)
│   └── service.py          # 系统服务接口 (IService)
├── vibe_data/              # 数据适配层
│   ├── factory.py          # 数据源工厂模式实现
│   ├── provider.py         # 数据源基类接口
│   └── adapter/            # 具体数据源适配器 (Sina, Tushare, Local)
├── vibe_driver/            # 底层驱动
│   └── scheduler.py        # 轻量级调度器 (替代 APScheduler，零依赖)
├── vibe_services/          # 业务服务层
│   ├── module_loader.py    # 模块加载器 (负责模块扫描、热重载)
│   ├── scheduler_service.py# 调度服务 (包装 vibe_driver)
│   └── web_service.py      # Web 服务封装
├── vibe_server/            # Web 服务器实现
│   ├── server.py           # FastAPI 应用入口 (HTTP API)
│   └── websocket_manager.py# WebSocket 管理器 (实时前端通讯)
├── vibe_backtest/          # 回测引擎
│   └── engine.py           # 基于事件驱动的简易回测引擎
├── vibe_crawler/           # 爬虫框架
│   └── crawler.py          # 爬虫基类 (BaseCrawler)
├── ui/                     # 前端资源
│   └── index.html          # 单页应用入口 (Vue3 + ECharts + SortableJS)
├── templates/              # 代码生成模板
└── 数据接口参考文档/                #  数据接口参考文档
```

## 🚀 快速开始

### 1. 安装依赖
确保已安装 Python 3.9+，并安装必要库：
```bash
pip install fastapi uvicorn requests pyyaml pandas
```

### 2. 启动系统
直接运行根目录下的批处理文件：
```bash
start_vibeStock.bat
```
系统启动后，访问 `http://localhost:8000` 即可查看 Dashboard。

### 3. 配置说明
- **端口修改**: 在 `config/config.yaml` 中修改 `server.port`。
- **数据源**: 在 `config/config.yaml` 中切换 `data.provider` (sina/tushare/local)。

## 🛠️ 开发者工具 (CLI)

- **启动系统**: `python vibe.py run`
- **新建模块**: `python vibe.py new <module_name> -d "描述"`
- **调试模块**: `python vibe.py debug modules/beta/your_module.py`
- **回测模块**: `python vibe.py backtest modules/prod/strategy.py --start 2025-01-01 --end 2025-01-31`
- **列出模块**: `python vibe.py list`

## 📊 数据健康与日志
- **日志文件**: 系统所有运行日志将输出到根目录下的 `vibe_system.log`。
- **数据排查**: 如果 Dashboard 出现红点，请检查 `vibe_system.log` 中关于 `vibe.data.sina` 的错误记录。

## 📜 许可证
本项目仅供学习与研究使用。