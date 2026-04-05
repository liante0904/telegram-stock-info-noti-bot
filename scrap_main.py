# -*- coding:utf-8 -*- 
import os
import asyncio
import time
import argparse
import telegram.error
from loguru import logger
from utils.telegram_util import send_admin_alert_sync, sendMarkDownText
from utils.sqlite_util import convert_sql_to_telegram_messages
from utils.file_util import download_file_wget
from dotenv import load_dotenv

from models.SQLiteManager import SQLiteManager
import datetime

# business
from modules.LS_0 import LS_checkNewArticle, LS_detail
from modules.ShinHanInvest_1 import ShinHanInvest_checkNewArticle
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
from modules.Yuanta_27 import Yuanta_checkNewArticle

load_dotenv()

token = os.getenv('TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET')
chat_id = os.getenv('TELEGRAM_CHANNEL_ID_REPORT_ALARM')

#################### global 변수 정리 ###################################
############공용 상수############

json_data_list = []

# 연속키용 상수
FIRST_ARTICLE_INDEX = 0
#################### global 변수 정리 끝###################################

# 로그 설정
def setup_logger():
    HOME_PATH = os.path.expanduser("~")
    KST = datetime.timezone(datetime.timedelta(hours=9))
    log_date = datetime.datetime.now(KST).strftime('%Y%m%d')
    LOG_PATH = os.path.join(HOME_PATH, "log", log_date)
    os.makedirs(LOG_PATH, exist_ok=True)
    
    # loguru 설정: 콘솔(기본)과 파일 모두 출력
    log_file = os.path.join(LOG_PATH, f"{log_date}_scrap_main.log")
    logger.add(log_file, rotation="00:00", retention="30 days", level="DEBUG", 
               format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")
    return LOG_PATH

async def enrich_data():
    """
    상세 정보(PDF URL 등)가 누락된 게시글을 찾아 후처리를 수행합니다.
    """
    logger.info("Starting data enrichment (fetching detailed URLs)...")
    db = SQLiteManager()
    
    from models.FirmInfo import FirmInfo
    
    for sec_firm_order in range(len(FirmInfo.firm_names)):
        firm_info = FirmInfo(sec_firm_order=sec_firm_order, article_board_order=0)

        if firm_info.get_firm_name() and firm_info.telegram_update_required:
            # 최근 7일 이내의 빈 URL 레코드 조회
            records = await db.fetch_all_empty_telegram_url_articles(firm_info=firm_info, days_limit=7)
            
            if not records:
                continue

            logger.info(f"Enriching {len(records)} records for {firm_info.get_firm_name()} (Order: {sec_firm_order})")

            try:
                if sec_firm_order == 19:  # DB금융투자
                    update_records = await fetch_detailed_url(records)
                    update_tasks = [
                        db.update_telegram_url(r['report_id'], r['TELEGRAM_URL'], pdf_url=r.get('PDF_URL') or r['TELEGRAM_URL'])
                        for r in update_records if r.get('TELEGRAM_URL')
                    ]
                    if update_tasks:
                        await asyncio.gather(*update_tasks)

                elif sec_firm_order == 0:  # LS증권
                    # LS_detail은 리스트를 인자로 받을 수 있도록 설계되어 있음
                    update_records = await LS_detail(articles=records, firm_info=firm_info)
                    update_tasks = [
                        db.update_telegram_url(r['report_id'], r['TELEGRAM_URL'], r.get('ARTICLE_TITLE'), pdf_url=r.get('PDF_URL') or r['TELEGRAM_URL'])
                        for r in update_records if r.get('TELEGRAM_URL')
                    ]
                    if update_tasks:
                        await asyncio.gather(*update_tasks)
                
            except Exception as e:
                logger.error(f"Error during enrichment for firm {sec_firm_order}: {str(e)}")

async def daily_send_report(date_str=None):
    db = SQLiteManager()
    rows = await db.daily_select_data(date_str=date_str, type='send')
    if rows:
        formatted_messages = await convert_sql_to_telegram_messages(rows)
        logger.info(f"Prepared {len(formatted_messages)} messages to send.")

        # 메시지 발송
        send_success = True  # 모든 메시지가 성공했는지 여부를 추적
        for sendMessageText in formatted_messages:
            try:
                logger.debug(f"Sending message: {sendMessageText[:50]}...")
                await sendMarkDownText(token=token,
                                       chat_id=chat_id,
                                       sendMessageText=sendMessageText)
            except telegram.error.TelegramError as e:
                logger.error(f"Telegram API Error: {e} | Message: {sendMessageText[:50]}")
                send_success = False
            except Exception as e:
                logger.exception(f"Unexpected error while sending message: {e}")
                send_success = False

        # 모든 메시지가 성공적으로 전송된 경우에만 데이터 업데이트
        if send_success:
            r = await db.daily_update_data(date_str=date_str, fetched_rows=rows, type='send')
            if r:
                logger.info('DB daily_update_data successful.')
        else:
            logger.warning('Some messages failed to send. DB update skipped.')
    
def sync_check_main(sync_check_functions, total_data):
    totalCnt = 0
    # 동기 함수 실행
    for check_function in sync_check_functions:
        try:
            logger.info(f"{check_function.__name__} => 새 게시글 정보 확인")
            json_data_list = check_function()  # 각 함수가 반환한 json_data_list
            if json_data_list:  # 유효한 데이터가 있을 경우에만 처리
                logger.info(f"{check_function.__name__} => {len(json_data_list)}개의 유효한 게시글 발견")
                total_data.extend(json_data_list)  # 전체 리스트에 추가
                totalCnt += len(json_data_list)
            time.sleep(1)  # 과도한 요청 방지를 위한 딜레이
        except Exception as e:
            logger.exception(f"Error in sync function {check_function.__name__}: {str(e)}")
            send_admin_alert_sync(f"Error in sync function {check_function.__name__}: {str(e)}")
    return totalCnt

async def async_check_main(async_check_functions, total_data):
    totalCnt = 0
    # 비동기 함수 리스트 실행
    logger.info(f"Starting {len(async_check_functions)} asynchronous tasks in parallel...")
    tasks = [func() for func in async_check_functions]  # 비동기 함수 호출을 태스크로 생성
    results = await asyncio.gather(*tasks, return_exceptions=True)  # 태스크 병렬 실행 및 결과 수집

    for idx, result in enumerate(results):
        async_check_function = async_check_functions[idx]
        func_name = async_check_function.__name__
        
        if isinstance(result, Exception):
            logger.error(f"Error in async function {func_name}: {result}")
            send_admin_alert_sync(f"Error in async function {func_name}: {str(result)}")
        elif result:  # 유효한 데이터가 있을 경우에만 처리
            logger.info(f"{func_name} => {len(result)}개의 유효한 게시글 발견")
            total_data.extend(result)  # 전체 리스트에 추가
            totalCnt += len(result)
        else:
            logger.debug(f"{func_name} => 새 게시글 없음")

    return totalCnt

async def retry_db_insert_in_memory(db, data, table_name, retries=3, delay=60):
    """메모리에서 데이터를 보관한 채로 일정 시간 뒤 DB 삽입 재시도"""
    for attempt in range(retries):
        try:
            inserted_count, updated_count = db.insert_json_data_list(data, table_name)
            logger.info(f"DB 재삽입 성공: {inserted_count}개의 새로운 게시글, {updated_count}개의 게시글 업데이트.")
            return inserted_count, updated_count  # 성공 시 건수 반환
        except Exception as e:
            logger.error(f"DB 삽입 실패 (시도 {attempt + 1}/{retries}): {str(e)}")
            logger.exception("DB Insert retry failed details:")
            if attempt < retries - 1:
                logger.info(f"{delay}초 후 다시 시도합니다...")
                await asyncio.sleep(delay)  # 재시도 전 대기

    # 모든 시도 실패 시
    logger.error("모든 DB 삽입 시도가 실패했습니다.")
    return 0, 0

async def main(date_str=None):
    try:
        log_path = setup_logger()
        logger.info(f'=================== scrap_main START (Log: {log_path}) ===================')
        # 동기 함수 리스트
        sync_check_functions = [
            LS_checkNewArticle,
            # ShinHanInvest_checkNewArticle,
            # Samsung_checkNewArticle,
            # Shinyoung_checkNewArticle,
            #DS_checkNewArticle,
            Miraeasset_checkNewArticle,
            # Hmsec_checkNewArticle,
            # TOSSinvest_checkNewArticle,
            # Leading_checkNewArticle,
            Sks_checkNewArticle,
            Yuanta_checkNewArticle,
        ]

        # 비동기 함수 리스트
        async_check_functions = [
            ShinHanInvest_checkNewArticle,
            Samsung_checkNewArticle,
            Shinyoung_checkNewArticle,
            Hmsec_checkNewArticle,
            TOSSinvest_checkNewArticle,
            Leading_checkNewArticle,
            NHQV_checkNewArticle,
            HANA_checkNewArticle,
            KB_checkNewArticle,
            Sangsanginib_checkNewArticle,
            Kiwoom_checkNewArticle,
            Koreainvestment_selenium_checkNewArticle,
            # eugene_checkNewArticle,
            DAOL_checkNewArticle,
            Daeshin_checkNewArticle,
            iMfnsec_checkNewArticle,
            DBfi_checkNewArticle,
            MERITZ_checkNewArticle,
            Hanwha_checkNewArticle,
            Hanyang_checkNewArticle,
            BNK_checkNewArticle,
            Kyobo_checkNewArticle,
            IBK_checkNewArticle
        ]

        total_data = []  # 전체 데이터를 저장할 리스트
        totalCnt = 0
        inserted_count = 0
        updated_count = 0

        # 동기 함수 실행
        logger.info("Running synchronous functions...")
        sync_check_main(sync_check_functions, total_data)

        # 비동기 함수 실행
        logger.info("Running asynchronous functions...")
        await async_check_main(async_check_functions, total_data)

        logger.info('==============전체 레포트 제공 회사 게시글 조회 완료==============')

        if total_data:
            # 5번 개선: 메모리 레벨 중복 제거 (KEY 기준)
            unique_data = {}
            for entry in total_data:
                # SQLiteManager의 KEY 생성 로직과 동일하게 적용
                key = entry.get("KEY") or entry.get("ATTACH_URL", '')
                if key not in unique_data:
                    unique_data[key] = entry
            
            deduplicated_data = list(unique_data.values())
            if len(deduplicated_data) < len(total_data):
                logger.info(f"메모리 내 중복 제거 완료: {len(total_data)} -> {len(deduplicated_data)}")
            
            total_data = deduplicated_data
            totalCnt = len(total_data)

            db = SQLiteManager()

            # 데이터 삽입 시도
            try:
                inserted_count, updated_count = db.insert_json_data_list(total_data, 'data_main_daily_send')
                logger.info(f"총 {totalCnt}개의 게시글을 DB에 Insert/Update 시도합니다.")
                logger.info(f"결과: {inserted_count}개 삽입, {updated_count}개 업데이트.")
            except Exception as e:
                logger.error(f"DB 삽입 중 오류 발생: {str(e)}")
                logger.exception("DB Insert Error details:")

                # 메모리에서 데이터를 보관하며 재시도
                logger.info("DB 삽입 실패, 일정 시간 후 재시도합니다...")
                inserted_count, updated_count = await retry_db_insert_in_memory(db, total_data, 'data_main_daily_send', retries=3, delay=60)

            if inserted_count > 0 or updated_count > 0:
                # 데이터 강화(후처리) 작업 실행
                await enrich_data()

        else:
            logger.warning("새로운 게시글 스크랩 실패 또는 데이터 없음.")
        
        # 발송 전 최종적으로 한 번 더 후처리가 필요한 항목이 있는지 체크
        if not (inserted_count > 0 or updated_count > 0):
            await enrich_data()


        # 발송 작업 수행 (날짜가 지정된 경우 해당 날짜 기준, 아니면 오늘 기준)
        await daily_send_report(date_str=date_str)

    except Exception as e:
        # 전체 프로세스 에러 처리
        logger.exception("An error occurred in the main process")
        send_admin_alert_sync(f"Error in main: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Scrap and send main script.')
    parser.add_argument('date', type=str, nargs='?', default=None, help='Date in YYYY-MM-DD format.')

    args = parser.parse_args()
    asyncio.run(main(date_str=args.date))
