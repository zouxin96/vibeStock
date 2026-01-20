# 创建新模块流程指南 (Module Creation Workflow)

本文档旨在指导开发者（及 AI 助手）如何规范、高效地创建一个新的 vibeStock 功能模块。

## 1. 需求分析 (Requirement Analysis)
在开始写代码之前，首先要明确用户的核心需求：
*   **目标 (Goal)**: 用户想看到什么？(例如：涨停股的地区分布、某个指标的实时走势)
*   **形式 (Form)**: 以什么形式展示？(例如：列表、饼图、热力图、K线图)
*   **频率 (Frequency)**: 数据需要多快更新？(例如：实时/10秒、分钟级、日线级)

## 2. 数据源评估 (Data Source Assessment)
思考实现该功能所需的具体数据字段。
*   **核心字段**: 例如：股票代码、最新价、涨跌幅、所属地区、成交量。
*   **辅助字段**: 例如：昨收价（用于计算涨幅）、总市值（用于排序）。

## 3. 数据可用性检查 (Data Availability Check)
检查当前的 `vibe_data` 层是否已经提供了所需数据。

*   **查看 `HybridDataProvider` (`vibe_data/hybrid.py`)**:
    *   检查是否有现成的方法，如 `get_limit_up_pool()`, `get_em_sectors()`。
*   **查看底层适配器 (`vibe_data/adapter/akshare/...`)**:
    *   如果 Hybrid 没有，检查 AKShare/Sina 适配器里是否有类似功能的函数。
    *   *技巧*: 可以在 `adapter` 目录搜索相关的 API 关键字。

### 🚨 关键决策点 (Decision Point)
**如果发现现有适配器不支持所需数据：**
1.  **不要急于在模块里写死 API 调用** (避免 `import akshare` 直接调用)。
2.  **询问用户**: "当前适配器缺少 [某某数据] 的接口，是否允许我修改 `AKShareAdapter` 来添加这个功能？"
3.  **修改适配器**:
    *   在 `vibe_data/adapter/akshare/` 下的相关文件 (如 `market.py`, `meta.py`) 中添加标准方法 (如 `get_area_cons()`)。
    *   确保方法包含异常处理 (`try-except`) 和日志记录。

## 4. 模块实现 (Implementation)
确认数据准备就绪后，开始编写模块代码。

### 4.1 创建目录结构
在 `modules/beta/` (测试) 或 `modules/prod/` (生产) 下创建新目录：
```
modules/beta/my_new_module/
├── __init__.py      # 后端逻辑
└── widget.js        # 前端 UI
```

### 4.2 后端编写 (`__init__.py`)
*   **继承**: `class MyModule(VibeModule)`
*   **初始化**: 设置 `self.interval` (刷新频率)。
*   **配置**: 在 `configure()` 中注册定时任务 `self.context.register_cron(...)` 并立即运行一次 `process()`。
*   **处理**: 在 `process()` 中获取数据、处理逻辑、并通过 `self.context.broadcast_ui("频道ID", data)` 推送。
*   **UI配置**: 实现 `get_ui_config()` 返回组件元数据。

### 4.3 前端编写 (`widget.js`)
*   **组件定义**: 定义 Vue 组件。
*   **订阅**: 在 `onMounted` 中订阅 `window.vibeSocket.subscribe("频道ID", ...)`。
*   **销毁**: 在 `onUnmounted` 中取消订阅。
*   **注册**: 将组件注册到 `window.VibeComponentRegistry`。
*   **复用**: 尽量复用 `ui/widgets.js` 中的 `BaseListWidget`, `BasePieWidget` 等，除非有特殊定制需求。

## 5. 验证与测试 (Verification)
*   **重启服务**: 修改了后端代码通常需要重启。
*   **观察日志**: 确认模块启动日志、数据获取日志是否正常。
*   **检查 UI**: 确认 Widget 是否能加载，数据是否显示。
*   **边界情况**: 考虑数据为空、网络超时等情况的容错处理。
