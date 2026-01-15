python使用 C:\veighna_studio\python.exe
注释请写中文
```
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