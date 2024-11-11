import aiohttp
import asyncio
from bs4 import BeautifulSoup
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.SQLiteManager import SQLiteManager

async def fetch_summary_info(session, code):
    url = f"https://finance.naver.com/item/main.naver?code={code}"
    try:
        print(f"Fetching data for code: {code}")
        async with session.get(url) as response:
            if response.status != 200:
                print(f"Failed to fetch data for code: {code} (Status: {response.status})")
                return code, None  # 네이버 금융 접속 실패 시 None 반환
            response_text = await response.text()
            soup = BeautifulSoup(response_text, 'html.parser')
            summary_info = soup.select_one('#summary_info')

            if summary_info:
                # '기업개요'를 제거하고 텍스트 반환
                text = summary_info.get_text(strip=True).replace('기업개요', '', 1)
                print(f"Successfully fetched data for code: {code}")
                return code, text
            else:
                print(f"No summary info found for code: {code}")
                return code, None  # 기업 개요가 없을 경우 None 반환
    except Exception as e:
        print(f"Error fetching data for code {code}: {e}")
        return code, None  # 예외 발생 시 None 반환

async def update_company_overviews():
    db = SQLiteManager()
    db.open_connection()
    query = "SELECT ISU_NO FROM STOCK_INFO_MASTER_KR_ISU WHERE COMPANY_OVERVIEW is null"
    rows = db.execute_query(query=query, params="")

    print(f"Starting data fetch for {len(rows)} items...")

    tasks = []
    async with aiohttp.ClientSession() as session:
        for row in rows:
            code = row['ISU_NO']
            tasks.append(fetch_summary_info(session, code))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
    print("Fetching completed. Starting database update...")
    
    for code, company_overview in results:
        if not isinstance(company_overview, Exception):
            update_query = "UPDATE STOCK_INFO_MASTER_KR_ISU SET COMPANY_OVERVIEW = ? WHERE ISU_NO = ?"
            db.execute_query(update_query, (company_overview, code))
            print(f"Updated COMPANY_OVERVIEW for code: {code}")

    db.close_connection()
    print("Data fetch and update process completed.")

if __name__ == "__main__":
    asyncio.run(update_company_overviews())

