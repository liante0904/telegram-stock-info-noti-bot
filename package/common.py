# -*- coding:utf-8 -*- 
import os
import sys
import datetime
from pytz import timezone
import telegram
import datetime
import time
import json
import re
import asyncio
import urllib.parse as urlparse
import urllib.request

from package import googledrive

# TEST 

# import secretkey

from requests import get  # to make GET request

# 로직 설명
# 1. Main()-> 각 회사별 함수를 통해 반복 (추후 함수명 일괄 변경 예정)
#   - checkNewArticle -> parse -> downloadFile -> Send 
# 2. 연속키의 경우 현재 .key로 저장
#   - 추후 heroku db로 처리 예정(MySQL)
#   - DB연결이 안되는 경우, Key로 처리할수 있도록 예외처리 반영
# 3. 최초 조회되는 게시판 혹은 Key값이 없는 경우 메세지를 발송하지 않음.
# 4. 테스트와 운영을 구분하여 텔레그램 발송 채널 ID 구분 로직 추가
#   - 어떻게 구분지을지 생각해봐야함
# 5. 메시지 발송 방법 변경 (봇 to 사용자 -> 채널에 발송)

###########패키지 변수############
SECRETKEY = ""

############공용 상수############
# sleep key
SLEEP_KEY_DIR_FILE_NAME = './key/sleep.key'
INTERVAL_TIME = 3 # 10분 단위 적용
INTERVAL_INIT_TIME = 1

# 게시글 갱신 시간
REFRESH_TIME = 60 * 20 # 20분

# 연속키URL
NXT_KEY = ''
NXT_KEY_ARTICLE_TITLE = ''

# 게시판 URL
BOARD_URL = ''

# 테스트 발송여부
TEST_SEND_YN = ''

# 텔레그램 채널 발송 여부
SEND_YN = ''
TODAY_SEND_YN = ''

# 텔레그램 마지막 메세지 발송시간(단위 초)
SEND_TIME_TERM = 0 # XX초 전에 해당 증권사 메시지 발송

# 첫번째URL 
FIRST_ARTICLE_URL = ''

# SendAddText 글로벌 변수
SEND_ADD_MESSAGE_TEXT = ''

# LOOP 인덱스 변수
SEC_FIRM_ORDER = 0 # 증권사 순번
ARTICLE_BOARD_ORDER = 0 # 게시판 순번

# 이모지
EMOJI_FIRE = u'\U0001F525'
EMOJI_PICK = u'\U0001F449'

# 연속키용 상수
FIRST_ARTICLE_INDEX = 0

# 메세지 전송용 레포트 제목(말줄임표 사용 증권사)
LIST_ARTICLE_TITLE = ''


#################### global 변수 정리 ###################################
FIRM_NM = ''
BOARD_NM = ''
#################### global 변수 정리 끝###################################

async def sendAlertMessage(sendMessageText): #실행시킬 함수명 임의지정
    global CHAT_ID
    bot = telegram.Bot(token = SECRETKEY.TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)
    return await bot.sendMessage(chat_id = SECRETKEY.TELEGRAM_CHANNEL_ID_REPORT_ALARM, text = sendMessageText, disable_web_page_preview = True)

async def sendMessage(sendMessageText): #실행시킬 함수명 임의지정
    global CHAT_ID
    bot = telegram.Bot(token = SECRETKEY.TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)
    return await bot.sendMessage(chat_id = GetSendChatId(), text = sendMessageText, disable_web_page_preview = True, parse_mode = "Markdown")

async def sendDocument(ATTACH_FILE_NAME): #실행시킬 함수명 임의지정
    global CHAT_ID
    bot = telegram.Bot(token = SECRETKEY.TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)
    return await bot.sendDocument(chat_id = GetSendChatId(), document = open(ATTACH_FILE_NAME, 'rb'))

# 최초 send함수
# URL(프리뷰해제) 발송 + 해당 레포트 pdf 발송
def send(ARTICLE_BOARD_NAME , ARTICLE_TITLE , ARTICLE_URL): # 파일의 경우 전역변수로 처리 (downloadFile 함수)
    global CHAT_ID

    print('send()')
    DISABLE_WEB_PAGE_PREVIEW = True # 메시지 프리뷰 여부 기본값 설정

    # 실제 전송할 메시지 작성
    sendMessageText = ''
    sendMessageText += GetSendMessageTitle()
    sendMessageText += ARTICLE_TITLE + "\n"
    sendMessageText += EMOJI_PICK + ARTICLE_URL 

    #생성한 텔레그램 봇 정보(@ebest_noti_bot)
    bot = telegram.Bot(token = SECRETKEY.TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)

    #생성한 텔레그램 봇 정보 출력
    #me = bot.getMe()
    #print('텔레그램 채널 정보 :',me)

    if SEC_FIRM_ORDER == 999 or SEC_FIRM_ORDER == 998 or SEC_FIRM_ORDER == 997 : # 매매동향의 경우 URL만 발송하여 프리뷰 처리 
        DISABLE_WEB_PAGE_PREVIEW = False

    #bot.sendMessage(chat_id = GetSendChatId(), text = sendMessageText, disable_web_page_preview = DISABLE_WEB_PAGE_PREVIEW)
    

    if DISABLE_WEB_PAGE_PREVIEW: # 첨부파일이 있는 경우 => 프리뷰는 사용하지 않음
        try:
            time.sleep(1) # 메시지 전송 텀을 두어 푸시를 겹치지 않게 함
            #bot.sendDocument(chat_id = GetSendChatId(), document = open(ATTACH_FILE_NAME, 'rb'))
            r = asyncio.run(sendDocument(ATTACH_FILE_NAME)) #봇 실행하는 코드
            os.remove(ATTACH_FILE_NAME) # 파일 전송 후 PDF 삭제
            return r
        except:
            return
    else: 
        return asyncio.run(sendMessage(sendMessageText)) #봇 실행하는 코드    
    
    time.sleep(1) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)

# URL 발신용 전용 함수 : ex) 네이버 뉴스
def sendURL(ARTICLE_BOARD_NAME , ARTICLE_TITLE , ARTICLE_URL): # 파일의 경우 전역변수로 처리 (downloadFile 함수)
    global CHAT_ID

    print('sendURL()')

    # 실제 전송할 메시지 작성
    sendMessageText = ''
    # sendMessageText += GetSendMessageTitle()
    sendMessageText += ARTICLE_TITLE + "\n"
    sendMessageText += EMOJI_PICK + ARTICLE_URL 

    #생성한 텔레그램 봇 정보 assign (@ebest_noti_bot)
    bot = telegram.Bot(token = SECRETKEY.TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)

    #생성한 텔레그램 봇 정보 출력
    #me = bot.getMe()
    #print('텔레그램 채널 정보 :',me)

    #bot.sendMessage(chat_id = GetSendChatId(), text = sendMessageText)
    return asyncio.run(sendMessage(sendMessageText)) #봇 실행하는 코드

def sendPhoto(ARTICLE_URL): # 파일의 경우 전역변수로 처리 (downloadFile 함수)
    print('sendPhoto()')

    #생성한 텔레그램 봇 정보(@ebest_noti_bot)
    bot = telegram.Bot(token = SECRETKEY.TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)

    return bot.sendPhoto(chat_id = GetSendChatId(), photo = ARTICLE_URL)
    time.sleep(1) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)

# 가공없이 텍스트를 발송합니다.
def sendText(sendMessageText): 
    global CHAT_ID

    #생성한 텔레그램 봇 정보(@ebest_noti_bot)
    bot = telegram.Bot(token = SECRETKEY.TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)
    #bot.sendMessage(chat_id = GetSendChatId(), text = sendMessageText, disable_web_page_preview = True, parse_mode = "Markdown")
    return asyncio.run(sendMessage(sendMessageText)) #봇 실행하는 코드
    time.sleep(1) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)

# 인자 텍스트를 더해가며 발송합니다. 
# 더해진 텍스트가 텔레그램 제한인 3500자를 넘어가면 발송처리하고 초기화합니다
# 두번째 인자는 첫번째 인자 텍스트를 앞으로 더할지 뒤로 더할지 결정합니다. (F: 앞, B: 뒤에 텍스트를 더합니다)
# 인자를 결정하지 않은 경우 텍스트를 뒤로 붙이도록 설정
# 두번째 파라미터가 Y인 경우 길이와 상관없이 발송처리(집계된 데이터 발송용)
def sendAddText(sendMessageText, sendType='N'): 
    global SEND_ADD_MESSAGE_TEXT

    SEND_ADD_MESSAGE_TEXT += sendMessageText
    print('sendType ', sendType)
    print('sendMessageText ',sendMessageText)
    print('SEND_ADD_MESSAGE_TEXT ', SEND_ADD_MESSAGE_TEXT)

    if len(SEND_ADD_MESSAGE_TEXT) > 3500 or ( sendType == 'Y' and len(SEND_ADD_MESSAGE_TEXT) > 0 ) :
        print("sendAddText() (실제 발송요청)\n", SEND_ADD_MESSAGE_TEXT)
        sendText(SEND_ADD_MESSAGE_TEXT)
        SEND_ADD_MESSAGE_TEXT = ''

    return ''

def sendMarkdown(INDEX, ARTICLE_BOARD_NAME , ARTICLE_TITLE , ARTICLE_URL, ATTACH_URL): # 파일의 경우 전역변수로 처리 (downloadFile 함수)
    global CHAT_ID
    global sendMessageText

    print('sendMarkdown()')
    DISABLE_WEB_PAGE_PREVIEW = True # 메시지 프리뷰 여부 기본값 설정

    # 첫 인덱스 타이틀
    if INDEX == 0:
        sendMessageText = ''
        sendMessageText += GetSendMessageTitle()

    sendMessageText += ARTICLE_TITLE + "\n" 

    # 원문 링크 , 레포트 링크
    if SEC_FIRM_ORDER == 996:
        sendMessageText += EMOJI_PICK  + "[원문링크(클릭)]" + "("+ ARTICLE_URL + ")"  + "\n" 
    else:
        sendMessageText += EMOJI_PICK  + "[원문링크(클릭)]" + "("+ ARTICLE_URL + ")" + "        "+ EMOJI_PICK + "[레포트링크(클릭)]" + "("+ ATTACH_URL + ")"

    if SEC_FIRM_ORDER == 996 and INDEX == 0 : return # 공매도 잔고의 경우 2건이상 일때 발송

    #생성한 텔레그램 봇 정보 assign (@ebest_noti_bot)
    bot = telegram.Bot(token = SECRETKEY.TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)

    #bot.sendMessage(chat_id = GetSendChatId(), text = sendMessageText, disable_web_page_preview = True, parse_mode = "Markdown")
    return asyncio.run(sendMessage(sendMessageText)) #봇 실행하는 코드
    time.sleep(1) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)

# URL에 파일명을 사용할때 한글이 포함된 경우 인코딩처리 로직 추가 
def DownloadFile(URL, FILE_NAME):
    global ATTACH_FILE_NAME
    print("DownloadFile()")

    if SEC_FIRM_ORDER == 6: # 교보증권 예외 로직
        # 로직 사유 : 레포트 첨부파일명에 한글이 포함된 경우 URL처리가 되어 있지 않음
        CONVERT_URL = URL 
        for c in URL: # URL내 한글이 있는 경우 인코딩 처리(URL에 파일명을 이용하여 조합함)
            # 코드셋 기준 파이썬:UTF-8 . 교보증권:EUC-KR
            # 1. 주소에서 한글 문자를 판별
            # 2. 해당 문자를 EUC-KR로 변환후 URL 인코딩
            print("##",c , "##", ord('가') <= ord(c) <= ord('힣') )
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
    FILE_NAME = str(GetCurrentDate('YYYYMMDD')[2:8]) + "_" + BOARD_NM + "_" + FILE_NAME + "_" + FIRM_NM

    # 파일명 길이 체크 후, 길면 자르고, 확장자 붙여 마무리함
    MAX_FILE_NAME_LENGTH = 240
    if len(FILE_NAME)  > MAX_FILE_NAME_LENGTH : FILE_NAME = FILE_NAME[0:MAX_FILE_NAME_LENGTH]
    FILE_NAME += '.pdf'
    # if '.pdf' not in FILE_NAME : FILE_NAME = FILE_NAME + '.pdf'

    ATTACH_FILE_NAME = re.sub('[\/:*?"<>|]','',FILE_NAME) # 저장할 파일명 : 파일명으로 사용할수 없는 문자 삭제 변환
    print('convert URL:',URL)
    print('convert ATTACH_FILE_NAME:',ATTACH_FILE_NAME)
    with open(ATTACH_FILE_NAME, "wb")as file:  # open in binary mode
        response = get(URL, verify=False)     # get request
        file.write(response.content) # write to file
        
    r = googledrive.upload(str(ATTACH_FILE_NAME))
    print('********************')
    print(f'main URL {r}')
    return r

def GetSendMessageText(INDEX, ARTICLE_BOARD_NAME , ARTICLE_TITLE , ARTICLE_URL):
    # 실제 전송할 메시지 작성
    sendMessageText = ''
    # 발신 게시판 종류
    # if INDEX == 1:
    #     sendMessageText += GetSendMessageTitle() + "\n"
    # 게시글 제목(굵게)
    sendMessageText += "*" + ARTICLE_TITLE.replace("_", " ").replace("*", "") + "*" + "\n"
    # 원문 링크
    sendMessageText += EMOJI_PICK  + "[원문링크(클릭)]" + "("+ ARTICLE_URL + ")"  + "\n" 

    return sendMessageText

# 실제 전송할 메시지 작성 
# 유형   : Markdown
# Paran  : ARTICLE_TITLE -> 레포트 제목  , ATTACH_URL -> 레포트 URL(PDF)
def GetSendMessageTextMarkdown(ARTICLE_TITLE , ATTACH_URL):
    
    sendMessageText = ''

    # 게시글 제목(굵게)
    sendMessageText += "*" + ARTICLE_TITLE.replace("_", " ").replace("*", "") + "*" + "\n"
    # 원문 링크
    sendMessageText += EMOJI_PICK  + "[원문링크(클릭)]" + "("+ ATTACH_URL + ")"  + "\n" 

    return sendMessageText
    
# 타이틀 생성 
# : 게시판 이름 삭제
def GetSendMessageTitle(): 
    SendMessageTitle = ""
    msgFirmName = ""
    
    if SEC_FIRM_ORDER == 999:
        msgFirmName = "매매동향"
    elif SEC_FIRM_ORDER == 998:
        msgFirmName = "네이버 - "
        if  ARTICLE_BOARD_ORDER == 0 : msgFirmName += "실시간 뉴스 속보"
        else: msgFirmName += "가장 많이 본 뉴스"
    elif SEC_FIRM_ORDER == 997: msgFirmName = "아이투자 - 랭킹스탁"
    elif SEC_FIRM_ORDER == 996: msgFirmName = "연합인포맥스 - 공매도 잔고 상위"
    elif SEC_FIRM_ORDER == 995: msgFirmName = "조선비즈 - C-Biz봇"
    elif SEC_FIRM_ORDER == 994: msgFirmName = "매경 증권 52주 신고저가 알림"
    elif SEC_FIRM_ORDER == 900: 
        msgFirmName = "[네이버 증권 "
        if ARTICLE_BOARD_ORDER == 0 : msgFirmName += "기업 리서치](https://m.stock.naver.com/investment/research/company)"
        elif ARTICLE_BOARD_ORDER == 1:  msgFirmName += "산업 리서치](https://m.stock.naver.com/investment/research/industry)"
        else: print(msgFirmName)
    elif SEC_FIRM_ORDER == 123: msgFirmName = "[오늘의 레포트](https://comp.fnguide.com/SVO/WooriRenewal/Report.asp)"
    else: # 증권사
        msgFirmName =  FIRM_NM 

    # SendMessageTitle += "\n" + EMOJI_FIRE + msgFirmName + EMOJI_FIRE + "\n" 
    SendMessageTitle += "\n\n" + " ●"+  msgFirmName + "\n" 
    
    return SendMessageTitle

def GetSendChatId():
    SendMessageChatId = 0
    if SEC_FIRM_ORDER == 998:
        if  ARTICLE_BOARD_ORDER == 0 : 
            SendMessageChatId = SECRETKEY.TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS # 네이버 실시간 속보 뉴스 채널
        else:
            SendMessageChatId = SECRETKEY.TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS # 네이버 많이본 뉴스 채널
    elif SEC_FIRM_ORDER == 997:
            SendMessageChatId = SECRETKEY.TELEGRAM_CHANNEL_ID_ITOOZA # 아이투자
    elif SEC_FIRM_ORDER == 995:
            SendMessageChatId = SECRETKEY.TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT # 조선비즈 C-bot
    elif SEC_FIRM_ORDER == 123: # 오늘의 레포트 채널 나누기 
        SendMessageChatId = SECRETKEY.TELEGRAM_CHANNEL_ID_TODAY_REPORT # 오늘의 레포트 채널
    elif SEC_FIRM_ORDER == 12: # 한경컨센 나누기
        SendMessageChatId = SECRETKEY.TELEGRAM_CHANNEL_ID_HANKYUNG_CONSEN # 한경 컨센
    else:
        SendMessageChatId = SECRETKEY.TELEGRAM_CHANNEL_ID_REPORT_ALARM # 운영 채널(증권사 신규 레포트 게시물 알림방)
    
    # SendMessageChatId = SECRETKEY.TELEGRAM_CHANNEL_ID_TEST
    return SendMessageChatId

def GetJsonData(TARGET_URL, METHOD_TYPE):
    global NXT_KEY
    global TEST_SEND_YN
    request = urllib.request.Request(TARGET_URL, headers={'User-Agent': 'Mozilla/5.0'})
    #검색 요청 및 처리
    response = urllib.request.urlopen(request)
    rescode = response.getcode()
    if rescode != 200 :return print("ChosunBizBot_StockPlusJSONparse 접속이 원활하지 않습니다 ")

    try:
        jres = json.loads(response.read().decode('utf-8'))
    except:
        return True

    # jres = jres['newsItems']
    print(jres)
    return jres


def SetSleepTimeKey(*args):
    try: nSleepCntKey = args[0]
    except: nSleepCntKey = 0
    file = open( SLEEP_KEY_DIR_FILE_NAME , 'w')    # hello.txt 파일을 쓰기 모드(w)로 열기. 파일 객체 반환
    file.write(  str(nSleepCntKey) )      # 파일에 문자열 저장
    print('nSleepCntKey:',nSleepCntKey, '연속키 파일 경로 :',SLEEP_KEY_DIR_FILE_NAME)
    file.close()                     # 파일 객체 닫기
    
def GetSleepTimeKey(*args):
    # 존재 여부 확인 후 연속키 파일 생성
    if not( os.path.isfile( SLEEP_KEY_DIR_FILE_NAME ) ): # 최초 실행 이거나 연속키 초기화
        # 연속키가 없는 경우 => 첫 게시글을 연속키로 저장
        file = open( SLEEP_KEY_DIR_FILE_NAME , 'w')    # hello.txt 파일을 쓰기 모드(w)로 열기. 파일 객체 반환
        file.write(  str(INTERVAL_INIT_TIME) )      # 파일에 문자열 저장
        print('INTERVAL_INIT_TIME:',INTERVAL_INIT_TIME, '연속키 파일 경로 :',SLEEP_KEY_DIR_FILE_NAME)
        file.close()                     # 파일 객체 닫기
        return int(INTERVAL_INIT_TIME)
    else:   # 이미 실행
        file = open( SLEEP_KEY_DIR_FILE_NAME , 'r')    # hello.txt 파일을 쓰기 모드(w)로 열기. 파일 객체 반환
        SLEEP_KEY = file.readline()       # 파일 내 데이터 읽기
        print('SLEEP_KEY:', SLEEP_KEY)
        if SLEEP_KEY:
            print('SLEEP_KEY T')
        else:
            SLEEP_KEY = '0'
            
        print('Get_nxtKey')
        print('SLEEP_KEY:',SLEEP_KEY, '연속키 파일 경로 :',SLEEP_KEY_DIR_FILE_NAME)
        file.close()                     # 파일 객체 닫기
        return SLEEP_KEY

# 한국 시간 (timezone('Asia/Seoul')) 날짜 정보를 구합니다.
# 'yyyymmdd'
def GetCurrentDate(*args):

    time_now = str(datetime.datetime.now(timezone('Asia/Seoul')))[:19] # 밀리세컨즈 제거

    DATE = time_now[:10].strip()
    DATE_SPLIT = DATE.split("-")
    

    pattern = ''
    r = ''
    # r = ['y','m','d','Y','M','D']    
    if not args:
        pattern= ''.join(DATE_SPLIT) 
    else: pattern = args[0]
    # if ['y','m','d','Y','M','D'] not in pattern :  return ''.join(DATE_SPLIT)

    print('pattern->',pattern)
    pattern= pattern.replace('yyyy', DATE_SPLIT[0])
    pattern= pattern.replace('YYYY', DATE_SPLIT[0])
    pattern= pattern.replace('mm', DATE_SPLIT[1])
    pattern= pattern.replace('MM', DATE_SPLIT[1])
    pattern= pattern.replace('dd', DATE_SPLIT[2])
    pattern= pattern.replace('DD', DATE_SPLIT[2])


    print('최종', pattern)
    return pattern  