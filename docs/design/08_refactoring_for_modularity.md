# 架构重构：全面模块化设计 (Modularization Refactoring)

## 1. 目标
响应用户需求，对系统进行深度解耦，实现 **数据源**、**触发器** 和 **系统服务** 的全面插件化。

## 2. 服务层模块化 (Service Layer)
**现状**: `vibe.py` 硬编码了 `SimpleScheduler` 和 `Uvicorn` 的启动逻辑。
**改进**:
*   定义 `IService` 接口 (Start/Stop/Status)。
*   创建 `ServiceManager` 负责服务的生命周期管理。
*   `Scheduler` 和 `WebServer` 变为普通的服务插件。
*   便于未来增加 `TelegramBotService`, `DataSyncService` 等。

## 3. 数据层模块化 (Data Layer)
**现状**: `DataFactory` 包含硬编码的 `if/else` 逻辑。
**改进**:
*   引入 **Provider Registry** (注册表机制)。
*   通过 `config.yaml` 中的 `data.provider` 字段动态加载类。
*   允许第三方编写 `MySQLProvider` 或 `EastMoneyProvider` 并注册进系统，无需修改核心代码。

## 4. 触发器模块化 (Trigger System)
**现状**: 触发逻辑分散在 `Context` 和 `Module` 中，仅支持简单的 Cron。
**改进**:
*   抽象 `BaseTrigger` 类。
*   实现 `TimeTrigger` (Cron/Interval), `DataTrigger` (Price Condition), `EventTrigger` (Topic Subscription).
*   模块定义触发器时不再调用具体方法，而是声明触发器对象列表。

## 5. 重构后的模块代码示例

```python
class MyStrategy(VibeModule):
    def configure(self):
        # 声明式触发器
        self.triggers = [
            IntervalTrigger(seconds=3),
            TopicTrigger(topic="market.open"),
            PriceTrigger(symbol="000001.SH", condition="> 10.0")
        ]
```
