# 开发指南：自定义服务 (Custom Services)

本指南说明如何为 vibeStock 添加后台常驻服务（例如：Telegram 消息机器人、数据自动同步服务、Web 管理后台扩展）。

## 1. 核心概念

服务（Service）是随系统启动而启动的后台进程/线程。它们由 `ServiceManager` 统一管理生命周期（Start/Stop）。

## 2. 开发步骤

### 第一步：创建服务类

在 `vibe_services/` 目录下新建文件（例如 `telegram_bot.py`），继承 `IService`。

```python
import threading
import time
from vibe_core.service import IService

class TelegramBotService(IService):
    def __init__(self, token: str):
        self._name = "telegram_bot"
        self.token = token
        self.running = False
        self._thread = None

    @property
    def name(self) -> str:
        return self._name

    def start(self):
        print(f"[{self.name}] Starting bot with token {self.token}...")
        self.running = True
        # 建议在独立线程中运行，以免阻塞主线程
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        print(f"[{self.name}] Stopping...")
        self.running = False
        if self._thread:
            self._thread.join(timeout=1)

    def _run_loop(self):
        """模拟机器人轮询逻辑"""
        while self.running:
            # print("Checking for new messages...")
            time.sleep(5)
```

### 第二步：注册并启动

在 `vibe.py` 的 `cmd_run` 函数中注册该服务。

**注意**: 目前需要修改 `vibe.py` 代码。未来版本将支持通过配置文件动态加载服务。

```python
# vibe.py

from vibe_services.telegram_bot import TelegramBotService

def cmd_run(args):
    # ... 初始化代码 ...
    
    # 实例化
    tg_service = TelegramBotService(token="123456:ABC-DEF")
    
    # 注册
    ServiceManager.register(tg_service)
    
    # ... 后续代码 (ServiceManager.start_all 会自动启动它) ...
```

## 3. 服务间通信

如果服务需要与其他模块交互（例如 Telegram 接收到指令后触发某个 VibeModule），建议使用 **事件总线 (EventBus)**。

1.  在 Service 中引用 `Context` 或直接引用 `EventBus` 单例（需设计）。
2.  构造 `Event` 并发布。

```python
# 在 Service 内部
evt = Event(type="COMMAND", topic="buy", payload={"code": "000001"})
# event_bus.publish(evt) 
```
