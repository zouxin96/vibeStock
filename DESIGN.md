# vibeStock 系统程序设计文档 (SDD)

**版本**: 1.0
**日期**: 2026-01-13
**状态**: 草案 (Draft)

---

## 1. 系统概述

**vibeStock** 是一个模块化、事件驱动的量化投研与自动化交易辅助系统。其核心设计理念是 **"Vibe Programming"**——即通过标准化的接口和极简的配置，让开发者（用户）能够快速编写、热插拔各种功能模块。

系统旨在解决四大核心需求：多源数据管理、事件驱动处理、非结构化内容分析、以及高度可扩展的模块化业务逻辑，并附带全真的历史回测能力。

---

## 2. 系统架构设计

系统采用 **微内核 + 插件式 (Microkernel + Plugin)** 架构。核心引擎负责底层的消息分发、资源调度和环境模拟，而具体的业务逻辑全部封装在 "Vibe Module" 中。

### 2.1 架构分层

1.  **数据层 (Data Layer)**: 负责与 Tushare、本地文件、数据库交互。
2.  **核心层 (Core Layer - The Vibe Engine)**:
    *   **事件总线 (Event Bus)**: 系统的神经中枢。
    *   **模块加载器 (Module Loader)**: 负责模块的生命周期管理。
    *   **调度器 (Scheduler)**: 处理定时任务。
3.  **服务层 (Service Layer)**:
    *   爬虫服务 (Crawler Service)
    *   回测引擎 (Backtest Engine)
4.  **应用层 (Module Layer)**: 用户编写的具体策略、监控、通知逻辑。
5.  **表现层 (Presentation Layer)**: 监控面板 (Web UI)、消息推送 (IM/SMS)。

---

## 3. 详细功能设计

### 3.1 功能一：数据管理 (Data Manager)

目标：统一数据访问接口，屏蔽底层数据源差异（Tushare/爬虫/CSV），并实现缓存与持久化。

**核心组件：**

*   **DataFactory (工厂模式)**: 根据配置请求不同的数据源适配器。
*   **Adapters (适配器)**:
    *   `TushareAdapter`: 封装 Tushare SDK，处理 API 限流和数据清洗。
    *   `CustomSourceAdapter`: 预留给未来接入通达信、东财等数据源。
*   **Repository (仓储)**:
    *   **热数据**: Redis (实时行情、信号状态)。
    *   **冷数据**: ClickHouse 或 TimescaleDB (历史K线、Tick数据)。
    *   **元数据**: SQLite/MySQL (股票列表、模块配置)。

**接口定义示例：**
```python
class IDataProvider:
    def get_price(self, code, date): pass
    def get_history(self, code, start, end): pass
    def save_data(self, data_type, content): pass
```

### 3.2 功能二：驱动消息与分时触发 (Driver & Trigger System)

目标：建立全系统的"心跳"，将外部变化转化为内部标准事件。

**驱动模式：**

1.  **时间驱动 (Time Driver)**:
    *   基于 Cron 表达式（如 `0 15 * * 1-5` 收盘时触发）。
    *   市场状态驱动（开盘前、交易中、收盘后）。
2.  **数据驱动 (Data Driver)**:
    *   **Tick Stream**: 监听实时行情接口，价格变动即触发。
    *   **Signal Stream**: 当某个指标（如 MACD 金叉）计算完成时触发。
3.  **消息驱动 (Message Driver)**:
    *   外部 Webhook 调用。
    *   系统内部指令（如管理员发送 `reload_modules`）。

**事件总线逻辑：**
`EventBus.publish(topic="quote.000001.SH", payload={price: 12.5, time: ...})`

### 3.3 功能三：内容爬取与分析 (Content ETL)

目标：处理非结构化数据（新闻、研报、截图），转化为可供模块消费的结构化信号。

**流程：**

1.  **采集 (Crawl)**:
    *   `ArticleCrawler`: 抓取财联社、雪球等文字流。
    *   `ImageCrawler`: 抓取龙虎榜截图、分时图截图。
2.  **处理 (Process)**:
    *   **NLP**: 提取关键词、情感打分、实体识别（提及哪只股票）。
    *   **OCR**: 识别图片中的表格数据。
3.  **归档 (Archive)**:
    *   原始文件存入 `storage/raw/` (对应目录结构中的 `tushare/` 或新建 `crawled_data/`)。
    *   解析结果存入数据库，并推送到事件总线：`EventBus.publish(topic="news.sentiment", payload={code: "00700", score: 0.9})`。

### 3.4 功能四：模块管理 (Vibe Module System)

这是实现 "Vibe 编程" 的核心。模块必须标准化，以便系统可以自动发现、加载、运行和监控。

**模块定义 (BaseModule):**

一个标准的 Vibe 模块包含以下属性：
*   **Metadata**: 名称、版本、描述、作者。
*   **Triggers**: 该模块订阅什么事件？（配置式，而非硬编码）。
*   **Logic**: `on_event(context, event)` 回调函数。
*   **Outputs**: 模块产生的结果去向。

**触发方式配置 (vibe.yaml 示例):**
```yaml
modules:
  - name: "EarlyMorningMonitor"
    type: "daemon" # 常驻
    triggers:
      - type: "cron"
        value: "0 9 * * 1-5" # 每天9点
      - type: "market_event"
        value: "open_auction" # 集合竞价
  - name: "InstantPriceAlert"
    type: "reactive" # 响应式
    triggers:
      - type: "quote_tick"
        symbol: "600519.SH"
        condition: "price > 2000"
```

**输出方式 (Output Channels):**
1.  **Dashboard**: 推送 WebSocket 到前端 React/Vue 面板。
2.  **Notification**: 调用钉钉/飞书/Telegram 机器人接口。
3.  **Instruction**: 生成交易指令（模拟或实盘接口）。

**模块热加载**: 系统监听 `modules/` 目录，文件变动时自动重新加载 Python Class。

### 3.5 特别功能：历史数据回测 (Time Travel Backtest)

目标：利用已存档的数据（如目录中 `tushare/` 下的 `历史分钟.md` 或数据库数据）模拟“某一天”。

**实现原理 (Context Isolation):**

1.  **模拟时钟 (Mock Clock)**: 系统时间不再取 `datetime.now()`，而是由回测引擎控制的 `context.current_time`。
2.  **事件重放 (Event Replay)**:
    *   读取某天的 Tick/分钟数据。
    *   按时间戳顺序将数据灌入 **事件总线**。
3.  **模块无感**:
    *   模块逻辑不需要修改。它看到的 `event.price` 就是当时的真实价格。
    *   模块发出的 "Notify" 或 "Trade" 指令会被拦截，转入 **回测统计器**，而不是真实发送给微信。

---

## 4. 技术选型建议

*   **编程语言**: Python 3.10+ (生态丰富，适合数据处理)。
*   **数据存储**:
    *   **PostgreSQL**: 核心关系型数据。
    *   **Redis**: 消息队列 (Pub/Sub) 及 缓存。
    *   **HDF5 / Parquet**: 存储大量历史回测数据（高性能文件存储）。
*   **Web 框架**: FastAPI (高性能异步，适合 WebSocket 推送)。
*   **前端**: React + Ant Design Pro (监控面板)。

---

## 5. 模块开发示例 (Vibe Script)

这是开发者日常编写代码的样子：

```python
from vibe_core import VibeModule, Context, Event

class DragonTigerMonitor(VibeModule):
    """
    模块描述: 监控每日龙虎榜，发现机构净买入超过1亿的股票
    """
    
    def configure(self):
        # 定义触发条件：每天收盘后处理数据
        self.trigger_on_cron("30 15 * * 1-5") 
        # 或者定义订阅： self.subscribe_topic("data.dragon_tiger")

    def on_trigger(self, ctx: Context, event: Event):
        # 1. 获取数据 (ctx 自动处理了是回测模式还是实盘模式)
        # 获取当日龙虎榜数据
        df = ctx.data.get_dragon_tiger_list(date=ctx.now.date())
        
        # 2. 逻辑分析
        targets = df[df['net_buy_amount'] > 100000000]
        
        if not targets.empty:
            msg = f"今日机构大额净买入: {len(targets)} 只"
            
            # 3. 输出 (多渠道)
            # 输出到监控面板
            ctx.output.to_dashboard("main_panel", table=targets)
            # 发送消息通知
            ctx.output.to_messenger(msg)
            # 生成关注指令
            for code in targets['code']:
                 ctx.output.emit_instruction("add_to_watch_list", code)

```
