# 模块设计：Vibe 模块管理 (Module System)

## 1. 概述
模块管理系统 (`vibe_core`) 是用户与系统交互的主要界面。它定义了 "Vibe Programming" 的标准：用户只需关注业务逻辑，无需关心底层的调度、数据连接和消息分发。

## 2. 模块生命周期

1.  **Discovery (发现)**: 扫描 `modules/` 目录下的 `.py` 文件。
2.  **Load (加载)**: 动态 import，校验是否继承自 `VibeModule`。
3.  **Init (初始化)**: 调用 `initialize()`，注入 `Context`。
4.  **Register (注册)**: 根据模块声明的 `triggers` 将其注册到事件总线。
5.  **Run (运行)**: 触发时执行 `on_event()`。
6.  **Unload (卸载)**: 热更新或系统关闭时清理资源。

## 3. 编程接口 (SDK)

### 3.1 BaseModule (基类)

```python
class VibeModule:
    def initialize(self, context):
        """初始化，配置触发器"""
        self.context = context
    
    def on_event(self, event):
        """核心逻辑回调"""
        pass

    def on_error(self, error):
        """错误处理"""
        pass
```

### 3.2 Context (上下文对象)
`Context` 是模块与外界交互的唯一桥梁，包含：
*   `ctx.data`: 数据访问接口 (Ref: 01_data_management)。
*   `ctx.logger`: 标准日志接口。
*   `ctx.output`: 输出接口 (Ref: Output Channels)。
*   `ctx.state`: 模块内部持久化状态（重启不丢失）。

### 3.3 输出渠道 (Output Channels)
*   `ctx.output.dashboard(title, data)`: 推送到前端 Web 面板。
*   `ctx.output.notify(msg, level='info')`: 发送 IM 消息。
*   `ctx.output.trade(order)`: 发送交易指令（仅在实盘/模拟盘有效）。

## 4. 模块管理控制台
提供 CLI 命令：
*   `vibe list`: 列出所有已加载模块及状态。
*   `vibe reload <module_name>`: 热重载指定模块。
*   `vibe new <name>`: 根据模板创建新模块文件。
