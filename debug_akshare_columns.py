import akshare as ak
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)

def check_columns():
    print("Checking THS Concepts...")
    try:
        df = ak.stock_board_concept_name_ths()
        print(f"THS Concepts Columns: {df.columns.tolist()}")
        if not df.empty:
            print(f"First row: {df.iloc[0].to_dict()}")
    except Exception as e:
        print(f"THS Concepts Error: {e}")

    print("\nChecking EM Concepts...")
    try:
        df = ak.stock_board_concept_name_em()
        print(f"EM Concepts Columns: {df.columns.tolist()}")
        if not df.empty:
            print(f"First row: {df.iloc[0].to_dict()}")
    except Exception as e:
        print(f"EM Concepts Error: {e}")

if __name__ == "__main__":
    check_columns()
