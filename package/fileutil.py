
# -*- coding:utf-8 -*- 
import os
import sys
import datetime
import logging
from pytz import timezone
import telegram
import requests
import time
import json
import re
import asyncio
import wget
import urllib.parse as urlparse
import urllib.request
import base64
from typing import List
from bs4 import BeautifulSoup

# URL에 파일명을 사용할때 한글이 포함된 경우 인코딩처리 로직 추가 
def DownloadFile(URL, FILE_NAME):
    global ATTACH_FILE_NAME
    print("DownloadFile()",URL, FILE_NAME)

    BOARD_NM = ''
    firm_info = get_firm_info(sec_firm_order = SEC_FIRM_ORDER, article_board_order = ARTICLE_BOARD_ORDER)
    # 로직 사유 : 레포트 첨부파일명에 한글이 포함된 경우 URL처리가 되어 있지 않음
    CONVERT_URL = URL 
    for c in URL: # URL내 한글이 있는 경우 인코딩 처리(URL에 파일명을 이용하여 조합함)
        # 코드셋 기준 파이썬:UTF-8 . 교보증권:EUC-KR
        # 1. 주소에서 한글 문자를 판별
        # 2. 해당 문자를 EUC-KR로 변환후 URL 인코딩
        # print("##",c , "##", ord('가') <= ord(c) <= ord('힣') )
        if ord('가') <= ord(c) <= ord('힣'): 
            c_encode = c.encode('euc-kr')
            CONVERT_URL = CONVERT_URL.replace(c, urlparse.quote(c_encode) )

    if URL != CONVERT_URL: 
        print("기존 URL에 한글이 포함되어 있어 인코딩처리함")
        print("CONVERT_URL", CONVERT_URL)
        URL = CONVERT_URL

    # 파일명 지정
    # 날짜 종목 제목 증권사 결국 이 순이 젤 좋아보이네
    # 날짜-대분류-소분류-제목-증권사.pdf
    # TODO 종목명 추가
    FILE_NAME = FILE_NAME.replace(".pdf", "").replace(".PDF", "") # 확장자 제거 후 시작
    print('FILE_NAME 확장자 제거 ,', FILE_NAME)
    FILE_NAME = FILE_NAME.replace(GetCurrentDate('YYYYMMDD')[2:8], "").replace(GetCurrentDate('YYYYMMDD'), "") # 날짜 제거 후 시작
    FILE_NAME = str(GetCurrentDate('YYYYMMDD')[2:8]) + "_" + BOARD_NM + "_" + FILE_NAME + "_" + firm_info['firm_name']
    # 파일명 길이 체크 후, 길면 자르고, 확장자 붙여 마무리함
    MAX_FILE_NAME_LENGTH = 240
    if len(FILE_NAME)  > MAX_FILE_NAME_LENGTH : FILE_NAME = FILE_NAME[0:MAX_FILE_NAME_LENGTH]
    FILE_NAME += '.pdf'
    # if '.pdf' not in FILE_NAME : FILE_NAME = FILE_NAME + '.pdf'

    ATTACH_FILE_NAME = re.sub('[\/:*?"<>|]','',FILE_NAME) # 저장할 파일명 : 파일명으로 사용할수 없는 문자 삭제 변환
    print('convert URL:',URL)
    print('convert ATTACH_FILE_NAME:',ATTACH_FILE_NAME)

    if os.path.exists(ATTACH_FILE_NAME):
        print(f"파일 '{ATTACH_FILE_NAME}'이(가) 이미 존재합니다. 다운로드를 건너뜁니다.")
        return None
    
    with open(ATTACH_FILE_NAME, "wb")as file:  # open in binary mode
        response = get(URL, verify=False)     # get request
        file.write(response.content) # write to file

            
    r = googledrive.upload(str(ATTACH_FILE_NAME))
    
    print(f'main URL {r}')
    return r

# wget을 이용하여 파일 다운로드 => 추후 다 변경할수도?
def DownloadFile_wget(URL, FILE_NAME):
    global ATTACH_FILE_NAME
    print("DownloadFile_wget()",URL, FILE_NAME)


    BOARD_NM = ''
    firm_info = get_firm_info(sec_firm_order = SEC_FIRM_ORDER, article_board_order = ARTICLE_BOARD_ORDER)
    # 로직 사유 : 레포트 첨부파일명에 한글이 포함된 경우 URL처리가 되어 있지 않음
    CONVERT_URL = URL 
    for c in URL: # URL내 한글이 있는 경우 인코딩 처리(URL에 파일명을 이용하여 조합함)
        # 코드셋 기준 파이썬:UTF-8 . 교보증권:EUC-KR
        # 1. 주소에서 한글 문자를 판별
        # 2. 해당 문자를 EUC-KR로 변환후 URL 인코딩
        # print("##",c , "##", ord('가') <= ord(c) <= ord('힣') )
        if ord('가') <= ord(c) <= ord('힣'): 
            c_encode = c.encode('euc-kr')
            CONVERT_URL = CONVERT_URL.replace(c, urlparse.quote(c_encode) )

    if URL != CONVERT_URL: 
        print("기존 URL에 한글이 포함되어 있어 인코딩처리함")
        print("CONVERT_URL", CONVERT_URL)
        URL = CONVERT_URL

    # 파일명 지정
    # 날짜 종목 제목 증권사 결국 이 순이 젤 좋아보이네
    # 날짜-대분류-소분류-제목-증권사.pdf
    # TODO 종목명 추가
    FILE_NAME = FILE_NAME.replace(".pdf", "").replace(".PDF", "") # 확장자 제거 후 시작
    print('FILE_NAME 확장자 제거 ,', FILE_NAME)
    FILE_NAME = FILE_NAME.replace(GetCurrentDate('YYYYMMDD')[2:8], "").replace(GetCurrentDate('YYYYMMDD'), "") # 날짜 제거 후 시작
    FILE_NAME = str(GetCurrentDate('YYYYMMDD')[2:8]) + "_" + BOARD_NM + "_" + FILE_NAME + "_" + firm_info['firm_name']

    # 파일명 길이 체크 후, 길면 자르고, 확장자 붙여 마무리함
    MAX_FILE_NAME_LENGTH = 240
    if len(FILE_NAME)  > MAX_FILE_NAME_LENGTH : FILE_NAME = FILE_NAME[0:MAX_FILE_NAME_LENGTH]
    FILE_NAME += '.pdf'
    # if '.pdf' not in FILE_NAME : FILE_NAME = FILE_NAME + '.pdf'

    ATTACH_FILE_NAME = re.sub('[\/:*?"<>|]','',FILE_NAME) # 저장할 파일명 : 파일명으로 사용할수 없는 문자 삭제 변환
    print('convert URL:',URL)
    print('convert ATTACH_FILE_NAME:',ATTACH_FILE_NAME)

    if os.path.exists(ATTACH_FILE_NAME):
        print(f"파일 '{ATTACH_FILE_NAME}'이(가) 이미 존재합니다. 다운로드를 건너뜁니다.")
        return None

    wget.download(url=URL, out=ATTACH_FILE_NAME)
    r = googledrive.upload(str(ATTACH_FILE_NAME))
    
    print(f'main URL {r}')
    return r

