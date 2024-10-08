# -*- coding:utf-8 -*- 
import os
import re
import subprocess
# from package.googledrive import *
from date_util import GetCurrentDate
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.SecretKey import SecretKey
# 비밀키 불러오기
SECRET_KEY = SecretKey()


# 로그 파일 경로는 환경 변수로부터 가져옵니다
LOG_FILE = os.getenv('LOG_FILE', '~/log/logfile.log')

# 한글 인코딩 처리 및 wget으로 다운로드
def download_file_wget(report_info_row, URL=None, FILE_NAME=None):
    """
    파일을 주어진 URL에서 다운로드하고 지정된 파일 이름으로 저장합니다.
    
    매개변수:
    report_info_row (dict): 보고서 정보가 담긴 딕셔너리.
    URL (str): 파일을 다운로드할 URL.
    FILE_NAME (str): 저장할 파일 이름.
    
    반환:
    bool: 파일이 성공적으로 다운로드되거나 이미 존재하는 경우 True, 그렇지 않으면 False.
    """
    print("download_file_wget()", URL, FILE_NAME)

    BOARD_NM = ''
    URL = report_info_row['ATTACH_URL'] if report_info_row['ATTACH_URL'] else report_info_row['ARTICLE_URL']

    FILE_NAME = report_info_row['ARTICLE_TITLE']
    FIRM_NAME = report_info_row['FIRM_NM']

    # 파일명 지정
    FILE_NAME = FILE_NAME.replace(".pdf", "").replace(".PDF", "")
    FILE_NAME = FILE_NAME.replace(GetCurrentDate('YYYYMMDD')[2:8], "").replace(GetCurrentDate('YYYYMMDD'), "")
    FILE_NAME = str(GetCurrentDate('YYYYMMDD')[2:8]) + "_" + BOARD_NM + "_" + FILE_NAME + "_" + FIRM_NAME

    # 파일명 길이 제한 처리 및 확장자 추가
    MAX_FILE_NAME_LENGTH = 240
    if len(FILE_NAME) > MAX_FILE_NAME_LENGTH:
        FILE_NAME = FILE_NAME[:MAX_FILE_NAME_LENGTH]
    FILE_NAME += '.pdf'

    # 파일명에서 사용할 수 없는 문자 제거
    ATTACH_FILE_NAME = re.sub('[\/:*?"<>|]', '', FILE_NAME)
    print('convert URL:', URL)
    print('convert ATTACH_FILE_NAME:', ATTACH_FILE_NAME)

    # 파일이 이미 존재하는지 확인
    if os.path.exists(ATTACH_FILE_NAME):
        log_message = f"파일 '{ATTACH_FILE_NAME}'이(가) 이미 존재합니다. 다운로드를 건너뜁니다."
        print(log_message)
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(log_message + '\n')
        return True  # 파일이 이미 존재하므로 성공으로 처리

    # wget 명령어 생성 및 실행
    wget_command = [
        'wget', '--user-agent="Mozilla/5.0"', '-O', ATTACH_FILE_NAME, URL,
        '--max-redirect=10', '--retry-connrefused', '--waitretry=5',
        '--read-timeout=20', '--timeout=15', '--tries=5', '--no-check-certificate'
    ]

    # # 구글 드라이브에 업로드
    # r = googledrive.upload(str(ATTACH_FILE_NAME))
    # print(f'main URL {r}')
    # return r

    try:
        result = subprocess.run(wget_command, check=True, text=True, capture_output=True)
        log_message = f"파일 다운로드 완료: {ATTACH_FILE_NAME}"
        print(log_message)
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(log_message + '\n')
            log_file.write(result.stdout + '\n')  # 성공 시 출력도 로그에 기록
        return True  # 파일 다운로드 성공 시 True 반환
    except subprocess.CalledProcessError as e:
        error_message = f"wget 다운로드 실패: {e}"
        print(error_message)
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(error_message + '\n')
            log_file.write(e.stderr + '\n')  # 에러 메시지도 로그에 기록
        return False  # 다운로드 실패 시 False 반환
    
def main():
    URL = 'https://docs.hmsec.com/SynapDocViewServer/job?fid=https://www.hmsec.com/documents/research/20241007073137310_ko.pdf&sync=true&fileType=URL&filePath=https://www.hmsec.com/documents/research/20241007073137310_ko.pdf'
    ATTACH_FILE_NAME = '241007__자동차 산업 - 2024년 9월 현대차그룹 글로벌 도매 판매 _현대차증권.pdf'
    # wget 명령어 생성 및 실행
    wget_command = [
        'wget', '--user-agent="Mozilla/5.0"', '-O', ATTACH_FILE_NAME, URL,
        '--max-redirect=10', '--retry-connrefused', '--waitretry=5',
        '--read-timeout=20', '--timeout=15', '--tries=5', '--no-check-certificate'
    ]

    # # 구글 드라이브에 업로드
    # r = googledrive.upload(str(ATTACH_FILE_NAME))
    # print(f'main URL {r}')
    # return r

    try:
        result = subprocess.run(wget_command, check=True, text=True, capture_output=True)
        log_message = f"파일 다운로드 완료: {ATTACH_FILE_NAME}"
        print(log_message)
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(log_message + '\n')
            log_file.write(result.stdout + '\n')  # 성공 시 출력도 로그에 기록
        return True  # 파일 다운로드 성공 시 True 반환
    except subprocess.CalledProcessError as e:
        error_message = f"wget 다운로드 실패: {e}"
        print(error_message)
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(error_message + '\n')
            log_file.write(e.stderr + '\n')  # 에러 메시지도 로그에 기록
        return False  # 다운로드 실패 시 False 반환
    
if __name__ == "__main__":
    main()