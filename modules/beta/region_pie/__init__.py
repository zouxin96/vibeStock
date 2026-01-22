from vibe_core.module import VibeModule
from vibe_core.event import Event
import pandas as pd
import time
import os
import threading

class RegionPieModule(VibeModule):
    """
    地区/省份涨停分布饼图 (基于系统 StockInfoAdapter + SQLite)
    Limit-Up Stock Distribution by Province
    """
    # Ensure data providers are ready before starting
    dependencies = ['StockInfoModule', 'AkShareDataModule']
    
    def __init__(self, context=None):
        super().__init__()
        if context:
            self.context = context
        self.id = "region_pie"
        self.name = "Region Pie Chart"
        self.interval = 10  
        
        self.last_log_time = 0
        self.is_fetching = False
        
    def configure(self):
        self.context.logger.info(f"{self.name} started.")
        self.process()
        self.context.register_cron(self, f"interval:{self.interval}")

    def on_event(self, event: Event):
        if event.type == "TIMER":
            self.process()

    def fetch_missing_info(self, codes):
        """后台通过系统接口触发网络获取 (only_cache=False)"""
        if self.is_fetching: return
        self.is_fetching = True
        
        try:
            updates = 0
            for code in codes:
                # 这里调用不带 only_cache=True，会触发网络请求并写入 SQLite
                info = self.context.data.get_stock_info(code)
                if info and 'provincial_name' in info:
                    updates += 1
                
                # 礼貌性延迟，避免封 IP
                time.sleep(0.5)
            
            if updates > 0:
                self.context.logger.info(f"Fetched info for {updates} new stocks via Adapter.")
                
        except Exception as e:
            self.context.logger.error(f"Error in fetch_missing_info: {e}")
        finally:
            self.is_fetching = False

    def process(self):
        if self.context.data is None: return

        try:
            # 1. 获取涨停池
            if not hasattr(self.context.data, 'get_limit_up_pool'):
                return

            df_limit = self.context.data.get_limit_up_pool()
            
            if df_limit is None or df_limit.empty:
                if time.time() - self.last_log_time > 60:
                     self.context.logger.info("Limit pool empty.")
                     self.last_log_time = time.time()
                return

            # 2. 提取代码列表
            code_col = '代码' if '代码' in df_limit.columns else 'code'
            if code_col not in df_limit.columns:
                return
                
            current_codes = [str(c).zfill(6) for c in df_limit[code_col]]
            
            # 3. 统计省份分布
            region_counts = {}
            missing_codes = []
            
            for code in current_codes:
                # 关键修改：
                # 使用 only_cache=True，这会查询 SQLite，速度极快 (毫秒级)
                # 不会阻塞主线程，也不会触发网络请求
                info = self.context.data.get_stock_info(code, only_cache=True)
                
                province = info.get('provincial_name') if info else None
                
                if province:
                    region_counts[province] = region_counts.get(province, 0) + 1
                else:
                    missing_codes.append(code)
            
            # 4. 异步获取缺失信息
            # 如果发现有 SQLite 里没有的股票，启动后台线程去联网抓取
            if missing_codes and not self.is_fetching:
                threading.Thread(target=self.fetch_missing_info, args=(missing_codes,), daemon=True).start()

            # 5. 构造 Payload
            sorted_regions = sorted(region_counts.items(), key=lambda x: x[1], reverse=True)
            payload = [{"name": name, "value": count} for name, count in sorted_regions]
                
            # Broadcast to the module ID (standard pattern)
            self.context.broadcast_ui("region_pie", payload)
            
            # Log
            now = time.time()
            if now - self.last_log_time >= 60:
                mapped_count = len(current_codes) - len(missing_codes)
                self.context.logger.info(f"[RegionPie] Broadcasted. Mapped: {mapped_count}/{len(current_codes)}")
                self.last_log_time = now

        except Exception as e:
            self.context.logger.error(f"RegionPie process error: {e}")

    @classmethod
    def get_ui_config(cls):
        return {
            "id": "region_pie",
            "title": "Limit-Up Distribution by Province",
            "component": "region-pie-widget",
            "default_col_span": "col-span-1",
            "config_default": {},
            "config_description": "Pie chart showing number of limit-up stocks per province using Snowball info.",
            "script_path": "widget.js"
        }
