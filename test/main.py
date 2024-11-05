import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.SQLiteManager import SQLiteManager
from models.FirmInfo import FirmInfo
from modules.DBfi_19 import DBfi_checkNewArticle
from package.json_to_sqlite import insert_json_data_list

async def main():
    r = await DBfi_checkNewArticle()
    insert_json_data_list(r, 'data_main_daily_send')
    firm_info = FirmInfo(
        sec_firm_order=19,
        article_board_order=0
    )
    
    db = SQLiteManager()
    # r = db.fetch_all(table_name='data_main_daily_send')
    r = await db.fetch_daily_articles_by_date(firm_info=firm_info,date_str='20241104')
    print(r)


if __name__ == "__main__":
    asyncio.run(main())