import asyncio
import aiohttp
import json
import ssl
import re
from datetime import datetime
import os
import sys
import urllib.parse as urlparse
from loguru import logger

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.db_factory import get_db
from modules.DBfi_19 import extract_dbfi_pdf_url, HEADERS_TEMPLATE, ssl_context

async def fix_dbfi_urls():
    db = get_db()
    
    # 1. 수정 대상 조회
    # - TELEGRAM_URL이 올바른 형식이 아니거나
    # - pdf_sync_status가 2(성공)가 아닌 경우 (pdf_url 재생성 필요)
    query = """
    SELECT report_id, "key", "telegram_url", "pdf_url", pdf_sync_status
    FROM "tbl_sec_reports"
    WHERE sec_firm_order = 19
      AND (
          "telegram_url" NOT LIKE 'https://whub.dbsec.co.kr/pv/gate%%'
          OR pdf_sync_status != 2
      )
    ORDER BY report_id DESC
    """
    
    try:
        rows = await db.execute_query(query)
        logger.info(f"Found {len(rows)} DBfi reports to fix.")
    except Exception as e:
        logger.error(f"Failed to query reports: {e}")
        return

    if not rows:
        logger.info("No reports need fixing.")
        return

    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context), timeout=timeout) as session:
        for row in rows:
            report_id = row['report_id']
            key_url = row['key']
            old_tg = row['telegram_url']
            old_pdf = row['pdf_url']
            
            logger.info(f"Processing report_id={report_id}, key={key_url}")
            
            try:
                # 2. key URL에서 encoded_url 가져오기
                async with session.post(key_url, headers=HEADERS_TEMPLATE) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to fetch key_url for report_id={report_id}")
                        continue
                    
                    detail_data = await response.json()
                    encoded_url = detail_data.get("data", {}).get("url", "")
                
                if not encoded_url:
                    logger.warning(f"No encoded_url found for report_id={report_id}")
                    continue
                
                # 3. 상세 URL 추출
                extracted = await extract_dbfi_pdf_url(session, encoded_url)
                if not extracted:
                    logger.warning(f"Failed to extract URLs for report_id={report_id}")
                    continue
                
                new_tg = extracted['gate_url']
                new_pdf = extracted['pdf_url']
                
                # 4. DB 업데이트 (pdf_sync_status를 0으로 설정하여 재다운로드 유도)
                update_query = """
                UPDATE "tbl_sec_reports"
                SET "telegram_url" = %s,
                    "pdf_url" = %s,
                    pdf_sync_status = 0
                WHERE report_id = %s
                """
                # pdf_sync_status가 2였던 것은 유지하고, 아니었던 것은 0으로 리셋하여 다시 다운로드 시도하게 함
                
                await db.execute_query(update_query, (new_tg, new_pdf, report_id))
                logger.success(f"Updated report_id={report_id}: TG={new_tg}, PDF={new_pdf}")
                
                # 너무 빠른 요청 방지
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error processing report_id={report_id}: {e}")

if __name__ == "__main__":
    logger.add("logs/fix_dbfi_urls.log", rotation="10 MB")
    asyncio.run(fix_dbfi_urls())
