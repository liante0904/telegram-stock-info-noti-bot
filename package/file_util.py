# -*- coding:utf-8 -*- 
import os
import re
import subprocess
from package import googledrive
from package.date_util import GetCurrentDate
from package.SecretKey import SecretKey
# 비밀키 불러오기
SECRET_KEY = SecretKey()



# 한글 인코딩 처리 및 wget으로 다운로드
def download_file_wget(report_info_row, URL=None, FILE_NAME=None):
    """
    Downloads a file from the given URL and saves it with the given file name.
    
    Parameters:
    report_info_row (dict): Dictionary containing report information.
    URL (str): The URL to download the file from.
    FILE_NAME (str): The name of the file to save.
    
    Returns:
    bool: True if the file is downloaded successfully or already exists, False otherwise.
    """
    print("download_file_wget()", URL, FILE_NAME)

    BOARD_NM = ''
    URL = report_info_row['ARTICLE_URL']
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
        print(f"파일 '{ATTACH_FILE_NAME}'이(가) 이미 존재합니다. 다운로드를 건너뜁니다.")
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
        result = subprocess.run(wget_command, check=True)
        print(f"파일 다운로드 완료: {ATTACH_FILE_NAME}")
        return True  # 파일 다운로드 성공 시 True 반환
    except subprocess.CalledProcessError as e:
        print(f"wget 다운로드 실패: {e}")
        return False  # 다운로드 실패 시 False 반환
    

