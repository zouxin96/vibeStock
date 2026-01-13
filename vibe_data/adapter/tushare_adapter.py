from ..provider import IDataProvider
# Placeholder for Tushare implementation
class TushareAdapter(IDataProvider):
    def __init__(self, token: str):
        self.token = token
        
    def get_price(self, code, date):
        return None
        
    def get_history(self, code, start_date, end_date):
        import pandas as pd
        return pd.DataFrame()
        
    def get_table(self, table_name, date=None):
        import pandas as pd
        return pd.DataFrame()
