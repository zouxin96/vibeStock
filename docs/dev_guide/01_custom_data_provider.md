# 开发指南：自定义数据源 (Custom Data Provider)

本指南说明如何为 vibeStock 接入新的数据源（例如：币安 API、东方财富爬虫、本地数据库等）。

## 1. 核心概念

数据层采用 **适配器模式**。所有数据源必须实现 `IDataProvider` 接口，并通过 `DataFactory` 注册到系统中。

## 2. 开发步骤

### 第一步：创建适配器类

在 `vibe_data/adapter/` 目录下新建文件（例如 `my_custom_adapter.py`），继承 `IDataProvider`。

```python
from typing import Optional
import pandas as pd
from vibe_data.provider import IDataProvider

class MyCustomAdapter(IDataProvider):
    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        # 初始化连接...

    def get_price(self, code: str, date: str) -> Optional[float]:
        """
        获取指定日期单价
        """
        # 实现你的逻辑，例如请求 API
        print(f"Fetching price for {code} from MySource...")
        return 100.0 

    def get_history(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取历史 K 线
        返回格式必须包含: date, open, close, high, low, volume
        """
        # 返回空的 DataFrame 示例
        return pd.DataFrame()

    def get_table(self, table_name: str, date: Optional[str] = None) -> pd.DataFrame:
        """
        获取通用数据表
        """
        return pd.DataFrame()
```

### 第二步：注册适配器

在 `vibe_data/factory.py` 或你的插件入口文件中进行注册。

```python
from vibe_data.factory import DataFactory
from vibe_data.adapter.my_custom_adapter import MyCustomAdapter

# 注册名称 "mysource"
DataFactory.register("mysource", MyCustomAdapter)
```

### 第三步：配置使用

修改 `config/config.yaml`，指定使用该数据源：

```yaml
data:
  provider: "mysource"
  # 其他传递给 __init__ 的参数
  tushare_token: "..." 
```

## 3. 最佳实践

*   **统一返回格式**: 无论底层数据源如何，`get_history` 必须返回标准的 Pandas DataFrame，列名统一为小写（`open`, `close`, `high`, `low`...）。
*   **缓存**: 建议在适配器内部实现简单的内存缓存或 Redis 缓存，减少 API 请求。
*   **错误处理**: 网络请求失败时应捕获异常并打印日志，尽量避免直接崩溃，可返回 `None` 或空 DataFrame。
