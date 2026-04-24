# -*- coding:utf-8 -*- 
import os
import sys
import asyncio
import time
import argparse
import datetime
from loguru import logger
from dotenv import load_dotenv

# 공통 로그 설정 적용
from utils.logger_util import setup_logger
setup_logger("scraper")

# --- 모듈 임포트 ---
from utils.telegram_util import sendMarkDownText
from utils.sqlite_util import convert_sql_to_telegram_messages
from models.db_factory import get_db

# business modules
from modules.LS_0 import LS_checkNewArticle, LS_detail
from modules.ShinHanInvest_1_new import ShinHanInvest_checkNewArticle_new as ShinHanInvest_checkNewArticle
from modules.NHQV_2 import NHQV_checkNewArticle
from modules.HANA_3 import HANA_checkNewArticle
from modules.KBsec_4 import KB_checkNewArticle
from modules.Samsung_5 import Samsung_checkNewArticle
from modules.Sangsanginib_6 import Sangsanginib_checkNewArticle
from modules.Shinyoung_7 import Shinyoung_checkNewArticle
from modules.Miraeasset_8 import Miraeasset_checkNewArticle
from modules.Hmsec_9 import Hmsec_checkNewArticle
from modules.Kiwoom_10 import Kiwoom_checkNewArticle
from modules.DS_11 import DS_checkNewArticle
from modules.eugenefn_12 import eugene_checkNewArticle
from modules.Koreainvestment_13 import Koreainvestment_selenium_checkNewArticle
from modules.DAOL_14 import DAOL_checkNewArticle
from modules.TOSSinvest_15 import TOSSinvest_checkNewArticle
from modules.Leading_16 import Leading_checkNewArticle
from modules.Daeshin_17 import Daeshin_checkNewArticle
from modules.iMfnsec_18 import iMfnsec_checkNewArticle
from modules.DBfi_19 import DBfi_checkNewArticle, fetch_detailed_url
from modules.MERITZ_20 import MERITZ_checkNewArticle
from modules.Hanwhawm_21 import Hanwha_checkNewArticle
from modules.Hygood_22 import Hanyang_checkNewArticle
from modules.BNKfn_23 import BNK_checkNewArticle
from modules.Kyobo_24 import Kyobo_checkNewArticle
from modules.IBKs_25 import IBK_checkNewArticle
from modules.SKS_26 import Sks_checkNewArticle
from modules.Yuanta_27 import Yuanta_checkNewArticle # 비동기 버전 (파일명 변경됨)
from modules.Heungkuk_28 import Heungkuk_checkNewArticle

load_dotenv()
token = os.getenv('TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET')
chat_id = os.getenv('TELEGRAM_CHANNEL_ID_REPORT_ALARM')

async def enrich_data():
    logger.info("Starting data enrichment process...")
    db = get_db()
    from models.FirmInfo import FirmInfo
    
    for sec_firm_order in range(len(FirmInfo.firm_names)):
        firm_info = FirmInfo(sec_firm_order=sec_firm_order, article_board_order=0)
        firm_name = firm_info.get_firm_name()

        if firm_name and firm_info.telegram_update_required:
            records = await db.fetch_all_empty_telegram_url_articles(firm_info=firm_info, days_limit=7)
            if not records: continue

            logger.info(f"[{firm_name}] Found {len(records)} records for enrichment.")
            try:
                if sec_firm_order == 19:  # DB
                    update_records = await fetch_detailed_url(records)
                    tasks = [db.update_telegram_url(r['report_id'], r['TELEGRAM_URL'], pdf_url=r.get('PDF_URL') or r['TELEGRAM_URL']) for r in update_records if r.get('TELEGRAM_URL')]
                    if tasks: await asyncio.gather(*tasks)
                elif sec_firm_order == 0:  # LS
                    update_records = await LS_detail(articles=records, firm_info=firm_info)
                    tasks = [db.update_telegram_url(r['report_id'], r['TELEGRAM_URL'], r.get('ARTICLE_TITLE'), pdf_url=r.get('PDF_URL') or r['TELEGRAM_URL']) for r in update_records if r.get('TELEGRAM_URL')]
                    if tasks: await asyncio.gather(*tasks)
                elif sec_firm_order == 11:  # DS
                    tasks = [
                        db.update_telegram_url(
                            r['report_id'], 
                            f"https://ssh-oci.netlify.app/share?id={r['report_id']}",
                            pdf_url=r.get('PDF_URL')
                        ) 
                        for r in records
                    ]
                    if tasks: await asyncio.gather(*tasks)
                logger.success(f"[{firm_name}] Enrichment completed.")
            except Exception as e:
                logger.error(f"[{firm_name}] Enrichment failed: {e}")

async def daily_send_report(date_str=None):
    db = get_db()
    rows = await db.daily_select_data(date_str=date_str, type='send')
    if rows:
        messages = convert_sql_to_telegram_messages(rows)
        logger.info(f"Sending {len(messages)} messages...")
        for i, msg in enumerate(messages):
            logger.debug(f"Message {i+1} preview:\n{msg[:500]}...")
        success = True
        for msg in messages:
            try:
                await sendMarkDownText(token=token, chat_id=chat_id, sendMessageText=msg)
            except Exception as e:
                logger.error(f"Telegram error: {e}")
                success = False
        if success:
            await db.daily_update_data(date_str=date_str, fetched_rows=rows, type='send')
            logger.success("Daily report sent and DB updated.")

def run_sync_scrapers(sync_funcs, total_data):
    for func in sync_funcs:
        try:
            logger.info(f"Scraping (Sync): {func.__name__}")
            res = func()
            if res:
                total_data.extend(res)
                logger.info(f"{func.__name__} => Found {len(res)} articles")
            time.sleep(1)
        except Exception as e:
            logger.error(f"Sync Scraper Error ({func.__name__}): {e}")

async def run_async_scrapers(async_funcs, total_data):
    logger.info(f"Launching {len(async_funcs)} async scrapers...")
    tasks = []
    task_names = []
    
    for f in async_funcs:
        try:
            if not callable(f):
                continue
            
            # 함수를 일단 호출해봅니다.
            res = f()
            
            # 호출 결과가 코루틴(awaitable)인 경우에만 tasks에 추가
            if asyncio.iscoroutine(res):
                tasks.append(res)
                task_names.append(f.__name__)
            # 호출 결과가 이미 리스트인 경우 (동기 함수처럼 동작한 경우) 즉시 처리
            elif isinstance(res, list):
                total_data.extend(res)
                logger.info(f"{f.__name__} (Sync-like) => Found {len(res)} articles")
            # 그 외의 경우 (None 등)
            elif res is not None:
                logger.warning(f"{f.__name__} returned unexpected type: {type(res)}")
                
        except Exception as e:
            logger.error(f"Error calling scraper {f.__name__}: {e}")

    if not tasks:
        return

    logger.debug(f"Gathering {len(tasks)} actual coroutines: {task_names}")
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for idx, res in enumerate(results):
        name = task_names[idx]
        if isinstance(res, Exception):
            logger.error(f"Async Scraper Error ({name}): {res}")
        elif isinstance(res, list):
            total_data.extend(res)
            logger.info(f"{name} => Found {len(res)} articles")
        elif res is not None:
            logger.warning(f"{name} returned non-list result: {type(res)}")

async def main(date_str=None):
    logger.info("=================== SCRAPER START ===================")
    total_data = []
    
    sync_funcs = [
        LS_checkNewArticle, Miraeasset_checkNewArticle, Sks_checkNewArticle, 
        Samsung_checkNewArticle, Shinyoung_checkNewArticle, Hmsec_checkNewArticle,
        Heungkuk_checkNewArticle,
        TOSSinvest_checkNewArticle, DS_checkNewArticle
    ]
    async_functions = [
        ShinHanInvest_checkNewArticle, Leading_checkNewArticle,
        NHQV_checkNewArticle, HANA_checkNewArticle, KB_checkNewArticle,
        Sangsanginib_checkNewArticle, Kiwoom_checkNewArticle, 
        # Koreainvestment_selenium_checkNewArticle, # Selenium 에러 해결 중 (보류)
        DAOL_checkNewArticle, 
        Daeshin_checkNewArticle, 
        # iMfnsec_checkNewArticle, # 보류
        DBfi_checkNewArticle,
        MERITZ_checkNewArticle, Hanwha_checkNewArticle, Hanyang_checkNewArticle,
        BNK_checkNewArticle, Kyobo_checkNewArticle, IBK_checkNewArticle,
        # eugene_checkNewArticle # 세션 만료 및 제한 에러 (보류)
        Yuanta_checkNewArticle # 비동기 버전 (명칭 표준화됨)
    ]

    run_sync_scrapers(sync_funcs, total_data)
    await run_async_scrapers(async_functions, total_data)

    if total_data:
        unique = { (d.get("KEY") or d.get("ATTACH_URL", "")): d for d in total_data }
        total_list = list(unique.values())
        db = get_db()
        try:
            dbfi_records = [row for row in total_list if row.get("SEC_FIRM_ORDER") == 19]
            if dbfi_records:
                await fetch_detailed_url(dbfi_records)
                logger.info(f"DBfi pre-enriched before insert: {len(dbfi_records)} rows")
            ins, upd = db.insert_json_data_list(total_list)
            logger.success(f"DB Sync: {ins} new, {upd} updated.")
            
            # DB 삽입 후 잠시 대기하여 트리거/커밋이 확실히 반영되도록 함
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"DB error: {e}")

    await enrich_data()
    
    # 발송 전에 DB 연결을 새로 하거나 세션을 확실히 분리하여 최신 데이터를 가져옴
    await daily_send_report(date_str=date_str)
    logger.info("=================== SCRAPER END =====================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('date', type=str, nargs='?', default=None)
    args = parser.parse_args()
    asyncio.run(main(date_str=args.date))
