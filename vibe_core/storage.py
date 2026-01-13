import os
import csv
import logging
import datetime
from typing import List, Dict, Any, Union
import pandas as pd

class CSVStorageService:
    """
    Simple file-based storage service using CSV.
    Allows modules to save data to 'data/storage/' directory.
    """
    
    def __init__(self, root_dir: str = "data/storage"):
        self.root_dir = root_dir
        self.logger = logging.getLogger("vibe.storage")
        
        if not os.path.exists(self.root_dir):
            os.makedirs(self.root_dir)

    def save_record(self, category: str, record: Dict[str, Any]):
        """
        Append a single record (dict) to a daily CSV file in the category folder.
        File format: data/storage/{category}/{date}.csv
        """
        today = datetime.datetime.now().strftime("%Y%m%d")
        category_dir = os.path.join(self.root_dir, category)
        
        if not os.path.exists(category_dir):
            os.makedirs(category_dir)
            
        file_path = os.path.join(category_dir, f"{today}.csv")
        
        # Check if file exists to write header
        file_exists = os.path.exists(file_path)
        
        try:
            with open(file_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=record.keys())
                if not file_exists:
                    writer.writeheader()
                writer.writerow(record)
        except Exception as e:
            self.logger.error(f"Failed to save record to {file_path}: {e}")

    def save_dataframe(self, category: str, filename: str, df: pd.DataFrame, append: bool = False):
        """
        Save a DataFrame to a specific file.
        """
        category_dir = os.path.join(self.root_dir, category)
        if not os.path.exists(category_dir):
            os.makedirs(category_dir)
            
        file_path = os.path.join(category_dir, filename)
        
        try:
            mode = 'a' if append else 'w'
            header = not append or not os.path.exists(file_path)
            df.to_csv(file_path, mode=mode, header=header, index=False)
            self.logger.info(f"Saved DataFrame to {file_path}")
        except Exception as e:
            self.logger.error(f"Failed to save DataFrame to {file_path}: {e}")

    def load_dataframe(self, category: str, filename: str) -> pd.DataFrame:
        """
        Load a DataFrame from storage.
        """
        file_path = os.path.join(self.root_dir, category, filename)
        if os.path.exists(file_path):
            try:
                return pd.read_csv(file_path)
            except Exception as e:
                self.logger.error(f"Failed to load {file_path}: {e}")
        return pd.DataFrame()
