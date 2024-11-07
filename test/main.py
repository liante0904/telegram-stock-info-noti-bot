import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from modules.DBfi_19 import DBfi_checkNewArticle
from models.FirmInfo import FirmInfo
from models.SQLiteManager import SQLiteManager

async def main():
    firm_info = FirmInfo(
        sec_firm_order=19,
        article_board_order=0
    )

    r = await DBfi_checkNewArticle()
    if r:
        db = SQLiteManager()
        db.insert_json_data_list(r, 'data_main_daily_send')
    
    # r = db.fetch_all(table_name='data_main_daily_send')
    r = await db.fetch_daily_articles_by_date(firm_info=firm_info,date_str='20241104')
    print(r)


if __name__ == "__main__":
    asyncio.run(main())