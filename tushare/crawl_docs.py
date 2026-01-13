"""
Tushare 股票相关接口文档爬虫
爬取 https://tushare.pro/document/2 下所有股票相关接口文档
"""

import requests
from bs4 import BeautifulSoup
import time
import os
import json
import html2text

# 股票相关接口的doc_id列表
STOCK_DOCS = {
    # 基础数据
    "股票列表": 25,
    "每日股本（盘前）": 329,
    "交易日历": 26,
    "ST股票列表": 397,
    "沪深港通股票列表": 398,
    "股票曾用名": 100,
    "上市公司基本信息": 112,
    "上市公司管理层": 193,
    "管理层薪酬和持股": 194,
    "北交所新旧代码对照": 375,
    "IPO新股上市": 123,
    "股票历史列表": 262,

    # 行情数据
    "历史日线": 27,
    "实时日线": 372,
    "历史分钟": 370,
    "实时分钟": 374,
    "周线行情": 144,
    "月线行情": 145,
    "复权行情": 146,
    "周月线行情每日更新": 336,
    "周月线复权行情每日更新": 365,
    "复权因子": 28,
    "实时Tick爬虫": 315,
    "实时成交爬虫": 316,
    "实时排名爬虫": 317,
    "每日指标": 32,
    "通用行情接口": 109,
    "每日涨跌停价格": 183,
    "每日停复牌信息": 214,
    "沪深股通十大成交股": 48,
    "港股通十大成交股": 49,
    "港股通每日成交统计": 196,
    "港股通每月成交统计": 197,
    "备用行情": 255,

    # 财务数据
    "利润表": 33,
    "资产负债表": 36,
    "现金流量表": 44,
    "业绩预告": 45,
    "业绩快报": 46,
    "分红送股数据": 103,
    "财务指标数据": 79,
    "财务审计意见": 80,
    "主营业务构成": 81,
    "财报披露日期表": 162,

    # 参考数据
    "前十大股东": 61,
    "前十大流通股东": 62,
    "股权质押统计数据": 110,
    "股权质押明细数据": 111,
    "股票回购": 124,
    "限售股解禁": 160,
    "大宗交易": 161,
    "股票开户数据停": 164,
    "股票开户数据旧": 165,
    "股东人数": 166,
    "股东增减持": 175,

    # 特色数据
    "券商盈利预测数据": 292,
    "每日筹码及胜率": 293,
    "每日筹码分布": 294,
    "股票技术面因子": 296,
    "股票技术面因子专业版": 328,
    "中央结算系统持股统计": 295,
    "中央结算系统持股明细": 274,
    "沪深股通持股明细": 188,
    "股票开盘集合竞价数据": 353,
    "股票收盘集合竞价数据": 354,
    "神奇九转指标": 364,
    "AH股比价": 399,
    "机构调研数据": 275,
    "券商月度金股": 267,

    # 两融及转融通
    "融资融券交易汇总": 58,
    "融资融券交易明细": 59,
    "融资融券标的盘前": 326,
    "转融券交易汇总停": 332,
    "转融资交易汇总": 331,
    "转融券交易明细停": 333,
    "做市借券交易汇总停": 334,

    # 资金流向数据
    "个股资金流向": 170,
    "个股资金流向THS": 348,
    "个股资金流向DC": 349,
    "板块资金流向THS": 371,
    "行业资金流向THS": 343,
    "板块资金流向DC": 344,
    "大盘资金流向DC": 345,
    "沪深港通资金流向": 47,

    # 打板专题数据
    "龙虎榜每日统计单": 106,
    "龙虎榜机构交易单": 107,
    "同花顺涨跌停榜单": 355,
    "涨跌停和炸板数据": 298,
    "涨停股票连板天梯": 356,
    "涨停最强板块统计": 357,
    "同花顺行业概念板块": 259,
    "同花顺概念和行业指数行情": 260,
    "同花顺行业概念成分": 261,
    "东方财富概念板块": 362,
    "东方财富概念成分": 363,
    "东财概念和行业指数行情": 382,
    "开盘竞价成交当日": 369,
    "市场游资最全名录": 311,
    "游资交易每日明细": 312,
    "同花顺App热榜": 320,
    "东方财富App热榜": 321,
    "通达信板块信息": 376,
    "通达信板块成分": 377,
    "通达信板块行情": 378,
    "榜单数据开盘啦": 347,
    "题材数据开盘啦": 350,
    "题材成分开盘啦": 351,
}

BASE_URL = "https://tushare.pro/document/2?doc_id={}"
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

def fetch_doc(doc_id: int, name: str) -> dict:
    """获取单个文档内容"""
    url = BASE_URL.format(doc_id)
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.encoding = 'utf-8'

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            # 查找文档主体内容
            content_div = soup.find('div', class_='document-content') or \
                          soup.find('div', class_='markdown-body') or \
                          soup.find('article') or \
                          soup.find('div', class_='content')

            if content_div:
                # 转换为markdown
                h = html2text.HTML2Text()
                h.ignore_links = False
                h.ignore_images = False
                h.body_width = 0  # 不自动换行
                markdown_content = h.handle(str(content_div))
            else:
                # 如果找不到特定容器，尝试获取整个body
                body = soup.find('body')
                if body:
                    h = html2text.HTML2Text()
                    h.ignore_links = False
                    h.body_width = 0
                    markdown_content = h.handle(str(body))
                else:
                    markdown_content = response.text

            return {
                "success": True,
                "name": name,
                "doc_id": doc_id,
                "url": url,
                "content": markdown_content,
                "html": response.text
            }
        else:
            return {
                "success": False,
                "name": name,
                "doc_id": doc_id,
                "error": f"HTTP {response.status_code}"
            }
    except Exception as e:
        return {
            "success": False,
            "name": name,
            "doc_id": doc_id,
            "error": str(e)
        }

def save_doc(doc: dict):
    """保存文档到本地"""
    if not doc["success"]:
        print(f"跳过失败文档: {doc['name']} - {doc.get('error', 'Unknown error')}")
        return

    # 保存markdown文件
    md_filename = f"{doc['doc_id']}_{doc['name']}.md"
    md_path = os.path.join(OUTPUT_DIR, md_filename)

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(f"# {doc['name']}\n\n")
        f.write(f"来源: {doc['url']}\n\n")
        f.write("---\n\n")
        f.write(doc['content'])

    print(f"已保存: {md_filename}")

def main():
    print(f"开始爬取 Tushare 股票接口文档...")
    print(f"共 {len(STOCK_DOCS)} 个接口")
    print(f"保存目录: {OUTPUT_DIR}")
    print("-" * 50)

    success_count = 0
    fail_count = 0

    for name, doc_id in STOCK_DOCS.items():
        print(f"正在获取: {name} (doc_id={doc_id})...")
        doc = fetch_doc(doc_id, name)

        if doc["success"]:
            save_doc(doc)
            success_count += 1
        else:
            print(f"获取失败: {name} - {doc.get('error', 'Unknown error')}")
            fail_count += 1

        # 避免请求过快
        time.sleep(0.5)

    print("-" * 50)
    print(f"爬取完成! 成功: {success_count}, 失败: {fail_count}")

    # 保存索引文件
    index = {name: doc_id for name, doc_id in STOCK_DOCS.items()}
    index_path = os.path.join(OUTPUT_DIR, "index.json")
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f"索引已保存: index.json")

if __name__ == "__main__":
    main()
