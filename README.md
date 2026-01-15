# vibeStock 

vibeStock 是一个基于 Python 的模块化量化交易与行情监控系统。它提供了从实时行情抓取、模块化策略运行、回测引擎到可视化 Web 面板的全套工具。

## 🌟 核心特性

- **模块化设计**: 轻松创建、调试和热加载交易/图表/提醒模块。
- **动态 Web 面板**: 
  - 实时行情监控（Watchlist）。
  - **自由排列**: 支持拖拽排列面板布局（Edit Mode），并自动保存配置。
  - **监控**: UI 实时显示数据。
- **多源数据支持**: 
  - 内置 **Sina (免费实时)** 接口，适用于盘中监控。
  - 其他接口。
- **自动化流转**: 
  - 基于 Cron/Interval 的自动触发机制。
  - 自动化的模块扫描与热重载。
- **完善的调试与回测**:
  - 交互式模块调试 CLI。
  - 内置简易回测引擎。

## 📁 项目结构
请看GEMINI.md

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
//请修改python的位置 我这里使用了veighna_studio
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