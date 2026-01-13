# 开发指南：Vibe 模块开发 (Module Development)

这是您最常使用的指南。VibeModule 是承载交易策略、监控逻辑、数据分析核心业务的地方。

## 1. 快速开始

使用 CLI 工具生成模板：

```powershell
# 生成一个名为 "ma_strategy" 的模块
python vibe.py new ma_strategy -d "双均线策略"
```

这会在 `modules/ma_strategy.py` 生成基础代码。

## 2. 模块结构详解

```python
from vibe_core.module import VibeModule
from vibe_core.event import Event

class MaStrategy(VibeModule):
    
    def configure(self):
        """
        [配置阶段]
        系统启动时仅调用一次。
        用于：注册触发器、初始化变量、订阅数据。
        """
        # 示例：每分钟运行一次
        self.trigger_on_cron("interval:60")
        
        # 初始化状态变量
        self.ma_fast = 0
        self.ma_slow = 0

    def on_event(self, event: Event):
        """
        [运行阶段]
        每次触发器满足条件时调用。
        """
        # 1. 获取数据
        # self.context 是与系统交互的唯一入口
        price = self.context.data.get_price("000001.SH", date="20230101")
        
        # 2. 执行逻辑
        self.context.logger.info(f"当前价格: {price}")
        
        # 3. 输出结果 (Web 面板)
        self.context.output.dashboard("my_widget", {"price": price})
```

## 3. 常用功能速查

### 3.1 获取数据 (`self.context.data`)

*   `get_price(code, date)`: 获取单点价格。
*   `get_history(code, start, end)`: 获取 DataFrame 格式的历史 K 线。
*   `get_table(name)`: 获取通用表数据（如龙虎榜）。

### 3.2 交互输出 (`self.context.output`)

*   `dashboard(widget_id, data)`: 推送数据到前端网页。
    *   需要在 `ui/index.html` 中有对应的接收逻辑才能显示。
*   `notify(message)`: 发送通知（日志/IM）。
*   `trade(order)`: (规划中) 发送交易指令。

## 4. 调试与测试

### 4.1 独立调试 (`debug`)
不启动整个系统，仅运行当前模块，手动注入数据。

```powershell
# 注入一个模拟事件
python vibe.py debug modules/ma_strategy.py --event '{"type": "TEST", "payload": {}}'
```

### 4.2 交互式调试
如果不带 `--event` 参数，进入命令行交互模式，可以连续输入 JSON 测试逻辑。

```powershell
python vibe.py debug modules/ma_strategy.py
```

### 4.3 历史回测 (`backtest`)
使用真实历史数据验证策略。

```powershell
python vibe.py backtest modules/ma_strategy.py --start "2023-01-01 09:30" --end "2023-01-05 15:00"
```

## 5. 开发建议

1.  **轻量级**: `on_event` 中不要执行耗时过长的阻塞操作（如 `time.sleep(10)`），这会卡住整个系统。如有耗时任务，请放入后台 `Service` 处理。
2.  **异常处理**: 虽然系统有全局捕获，但建议在关键逻辑块使用 `try-except` 保证模块稳定性。
3.  **状态保存**: 如果需要在重启后保留变量（如“持仓成本”），请使用 `self.context.state` 字典进行存取（需系统实现持久化层支持）。
