# 开发指南：自定义触发器 (Custom Triggers)

本指南说明如何在 Vibe 模块中使用和扩展触发器。触发器决定了模块的 `on_event` 方法何时被调用。

## 1. 使用现有触发器

在 VibeModule 的 `configure` 方法中，可以通过 `self.triggers` 列表声明触发方式。

### 1.1 时间触发 (Interval/Cron)

```python
from vibe_core.trigger import IntervalTrigger, CronTrigger

class MyModule(VibeModule):
    def configure(self):
        # 每 5 秒触发一次
        self.triggers.append(IntervalTrigger(seconds=5))
        
        # 每天上午 9:30 触发 (需 Scheduler 支持 Cron)
        # self.triggers.append(CronTrigger("30 9 * * *"))
```

### 1.2 主题触发 (Topic)

订阅特定的事件主题。

```python
from vibe_core.trigger import TopicTrigger

class MyModule(VibeModule):
    def configure(self):
        # 订阅行情数据
        self.triggers.append(TopicTrigger(topic="quote.000001.SH"))
```

## 2. 扩展新触发器类型

如果您需要一种新的触发机制（例如：当显卡温度超过 80 度时触发），需要两步走：

### 第一步：定义触发器数据结构

在 `vibe_core/trigger.py` 中继承 `BaseTrigger`。

```python
class GpuTempTrigger(BaseTrigger):
    def __init__(self, threshold: float):
        self.threshold = threshold
    
    def check(self, context) -> bool:
        current_temp = get_gpu_temp() # 伪代码
        return current_temp > self.threshold
```

### 第二步：注册处理逻辑 (Evaluator)

目前系统主要通过 `Scheduler` 处理 `IntervalTrigger`，通过 `EventBus` 处理 `TopicTrigger`。

对于自定义的复杂条件（如 GPU 温度），建议实现一个 **专用的后台服务 (Service)** 来轮询检测，并转换为标准事件。

**示例模式**:

1.  编写 `GpuMonitorService` (参考 Service 开发指南)。
2.  在 Service 中每秒检测温度。
3.  如果超过阈值，发布 `Event(type="ALERT", topic="gpu.overheat")`。
4.  在模块中使用 `TopicTrigger("gpu.overheat")` 进行订阅。

这种模式保持了系统的解耦：**核心引擎不需要知道所有触发器的具体实现逻辑，一切通过事件总线连接。**
