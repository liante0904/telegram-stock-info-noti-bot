# -*- coding:utf-8 -*- 
import os
import logging
import time
import asyncio
from send_error import send_message_to_shell

from models.SQLiteManager import SQLiteManager
from utils.date_util import GetCurrentDate

# business
from modules.LS_0 import LS_checkNewArticle
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
from modules.DBfi_19 import DBfi_checkNewArticle
from modules.MERITZ_20 import MERITZ_checkNewArticle

import scrap_af_main
import scrap_send_main
import scrap_upload_pdf
#################### global 변수 정리 ###################################
############공용 상수############

json_data_list = []

# 연속키용 상수
FIRST_ARTICLE_INDEX = 0
#################### global 변수 정리 끝###################################

   
# 로그 디렉토리 설정 함수
def setup_log_directory():
    HOME_PATH = os.path.expanduser("~")
    LOG_PATH = os.path.join(HOME_PATH, "log", GetCurrentDate('YYYYMMDD'))
    os.makedirs(LOG_PATH, exist_ok=True)
    return LOG_PATH

def get_script_name():
    # 현재 스크립트의 이름 가져오기
    script_filename = os.path.basename(__file__)
    script_name = script_filename.split('.')
    script_name = script_name[0]
    print('script_filename', script_filename)
    return script_name

def setup_debug_directory():
    LOG_PATH = setup_log_directory()
    script_name = get_script_name()
    # requests 라이브러리의 로깅을 활성화
    logging.getLogger("urllib3").setLevel(logging.DEBUG)
    # log 파일명
    LOG_FILENAME =  GetCurrentDate('YYYYMMDD')+ '_' + script_name + ".dbg"
    print('__file__', __file__, LOG_FILENAME)
    # log 전체경로
    LOG_FULLFILENAME = os.path.join(LOG_PATH, LOG_FILENAME)
    print('LOG_FULLFILENAME',LOG_FULLFILENAME)
    logging.basicConfig(filename=LOG_FULLFILENAME, level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    print("LOG_FULLFILENAME",LOG_FULLFILENAME)
    logging.debug('이것은 디버그 메시지입니다.')
    
def sync_check_main(sync_check_functions, total_data):
    totalCnt = 0
    # 동기 함수 실행
    for check_function in sync_check_functions:
        print(f"{check_function.__name__} => 새 게시글 정보 확인")
        json_data_list = check_function()  # 각 함수가 반환한 json_data_list
        if json_data_list:  # 유효한 데이터가 있을 경우에만 처리
            print('=' * 40)
            print(f"{check_function.__name__} => {len(json_data_list)}개의 유효한 게시글 발견")
            total_data.extend(json_data_list)  # 전체 리스트에 추가
            totalCnt += len(json_data_list)
        time.sleep(1)  # 과도한 요청 방지를 위한 딜레이
    return totalCnt

async def async_check_main(async_check_functions, total_data):
    totalCnt = 0
    # 비동기 함수 리스트 실행
    tasks = [func() for func in async_check_functions]  # 비동기 함수 호출을 태스크로 생성
    results = await asyncio.gather(*tasks)  # 태스크 병렬 실행 및 결과 수집

    for idx, json_data_list in enumerate(results):
        async_check_function = async_check_functions[idx]
        print(f"{async_check_function.__name__} => 새 게시글 정보 확인")
        if json_data_list:  # 유효한 데이터가 있을 경우에만 처리
            print('=' * 40)
            print(f"{async_check_function.__name__} => {len(json_data_list)}개의 유효한 게시글 발견")
            total_data.extend(json_data_list)  # 전체 리스트에 추가
            totalCnt += len(json_data_list)

    return totalCnt

async def main():
    try:
        print('===================scrap_send===============')
        
        # 로그 디렉토리 설정
        setup_log_directory()

        # 동기 함수 리스트
        sync_check_functions = [
            LS_checkNewArticle,
            ShinHanInvest_checkNewArticle,
            Samsung_checkNewArticle,
            Sangsanginib_checkNewArticle,
            Shinyoung_checkNewArticle,
            #DS_checkNewArticle,
            Miraeasset_checkNewArticle,
            Hmsec_checkNewArticle,
            Koreainvestment_selenium_checkNewArticle,
            DAOL_checkNewArticle,
            TOSSinvest_checkNewArticle,
            Leading_checkNewArticle,
        ]

        # 비동기 함수 리스트
        async_check_functions = [
            NHQV_checkNewArticle,
            HANA_checkNewArticle,
            KB_checkNewArticle,
            Kiwoom_checkNewArticle,
            eugene_checkNewArticle,
            Daeshin_checkNewArticle,
            iMfnsec_checkNewArticle,
            DBfi_checkNewArticle,
            MERITZ_checkNewArticle
        ]

        total_data = []  # 전체 데이터를 저장할 리스트
        totalCnt = 0

        # 동기 함수 실행
        print("Running synchronous functions...")
        for func in sync_check_functions:
            try:
                print(f"Running {func.__name__}")
                data = func()  # 동기 함수 호출
                if data:
                    total_data.extend(data)  # 데이터 병합
                    totalCnt += len(data)  # 카운트 증가
            except Exception as e:
                # 함수별 에러 처리
                logging.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
                send_message_to_shell(f"Error in sync function {func.__name__}: {str(e)}")

        # 비동기 함수 실행
        print("Running asynchronous functions...")
        for func in async_check_functions:
            try:
                print(f"Running {func.__name__}")
                data = await func()  # 비동기 함수 호출
                if data:
                    total_data.extend(data)  # 데이터 병합
                    totalCnt += len(data)  # 카운트 증가
            except Exception as e:
                # 함수별 에러 처리
                logging.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
                send_message_to_shell(f"Error in async function {func.__name__}: {str(e)}")

        print('==============전체 레포트 제공 회사 게시글 조회 완료==============')

        if total_data:
            db = SQLiteManager()
            # 모든 데이터를 한 번에 DB에 삽입
            inserted_count, updated_count = db.insert_json_data_list(total_data, 'data_main_daily_send')
            print(f"총 {totalCnt}개의 게시글을 스크랩하여.. DB에 Insert 시도합니다.")
            print(f"총 {inserted_count}개의 새로운 게시글을 DB에 삽입했고, {updated_count}개의 게시글을 업데이트했습니다.")

            if inserted_count or updated_count:
                # 추가 비동기 작업 실행
                await scrap_af_main.main()
                await scrap_send_main.main()
                await scrap_upload_pdf.main()
        else:
            print("새로운 게시글 스크랩 실패.")
    except Exception as e:
        # 전체 프로세스 에러 처리
        logging.error("An error occurred in the main process", exc_info=True)
        send_message_to_shell(f"Error in main: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
