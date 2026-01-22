import sys
import os
import json
import time
import logging
import pandas as pd

# 确保项目根目录在 sys.path 中
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from vibe_core.data.adapter.akshare_adapter import AKShareAdapter

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TagLoader")

def load_existing_data(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_data(data, filepath):
    # 确保目录存在
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def build_stock_tag_map():
    adapter = AKShareAdapter()
    data_file = os.path.join(project_root, "data", "stock_tags.json")
    
    # 加载现有数据 (用于增量更新或结构保持)
    stock_tags = load_existing_data(data_file)
    # 格式: code -> {"n": name, "c": [concepts], "i": [industries]}
    # 为了节省空间，使用简写: n=name, c=concepts, i=industries

    # ==========================
    # 1. 处理行业 (Industry)
    # ==========================
    logger.info("开始获取行业板块列表...")
    df_industries = adapter.get_em_sectors()
    if df_industries.empty:
        logger.error("无法获取行业列表")
    else:
        logger.info(f"获取到 {len(df_industries)} 个行业板块")
        total = len(df_industries)
        
        for idx, row in df_industries.iterrows():
            board_name = row['板块名称']
            board_code = row['板块代码']
            
            logger.info(f"[{idx+1}/{total}] 处理行业: {board_name} ({board_code})")
            
            # 获取成份股
            try:
                df_cons = adapter.get_industry_cons(board_name)
                if df_cons.empty:
                    logger.warning(f"  - 行业 {board_name} 无成份股")
                    continue
                    
                for _, stock_row in df_cons.iterrows():
                    code = str(stock_row['代码'])
                    name = stock_row['名称']
                    
                    if code not in stock_tags:
                        stock_tags[code] = {"n": name, "c": [], "i": []}
                    
                    # 更新名称 (以最新为准)
                    stock_tags[code]["n"] = name
                    
                    # 添加行业标签
                    if board_name not in stock_tags[code]["i"]:
                        stock_tags[code]["i"].append(board_name)
                        
                time.sleep(0.3) # 避免速率限制
                
            except Exception as e:
                logger.error(f"  - 处理行业 {board_name} 失败: {e}")

    # 保存中间结果
    save_data(stock_tags, data_file)

    # ==========================
    # 2. 处理概念 (Concept)
    # ==========================
    logger.info("开始获取概念板块列表...")
    df_concepts = adapter.get_em_concepts()
    if df_concepts.empty:
        logger.error("无法获取概念列表")
    else:
        logger.info(f"获取到 {len(df_concepts)} 个概念板块")
        total = len(df_concepts)
        
        for idx, row in df_concepts.iterrows():
            board_name = row['板块名称']
            board_code = row['板块代码']
            
            logger.info(f"[{idx+1}/{total}] 处理概念: {board_name} ({board_code})")
            
            # 简单去重或跳过已处理的逻辑可以加在这里，但考虑到成份股可能变动，建议全量刷新
            
            try:
                df_cons = adapter.get_concept_cons(board_name)
                if df_cons.empty:
                    # 有些概念可能暂时没数据，或者接口不稳定
                    logger.warning(f"  - 概念 {board_name} 无成份股或获取失败")
                    time.sleep(0.5) 
                    continue
                
                for _, stock_row in df_cons.iterrows():
                    code = str(stock_row['代码'])
                    name = stock_row['名称']
                    
                    if code not in stock_tags:
                        stock_tags[code] = {"n": name, "c": [], "i": []}
                    
                    stock_tags[code]["n"] = name
                    
                    if board_name not in stock_tags[code]["c"]:
                        stock_tags[code]["c"].append(board_name)
                
                time.sleep(0.5) # 概念请求较多，稍微慢一点
                
                # 每50个概念保存一次，防止程序崩溃丢失所有进度
                if idx % 50 == 0:
                    save_data(stock_tags, data_file)
                    logger.info("  (自动保存进度)")

            except Exception as e:
                logger.error(f"  - 处理概念 {board_name} 失败: {e}")
                time.sleep(1)

    # 最终保存
    save_data(stock_tags, data_file)
    logger.info(f"处理完成。共包含 {len(stock_tags)} 只股票的标签数据。")

if __name__ == "__main__":
    try:
        build_stock_tag_map()
    except KeyboardInterrupt:
        logger.info("用户中断，已保存现有进度。")
