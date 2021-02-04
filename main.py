import os
import sys
# import urlparse
import telegram
import requests
import datetime
import time
import ssl
import json
import re
import pymysql
from typing import List
from bs4 import BeautifulSoup
#from urllib.parse import urlparse
import urllib.parse as urlparse
from requests import get  # to make GET request

## 로직 설명 ##
# 1. Main() -> 각 회사별 함수를 통해 반복 (추후 함수명 일괄 변경 예정)
#     - checkNewArticle -> parse -> downloadFile -> Send 
# 2. 연속키의 경우 현재 .key로 저장
#     - 추후 heroku db로 처리 예정(MySQL)
#     - DB연결이 안되는 경우, Key로 처리할수 있도록 예외처리 반영
# 3. 최초 조회되는 게시판 혹은 Key값이 없는 경우 메세지를 발송하지 않음.
# 4. 테스트와 운영을 구분하여 텔레그램 발송 채널 ID 구분 로직 추가
#     - 어떻게 구분지을지 생각해봐야함
# 5. 메시지 발송 방법 변경 (봇 to 사용자 -> 채널에 발송)
############공용 상수############
# 메시지 발송 ID
CHAT_ID = '-1001431056975' # 운영 채널(증권사 신규 레포트 게시물 알림방)
# CHAT_ID = '-1001474652718' # 테스트 채널

# 게시글 갱신 시간
REFRESH_TIME = 600

# 회사이름
FIRM_NAME = (
    "이베스트 투자증권",    # 0
    "흥국증권",             # 1
    "상상인증권",           # 2
    "하나금융투자"          # 3
)

# 게시판 이름
BOARD_NAME = (
    ["이슈브리프" , "기업분석", "산업분석", "투자전략", "Quant"],
    ["투자전략", "산업/기업분석"],
    ["산업리포트", "기업리포트"],
    ["산업분석", "기업분석", "Daily"],
    ["투자전략", "Report & Note", "해외주식"],
)
EBEST_BOARD_NAME  = ["이슈브리프" , "기업분석", "산업분석", "투자전략", "Quant"]
HEUNGKUK_BOARD_NAME = ["투자전략", "산업/기업분석"]
SANGSANGIN_BOARD_NAME = ["산업리포트", "기업리포트"]
HANA_BOARD_NAME = ["산업분석", "기업분석", "Daily"]
HMSEC_BOARD_NAME = ["투자전략", "Report & Note", "해외주식"]

# 연속키URL
NXT_KEY = ''

# LOOP 인덱스 변수
SEC_FIRM_ORDER = 0 # 증권사 순번
ARTICLE_BOARD_ORDER = 0 # 게시판 순번

# 이모지
EMOJI_FIRE = u'\U0001F525'
EMOJI_PICK = u'\U0001F449'

# 연속키용 상수
FIRST_ARTICLE_INDEX = 0

def SEDAILY_checkNewArticle():
    global NXT_KEY

    TARGET_URL = 'https://www.sedaily.com/Search/Search/SEList?Page=1&scDetail=&scOrdBy=0&catView=AL&scText=%EA%B8%B0%EA%B4%80%C2%B7%EC%99%B8%EA%B5%AD%EC%9D%B8%C2%B7%EA%B0%9C%EC%9D%B8%20%EC%88%9C%EB%A7%A4%EC%88%98%C2%B7%EB%8F%84%20%EC%83%81%EC%9C%84%EC%A2%85%EB%AA%A9&scPeriod=1w&scArea=t&scTextIn=&scTextExt=&scPeriodS=&scPeriodE=&command=&_=1612164364267'
                 
    webpage = requests.get(TARGET_URL, verify=False)

    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")

    print('###첫실행구간###')
    soupList = soup.select('#NewsDataFrm > ul > li > a[href]')
    print('######')

    FIRST_ARTICLE_URL = 'https://www.sedaily.com'+soupList[FIRST_ARTICLE_INDEX].attrs['href']
    # 연속키 저장 테스트 -> 테스트 후 연속키 지정 구간으로 변경
    KEY_DIR_FILE_NAME = './key/'+ 'sedaily' + '.key' # => 파일형식 예시 : 1-0.key (앞자리: 증권사 순서, 뒷자리:게시판 순서)
    
    # 존재 여부 확인 후 연속키 파일 생성
    if not( os.path.isfile( KEY_DIR_FILE_NAME ) ): # 최초 실행 이거나 연속키 초기화
        # 연속키가 없는 경우 => 첫 게시글을 연속키로 저장
        print('sedaily의 매매동향 연속키가 존재 하지 않습니다. 첫번째 게시물을 연속키로 지정하고 메시지는 발송하지 않습니다.')
        NXT_KEY = Set_nxtKey(KEY_DIR_FILE_NAME, FIRST_ARTICLE_URL)
    else:   # 이미 실행
        NXT_KEY = Get_nxtKey(KEY_DIR_FILE_NAME, NXT_KEY)


    print('게시글URL:', FIRST_ARTICLE_URL) # 주소
    print('연속URL:', NXT_KEY) # 주소
    print('############')

    for list in soupList:
        LIST_ARTICLE_URL = 'https://www.sedaily.com'+list.attrs['href']
        LIST_ARTICLE_TITLE = list.select_one('div.text_area > h3').text.replace("[표]", "")
        print(LIST_ARTICLE_TITLE)

        if NXT_KEY != LIST_ARTICLE_URL or NXT_KEY == '': #
            send(ARTICLE_BOARD_NAME = '',ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)        
            SEDAILY_downloadFile(LIST_ARTICLE_URL)
            print('메세지 전송 URL:', LIST_ARTICLE_URL)
        else:
            print('새로운 게시물을 모두 발송하였습니다.')
            Set_nxtKey(KEY_DIR_FILE_NAME, FIRST_ARTICLE_URL)
            return True

def SEDAILY_downloadFile(ARTICLE_URL):
    webpage = requests.get(ARTICLE_URL, verify=False)
    # 첨부파일 URL
    attachFileCode = BeautifulSoup(webpage.content, "html.parser").select_one('#v-left-scroll-in > div.article_con > div.con_left > div.article_view > figure > p > img')
    print(attachFileCode)
    ATTACH_URL = attachFileCode.attrs['src']
    sendPhoto(ATTACH_URL)    
    time.sleep(5) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)

def EBEST_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    # 게시글 url의 경우 
    # 1. 앞에 "https://www.ebestsec.co.kr/EtwFrontBoard/" 를 추가
    # 2. amp; 를 삭제처리를 해야함

    # 게시글 내 첨부파일의 경우 
    # 1. 앞에 "https://www.ebestsec.co.kr/_bt_lib/util/download.jsp?dataType=" 를 추가
    # 2. 링크에서 알맹이를 붙이면 됨 -> javascript:download("08573D2F59307A57F4FC67A81B8C333A4C884E6D2951A32F4A48B73EF4E6EC22A0E62B351A025A54E20CB47DEF8A0A801BF2F7B5E3E640975E88D7BACE3B4A49F83020ED90019B489B3C036CF8AB930DCF4795CE87DE76454465F0CF7316F47BF3A0BC08364132247378E3AABC8D0981627BD8F94134BF00D27B03D8F04AC8C04369354956052B75415A9585589694B5F63378DFA40C6BA6435302B96D780C3B3EB2BF0C866966D4CE651747574C8B25208B848CBEBB1BE0222821FC75DCE016")

    requests.packages.urllib3.disable_warnings()

    # 이슈브리프
    TARGET_URL_0 = 'https://www.ebestsec.co.kr/EtwFrontBoard/List.jsp?board_no=146&left_menu_no=211&front_menu_no=1029&parent_menu_no=211'
    # 기업분석 게시판
    TARGET_URL_1 = 'https://www.ebestsec.co.kr/EtwFrontBoard/List.jsp?board_no=36&left_menu_no=211&front_menu_no=212&parent_menu_no=211'
    # 산업분석
    TARGET_URL_2 = 'https://www.ebestsec.co.kr/EtwFrontBoard/List.jsp?board_no=37&left_menu_no=211&front_menu_no=213&parent_menu_no=211'
    # 투자전략
    TARGET_URL_3 = 'https://www.ebestsec.co.kr/EtwFrontBoard/List.jsp?board_no=38&left_menu_no=211&front_menu_no=214&parent_menu_no=211'
    # Quant
    TARGET_URL_4 = 'https://www.ebestsec.co.kr/EtwFrontBoard/List.jsp?board_no=147&left_menu_no=211&front_menu_no=1036&parent_menu_no=211'

    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1, TARGET_URL_2, TARGET_URL_3, TARGET_URL_4)

    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        EBEST_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        time.sleep(5)

def EBEST_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY

    webpage = requests.get(TARGET_URL, verify=False)

    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")

    print('###첫실행구간###')
    soupList = soup.select('#contents > table > tbody > tr > td.subject > a')
    print('######')
    ARTICLE_BOARD_NAME = EBEST_BOARD_NAME[ARTICLE_BOARD_ORDER]
    FIRST_ARTICLE_TITLE = soupList[FIRST_ARTICLE_INDEX].text
    FIRST_ARTICLE_URL = 'https://www.ebestsec.co.kr/EtwFrontBoard/' + soupList[FIRST_ARTICLE_INDEX].attrs['href'].replace("amp;", "")
    # 연속키 저장 테스트 -> 테스트 후 연속키 지정 구간으로 변경
    KEY_DIR_FILE_NAME = './key/'+ str(SEC_FIRM_ORDER) + '-' + str(ARTICLE_BOARD_ORDER) + '.key' # => 파일형식 예시 : 1-0.key (앞자리: 증권사 순서, 뒷자리:게시판 순서)
    
    # 존재 여부 확인 후 연속키 파일 생성
    if not( os.path.isfile( KEY_DIR_FILE_NAME ) ): # 최초 실행 이거나 연속키 초기화
        # 연속키가 없는 경우 => 첫 게시글을 연속키로 저장
        print(FIRM_NAME[SEC_FIRM_ORDER],'의 ',BOARD_NAME[SEC_FIRM_ORDER][ARTICLE_BOARD_ORDER],'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
        NXT_KEY = Set_nxtKey(KEY_DIR_FILE_NAME, FIRST_ARTICLE_URL)
    else:   # 이미 실행
        NXT_KEY = Get_nxtKey(KEY_DIR_FILE_NAME, NXT_KEY)

    print('게시판 이름:', ARTICLE_BOARD_NAME) # 게시판 종류
    print('게시글 제목:', FIRST_ARTICLE_TITLE) # 게시글 제목
    print('게시글URL:', FIRST_ARTICLE_URL) # 주소
    print('연속URL:', NXT_KEY) # 주소
    print('############')

    for list in soupList:
        LIST_ARTICLE_URL = 'https://www.ebestsec.co.kr/EtwFrontBoard/' + list.attrs['href'].replace("amp;", "")
        LIST_ARTICLE_TITLE = list.text
        if NXT_KEY != LIST_ARTICLE_URL or NXT_KEY == '': #  
            EBEST_downloadFile(LIST_ARTICLE_URL)
            send(ARTICLE_BOARD_NAME = ARTICLE_BOARD_NAME, ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)        
            print('메세지 전송 URL:', LIST_ARTICLE_URL)
        else:
            print('새로운 게시물을 모두 발송하였습니다.')
            Set_nxtKey(KEY_DIR_FILE_NAME, FIRST_ARTICLE_URL)
            return True

def EBEST_downloadFile(ARTICLE_URL):
    global ATTACH_FILE_NAME
    ATTACH_BASE_URL = 'https://www.ebestsec.co.kr/_bt_lib/util/download.jsp?dataType='

    webpage = requests.get(ARTICLE_URL, verify=False)
    # 첨부파일 URL
    attachFileCode = BeautifulSoup(webpage.content, "html.parser").select_one('.attach > a')['href']
    ATTACH_URL = attachFileCode.replace('Javascript:download("', ATTACH_BASE_URL).replace('")', '')
    print('첨부파일 URL : ',ATTACH_URL)
    # 첨부파일 이름
    ATTACH_FILE_NAME = BeautifulSoup(webpage.content, "html.parser").select_one('.attach > a').text.strip()
    print('첨부파일이름 : ',ATTACH_FILE_NAME)
    DownloadFile(URL = ATTACH_URL, FILE_NAME = ATTACH_FILE_NAME)
    time.sleep(5) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)
    
def send(ARTICLE_BOARD_NAME , ARTICLE_TITLE , ARTICLE_URL): # 파일의 경우 전역변수로 처리 (downloadFile 함수)
    print('send()')
    DISABLE_WEB_PAGE_PREVIEW = True # 메시지 프리뷰 여부 기본값 설정

    ARTICLE_BOARD_NAME = ''

    if SEC_FIRM_ORDER == 'SEDAILY':
        msgFirmName = "매매동향"
        ARTICLE_BOARD_NAME = ''
        if  "최종치" in ARTICLE_TITLE: return print('sedaily의 매매동향 최종치 집계 데이터는 메시지 발송을 하지 않습니다.') # 장마감 최종치는 발송 안함
    else:
        msgFirmName = FIRM_NAME[SEC_FIRM_ORDER] + " - "
        ARTICLE_BOARD_NAME = BOARD_NAME[SEC_FIRM_ORDER][ARTICLE_BOARD_ORDER]

    # if SEC_FIRM_ORDER == 0:
    #     msgFirmName = "이베스트 투자증권"
    # elif SEC_FIRM_ORDER == 1:
    #     msgFirmName = "흥국증권"
    # elif SEC_FIRM_ORDER == 2:
    #     msgFirmName = "상상인증권"
    # elif SEC_FIRM_ORDER == 3:
    #     msgFirmName = "하나금융투자"
    # elif SEC_FIRM_ORDER == 'SEDAILY':
    #     msgFirmName = "매매동향"
    #     ARTICLE_BOARD_NAME = ''
    #     if  "최종치" in ARTICLE_TITLE: return # 장마감 최종치는 발송 안함
    # else:
    #     msgFirmName = ''


    # 실제 전송할 메시지 작성
    sendMessageText = ''
    sendMessageText += EMOJI_FIRE + msgFirmName + ARTICLE_BOARD_NAME + EMOJI_FIRE + "\n"
    sendMessageText += ARTICLE_TITLE + "\n"
    sendMessageText += EMOJI_PICK + ARTICLE_URL 

    #생성한 텔레그램 봇 정보 assign (@ebest_noti_bot)
    my_token_key = '1372612160:AAHVyndGDmb1N2yEgvlZ_DmUgShqk2F0d4w'
    bot = telegram.Bot(token = my_token_key)

    #생성한 텔레그램 봇 정보 출력
    #me = bot.getMe()
    #print('텔레그램 채널 정보 : ',me)

    #생성한 텔레그램 봇 /start 시작 후 사용자 id 받아 오기
    #CHAT_ID = bot.getUpdates()[-1].message.chat.id

    if SEC_FIRM_ORDER == 'SEDAILY': # 매매동향의 경우 URL만 발송하여 프리뷰 처리 
        DISABLE_WEB_PAGE_PREVIEW = False
    

    bot.sendMessage(chat_id = CHAT_ID, text = sendMessageText, disable_web_page_preview = DISABLE_WEB_PAGE_PREVIEW)
    


    if DISABLE_WEB_PAGE_PREVIEW: # 첨부파일이 있는 경우 => 프리뷰는 사용하지 않음
        time.sleep(1) # 메시지 전송 텀을 두어 푸시를 겹치지 않게 함
        bot.sendDocument(chat_id = CHAT_ID, document = open(ATTACH_FILE_NAME, 'rb') )
        os.remove(ATTACH_FILE_NAME) # 파일 전송 후 PDF 삭제
    
    time.sleep(8) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)

def sendPhoto(ARTICLE_URL): # 파일의 경우 전역변수로 처리 (downloadFile 함수)
    print('sendPhoto()')

    #생성한 텔레그램 봇 정보 assign (@ebest_noti_bot)
    my_token_key = '1372612160:AAHVyndGDmb1N2yEgvlZ_DmUgShqk2F0d4w'
    bot = telegram.Bot(token = my_token_key)

    bot.sendPhoto(chat_id = CHAT_ID, photo = ARTICLE_URL)
    time.sleep(8) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)

def HeungKuk_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    requests.packages.urllib3.disable_warnings()

    # 흥국 투자전략
    TARGET_URL_0 = 'http://www.heungkuksec.co.kr/research/industry/list.do'
    # 흥국 산업/기업 분석
    TARGET_URL_1 = 'http://www.heungkuksec.co.kr/research/company/list.do'
    
    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1)
    
    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        HeungKuk_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        time.sleep(5)
 
def HeungKuk_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    
    global NXT_KEY

    webpage = requests.get(TARGET_URL, verify=False)

    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")

    print('###첫실행구간###')
    soupList = soup.select('#content > table > tbody > tr > td.left > a')

    ARTICLE_BOARD_NAME = HEUNGKUK_BOARD_NAME[ARTICLE_BOARD_ORDER]
    FIRST_ARTICLE_TITLE = soupList[FIRST_ARTICLE_INDEX].text
    FIRST_ARTICLE_URL = 'http://www.heungkuksec.co.kr/research/industry/view.do?' + soupList[FIRST_ARTICLE_INDEX]['onclick'].replace("nav.go('view', '", "").replace("');", "").strip()
    
    # 연속키 저장 테스트 -> 테스트 후 연속키 지정 구간으로 변경
    KEY_DIR_FILE_NAME = './key/'+ str(SEC_FIRM_ORDER) + '-' + str(ARTICLE_BOARD_ORDER) + '.key' # => 파일형식 예시 : 1-0.key (앞자리: 증권사 순서, 뒷자리:게시판 순서)
    
    # 존재 여부 확인 후 연속키 파일 생성
    if not( os.path.isfile( KEY_DIR_FILE_NAME ) ): # 최초 실행 이거나 연속키 초기화
        # 연속키가 없는 경우 => 첫 게시글을 연속키로 저장
        print(FIRM_NAME[SEC_FIRM_ORDER],'의 ',BOARD_NAME[SEC_FIRM_ORDER][ARTICLE_BOARD_ORDER],'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
        NXT_KEY = Set_nxtKey(KEY_DIR_FILE_NAME, FIRST_ARTICLE_URL)
    else:   # 이미 실행
        NXT_KEY = Get_nxtKey(KEY_DIR_FILE_NAME, NXT_KEY)

    print('게시판 이름:', ARTICLE_BOARD_NAME) # 게시판 종류
    print('게시글 제목:', FIRST_ARTICLE_TITLE) # 게시글 제목
    print('게시글URL:', FIRST_ARTICLE_URL) # 주소
    print('연속URL:', NXT_KEY) # 주소
    print('############')

    for list in soupList:
        LIST_ARTICLE_URL = 'http://www.heungkuksec.co.kr/research/industry/view.do?'+list['onclick'].replace("nav.go('view', '", "").replace("');", "").strip()
        LIST_ARTICLE_TITLE = list.text
        if NXT_KEY != LIST_ARTICLE_URL or NXT_KEY == '': #  
            HeungKuk_downloadFile(LIST_ARTICLE_URL)
            send(ARTICLE_BOARD_NAME = ARTICLE_BOARD_NAME, ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)        
            print('메세지 전송 URL:', LIST_ARTICLE_URL)
        else:
            print('새로운 게시물을 모두 발송하였습니다.')
            Set_nxtKey(KEY_DIR_FILE_NAME, FIRST_ARTICLE_URL)
            return True

def HeungKuk_downloadFile(ARTICLE_URL):
    global ATTACH_FILE_NAME

    webpage = requests.get(ARTICLE_URL, verify=False)    
    
    # 첨부파일 URL
    attachFileCode = BeautifulSoup(webpage.content, "html.parser").select_one('div.div_01 > a')['href']
    ATTACH_URL = 'http://www.heungkuksec.co.kr/' + attachFileCode
    print('첨부파일 URL : ',ATTACH_URL)
    # 첨부파일 이름
    ATTACH_FILE_NAME = BeautifulSoup(webpage.content, "html.parser").select_one('td.col_b669ad.left').text.strip()+ ".pdf"
    print('첨부파일이름 : ',ATTACH_FILE_NAME)
    DownloadFile(URL = ATTACH_URL, FILE_NAME = ATTACH_FILE_NAME)
    time.sleep(5) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)

def SangSangIn_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    requests.packages.urllib3.disable_warnings()

    # 흥국 투자전략
    TARGET_URL_0 =  'http://www.sangsanginib.com/noticeList.fn?sgrp=S01&siteCmsCd=CM0001&topCmsCd=CM0004&cmsCd=CM0338&pnum=2&cnum=3'
    # 흥국 산업/기업 분석
    TARGET_URL_1 =  'http://www.sangsanginib.com/stocksList.fn?sgrp=S01&siteCmsCd=CM0001&topCmsCd=CM0004&cmsCd=CM0079&pnum=3&cnum=4'
    
    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1)
    
    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        SangSangIn_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        time.sleep(5)
 
def SangSangIn_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY

    webpage = requests.get(TARGET_URL, verify=False)

    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")

    print('###첫실행구간###')
    soupList = soup.select('#contents > div > div.bbs_a_type > table > tbody > tr > td.con > a')
    ARTICLE_BOARD_NAME = SANGSANGIN_BOARD_NAME[ARTICLE_BOARD_ORDER]
    FIRST_ARTICLE_TITLE = soupList[FIRST_ARTICLE_INDEX].text
    FIRST_ARTICLE_URL = 'http://www.sangsanginib.com' + soupList[FIRST_ARTICLE_INDEX]['href'] #.replace("nav.go('view', '", "").replace("');", "").strip()
    

    # 연속키 저장 테스트 -> 테스트 후 연속키 지정 구간으로 변경
    KEY_DIR_FILE_NAME = './key/'+ str(SEC_FIRM_ORDER) + '-' + str(ARTICLE_BOARD_ORDER) + '.key' # => 파일형식 예시 : 1-0.key (앞자리: 증권사 순서, 뒷자리:게시판 순서)
    
    # 존재 여부 확인 후 연속키 파일 생성
    if not( os.path.isfile( KEY_DIR_FILE_NAME ) ): # 최초 실행 이거나 연속키 초기화
        # 연속키가 없는 경우 => 첫 게시글을 연속키로 저장
        print(FIRM_NAME[SEC_FIRM_ORDER],'의 ',BOARD_NAME[SEC_FIRM_ORDER][ARTICLE_BOARD_ORDER],'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
        NXT_KEY = Set_nxtKey(KEY_DIR_FILE_NAME, FIRST_ARTICLE_TITLE)
    else:   # 이미 실행
        NXT_KEY = Get_nxtKey(KEY_DIR_FILE_NAME, NXT_KEY)

    print('게시판 이름:', ARTICLE_BOARD_NAME) # 게시판 종류
    print('게시글 제목:', FIRST_ARTICLE_TITLE) # 게시글 제목
    print('게시글URL:', FIRST_ARTICLE_URL) # 주소
    print('연속URL:', NXT_KEY) # 주소
    print('############')

    for list in soupList:
        LIST_ARTICLE_URL = 'http://www.sangsanginib.com' +list['href']
        LIST_ARTICLE_TITLE = list.text
        if NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '': #  
            SangSangIn_downloadFile(LIST_ARTICLE_URL)
            send(ARTICLE_BOARD_NAME = ARTICLE_BOARD_NAME, ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)        
            print('메세지 전송 URL:', LIST_ARTICLE_URL)
        else:
            print('새로운 게시물을 모두 발송하였습니다.')
            Set_nxtKey(KEY_DIR_FILE_NAME, FIRST_ARTICLE_TITLE)
            return True

def SangSangIn_downloadFile(ARTICLE_URL):
    global ATTACH_FILE_NAME

    webpage = requests.get(ARTICLE_URL, verify=False)    
    
    # 첨부파일 URL
    attachFileCode = BeautifulSoup(webpage.content, "html.parser").select_one('#contents > div > div.bbs_a_view > dl.b_bottom > dd > em:nth-child(1) > a')['href']
    ATTACH_URL = 'http://www.sangsanginib.com' + attachFileCode
    print('첨부파일 URL : ',ATTACH_URL)
    # 첨부파일 이름
    ATTACH_FILE_NAME = BeautifulSoup(webpage.content, "html.parser").select_one('#contents > div > div.bbs_a_view > dl.b_bottom > dd > em:nth-child(1) > a').text.strip()
    print('첨부파일이름 : ',ATTACH_FILE_NAME)
    DownloadFile(URL = ATTACH_URL, FILE_NAME = ATTACH_FILE_NAME)
    time.sleep(5) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)

def HANA_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    requests.packages.urllib3.disable_warnings()

    # 하나금융 Daily
    TARGET_URL_0 =  'https://www.hanaw.com/main/research/research/list.cmd?pid=4&cid=1'
    # 하나금융 산업 분석
    TARGET_URL_1 =  'https://www.hanaw.com/main/research/research/list.cmd?pid=3&cid=1'
    # 하나금융 기업 분석
    TARGET_URL_2 =  'https://www.hanaw.com/main/research/research/list.cmd?pid=3&cid=2'
    
    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1, TARGET_URL_2)

    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        HANA_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        time.sleep(5)
 
def HANA_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    
    global NXT_KEY

    webpage = requests.get(TARGET_URL, verify=False)

    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")
    soupList = soup.select('#container > div.rc_area_con > div.daily_bbs.m-mb20 > ul > li')

    print('###첫실행구간###')
    ARTICLE_BOARD_NAME = HANA_BOARD_NAME[ARTICLE_BOARD_ORDER]
    FIRST_ARTICLE_TITLE = soup.select('#container > div.rc_area_con > div.daily_bbs.m-mb20 > ul > li:nth-child(1) > div.con > ul > li.mb4 > h3 > a:nth-child(1)')[FIRST_ARTICLE_INDEX].text.strip()
    FIRST_ARTICLE_URL =  'https://www.hanaw.com' + soup.select('#container > div.rc_area_con > div.daily_bbs.m-mb20 > ul > li:nth-child(1) > div.con > ul > li:nth-child(5) > div > a')[FIRST_ARTICLE_INDEX].attrs['href']

    print('FIRST_ARTICLE_TITLE:',FIRST_ARTICLE_TITLE)
    print('FIRST_ARTICLE_URL:',FIRST_ARTICLE_URL)
    # 연속키 저장 테스트 -> 테스트 후 연속키 지정 구간으로 변경
    KEY_DIR_FILE_NAME = './key/'+ str(SEC_FIRM_ORDER) + '-' + str(ARTICLE_BOARD_ORDER) + '.key' # => 파일형식 예시 : 1-0.key (앞자리: 증권사 순서, 뒷자리:게시판 순서)
    
    # 존재 여부 확인 후 연속키 파일 생성
    if not( os.path.isfile( KEY_DIR_FILE_NAME ) ): # 최초 실행 이거나 연속키 초기화
        # 연속키가 없는 경우 => 첫 게시글을 연속키로 저장
        print(FIRM_NAME[SEC_FIRM_ORDER],'의 ',BOARD_NAME[SEC_FIRM_ORDER][ARTICLE_BOARD_ORDER],'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
        NXT_KEY = Set_nxtKey(KEY_DIR_FILE_NAME, FIRST_ARTICLE_TITLE)
    else:   # 이미 실행
        NXT_KEY = Get_nxtKey(KEY_DIR_FILE_NAME, NXT_KEY)

    print('게시판 이름:', ARTICLE_BOARD_NAME) # 게시판 종류
    print('게시글 제목:', FIRST_ARTICLE_TITLE) # 게시글 제목
    print('게시글URL:', FIRST_ARTICLE_URL) # 주소
    print('연속URL:', NXT_KEY) # 주소
    print('############')

    for list in soupList:
        LIST_ARTICLE_TITLE = list.select_one('div.con > ul > li.mb4 > h3 > a').text.strip()
        LIST_ARTICLE_URL =  'https://www.hanaw.com' + list.select_one('div.con > ul > li:nth-child(5) > div > a').attrs['href']
        LIST_ATTACT_FILE_NAME = list.select_one('div.con > ul > li:nth-child(5) > div > a').text

        if NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '': #  
            HANA_downloadFile(LIST_ARTICLE_URL, LIST_ATTACT_FILE_NAME)
            send(ARTICLE_BOARD_NAME = ARTICLE_BOARD_NAME, ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)
            print('메세지 전송 URL:', LIST_ARTICLE_URL)
        else:
            print('새로운 게시물을 모두 발송하였습니다.')
            print('이거>>>>',LIST_ARTICLE_TITLE)
            Set_nxtKey(KEY_DIR_FILE_NAME, FIRST_ARTICLE_TITLE)
            return True

def HANA_downloadFile(LIST_ARTICLE_URL, LIST_ATTACT_FILE_NAME):
    global ATTACH_FILE_NAME
    ATTACH_FILE_NAME = LIST_ATTACT_FILE_NAME #BeautifulSoup(webpage.content, "html.parser").select_one('#contents > div > div.bbs_a_view > dl.b_bottom > dd > em:nth-child(1) > a').text.strip()
    print('첨부파일이름 : ',ATTACH_FILE_NAME)
    DownloadFile(URL = ATTACH_URL, FILE_NAME = ATTACH_FILE_NAME)    
    time.sleep(5) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)

def YUANTA_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    requests.packages.urllib3.disable_warnings()

    # 흥국 투자전략
    TARGET_URL_0 =  'https://www.myasset.com/myasset/research/rs_list/rs_view.cmd?cd006=&cd007=RE02&cd008=&searchKeyGubun=&keyword=&jongMok_keyword=&keyword_in=&startCalendar=&endCalendar=&pgCnt=&page=&SEQ=167479'
    # 흥국 산업/기업 분석
    TARGET_URL_1 =  'https://www.myasset.com/myasset/research/rs_list/rs_list.cmd?cd006=&cd007=RE02&cd008='
    
    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1)
    
    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        YUANTA_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        time.sleep(5)
 
def YUANTA_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY

    webpage = requests.get(TARGET_URL, verify=False)

    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")

    print('###첫실행구간###')
    return print(soup)
    soupList = soup.select('#RS_0201001_P1_FORM > div.tblRow.txtC.mHide.noVLine.js-tblHead > table > tbody ')

    ARTICLE_BOARD_NAME = SANGSANGIN_BOARD_NAME[ARTICLE_BOARD_ORDER]
    FIRST_ARTICLE_TITLE = soupList[FIRST_ARTICLE_INDEX].text
    FIRST_ARTICLE_URL = 'http://www.sangsanginib.com' + soupList[FIRST_ARTICLE_INDEX]['href'] #.replace("nav.go('view', '", "").replace("');", "").strip()
    

    # 연속키 저장 테스트 -> 테스트 후 연속키 지정 구간으로 변경
    KEY_DIR_FILE_NAME = './key/'+ str(SEC_FIRM_ORDER) + '-' + str(ARTICLE_BOARD_ORDER) + '.key' # => 파일형식 예시 : 1-0.key (앞자리: 증권사 순서, 뒷자리:게시판 순서)
    
    # 존재 여부 확인 후 연속키 파일 생성
    if not( os.path.isfile( KEY_DIR_FILE_NAME ) ): # 최초 실행 이거나 연속키 초기화
        # 연속키가 없는 경우 => 첫 게시글을 연속키로 저장
        print(FIRM_NAME[SEC_FIRM_ORDER],'의 ',BOARD_NAME[SEC_FIRM_ORDER][ARTICLE_BOARD_ORDER],'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
        NXT_KEY = Set_nxtKey(KEY_DIR_FILE_NAME, FIRST_ARTICLE_TITLE)
    else:   # 이미 실행
        NXT_KEY = Get_nxtKey(KEY_DIR_FILE_NAME, NXT_KEY)

    print('게시판 이름:', ARTICLE_BOARD_NAME) # 게시판 종류
    print('게시글 제목:', FIRST_ARTICLE_TITLE) # 게시글 제목
    print('게시글URL:', FIRST_ARTICLE_URL) # 주소
    print('연속URL:', NXT_KEY) # 주소
    print('############')

    for list in soupList:
        LIST_ARTICLE_URL = 'http://www.sangsanginib.com' +list['href']
        LIST_ARTICLE_TITLE = list.text
        if NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '': #  
            YUANTA_downloadFile(LIST_ARTICLE_URL)
            send(ARTICLE_BOARD_NAME = ARTICLE_BOARD_NAME, ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)        
            print('메세지 전송 URL:', LIST_ARTICLE_URL)
        else:
            print('새로운 게시물을 모두 발송하였습니다.')
            Set_nxtKey(KEY_DIR_FILE_NAME, FIRST_ARTICLE_TITLE)
            return True

def YUANTA_downloadFile(ARTICLE_URL):
    global ATTACH_FILE_NAME

    webpage = requests.get(ARTICLE_URL, verify=False)    
    
    # 첨부파일 URL
    attachFileCode = BeautifulSoup(webpage.content, "html.parser").select_one('#contents > div > div.bbs_a_view > dl.b_bottom > dd > em:nth-child(1) > a')['href']
    ATTACH_URL = 'http://www.sangsanginib.com' + attachFileCode
    print('첨부파일 URL : ',ATTACH_URL)
    # 첨부파일 이름
    ATTACH_FILE_NAME = BeautifulSoup(webpage.content, "html.parser").select_one('#contents > div > div.bbs_a_view > dl.b_bottom > dd > em:nth-child(1) > a').text.strip()
    print('첨부파일이름 : ',ATTACH_FILE_NAME)
    DownloadFile(URL = ATTACH_URL, FILE_NAME = ATTACH_FILE_NAME)
    time.sleep(5) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)

# param
# KEY_DIR_FILE_NAME : 연속키 파일 경로
# NXT_KEY : 연속키 게시물 URL
# KEY_DIR_FILE_NAME 경로에 NXT_KEY 읽기
# return : NXT_KEY
def Get_nxtKey(KEY_DIR_FILE_NAME, NXT_KEY):
    file = open( KEY_DIR_FILE_NAME , 'r')    # hello.txt 파일을 쓰기 모드(w)로 열기. 파일 객체 반환
    NXT_KEY = file.readline()       # 파일 내 데이터 읽기
    print('Get_nxtKey')
    print('NXT_KEY:',NXT_KEY, '연속키 파일 경로 :',KEY_DIR_FILE_NAME)
    file.close()                     # 파일 객체 닫기
    return NXT_KEY

# param
# KEY_DIR_FILE_NAME : 연속키 파일 경로
# NXT_KEY : 연속키 게시물 URL
# KEY_DIR_FILE_NAME 경로에 NXT_KEY 저장
def Set_nxtKey(KEY_DIR_FILE_NAME, NXT_KEY):
    file = open( KEY_DIR_FILE_NAME , 'w')    # hello.txt 파일을 쓰기 모드(w)로 열기. 파일 객체 반환
    file.write( NXT_KEY )      # 파일에 문자열 저장
    print('Set_nxtKey')
    print('NXT_KEY:',NXT_KEY, '연속키 파일 경로 :',KEY_DIR_FILE_NAME)
    file.close()                     # 파일 객체 닫기
    return NXT_KEY

def DownloadFile(URL, FILE_NAME):
    global ATTACH_FILE_NAME
    print("DownloadFile()")
    ATTACH_FILE_NAME = re.sub('[\/:*?"<>|]','',FILE_NAME)
    print('convert ATTACH_FILE_NAME:',ATTACH_FILE_NAME)
    with open(ATTACH_FILE_NAME, "wb") as file:   # open in binary mode
        response = get(URL, verify=False)               # get request
        file.write(response.content)      # write to file
        
    return
# 액션 플랜 
# 1. 10분 간격으로 게시글을 읽어옵니다.
# 2. 게시글이 마지막 게시글이 이전 게시글과 다른 경우(새로운 게시글이 올라온 경우) 
    # 메세지로 게시글 정보를 보냅니다
    # 아닌 경우 다시 1번을 반복합니다.

def MySQL_TEST():
    print('MySQL_TEST')
    # Register database schemes in URLs.
    # urlparse.uses_netloc.append('mysql')
    # url = urlparse.urlparse(os.environ['mysql://b0464b22432146:290edeca@us-cdbr-east-03.cleardb.com/heroku_31ee6b0421e7ff9?reconnect=true'])
    print(os.environ['CLEARDB_DATABASE_URL'])
    try:

        # Check to make sure DATABASES is set in settings.py file.
        # If not default to {}

        if 'DATABASES' not in locals():
            DATABASES = {}

        if 'DATABASE_URL' in os.environ:
            url = urlparse.urlparse(os.environ['CLEARDB_DATABASE_URL'])

            # Ensure default database exists.
            DATABASES['default'] = DATABASES.get('default', {})

            # Update with environment configuration.
            DATABASES['default'].update({
                'NAME': url.path[1:],
                'USER': url.username,
                'PASSWORD': url.password,
                'HOST': url.hostname,
                'PORT': url.port,
            })
            conn = pymysql.connect(host=url.hostname, user=url.username, password=url.password, charset='utf8') 

            cursor = conn.cursor() 

            sql = "SELECT * FROM NXT_KEY" 

            cursor.execute(sql) 
            res = cursor.fetchall() 

            for data in res: 
                    print(data) 

            conn.commit() 
            conn.close() 

            # if url.scheme == 'mysql':
            #     DATABASES['default']['ENGINE'] = 'django.db.backends.mysql'
    except Exception:
        print('Unexpected error:', sys.exc_info())
        return

def main():
    global SEC_FIRM_ORDER  # 증권사 순번
    print('MySQL 연동 테스트')
    MySQL_TEST()
    print('########Program Start Run########')
    print('key폴더가 존재하지 않는 경우 무조건 생성합니다.')
    os.makedirs('./key', exist_ok=True)

    # SEC_FIRM_ORDER는 임시코드 추후 로직 추가 예정 
    while True:
              
        # SEC_FIRM_ORDER = 0 
        # print("EBEST_checkNewArticle() => 새 게시글 정보 확인")
        # EBEST_checkNewArticle()
        
        # SEC_FIRM_ORDER = 1
        # print("HeungKuk_checkNewArticle() => 새 게시글 정보 확인")
        # HeungKuk_checkNewArticle()        

        # SEC_FIRM_ORDER = 2
        # print("SangSangIn_checkNewArticle() => 새 게시글 정보 확인")
        # SangSangIn_checkNewArticle()

        # SEC_FIRM_ORDER = 3
        # print("HANA_checkNewArticle() => 새 게시글 정보 확인")
        # HANA_checkNewArticle()
        
        # SEC_FIRM_ORDER = 'SEDAILY'
        # print("SEDAILY_checkNewArticle() => 새 게시글 정보 확인")
        # SEDAILY_checkNewArticle()

        # SEC_FIRM_ORDER = 4
        # print("YUANTA_checkNewArticle() => 새 게시글 정보 확인")
        # YUANTA_checkNewArticle()


        print('######',REFRESH_TIME,'초 후 게시글을 재 확인 합니다.######')        
        time.sleep(REFRESH_TIME)

if __name__ == "__main__":
	main()
