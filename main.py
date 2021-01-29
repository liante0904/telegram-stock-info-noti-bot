#!/usr/bin/env python
#pyenv https://www.daleseo.com/python-pyenv/
#https://kslee7746.tistory.com/entry/텔레그램-웹페이지-게시물-업데이트-알람-봇-만들기1
#https://besixdouze.net/24
#https://steemit.com/kr-dev/@maanya/30
#https://medium.com/@jesamkim/%EC%BD%94%EB%A1%9C%EB%82%9819-%EA%B5%AD%EB%82%B4-%EB%B0%9C%EC%83%9D-%ED%98%84%ED%99%A9-%ED%85%94%EB%A0%88%EA%B7%B8%EB%9E%A8-%EC%95%8C%EB%A6%BC%EB%B4%87-%EB%A7%8C%EB%93%A4%EA%B8%B0-792022cec710
# heroku : https://dashboard.heroku.com/apps
#pip3 install python-telegram-bot
#pip3 freeze > requirements.txt
#https://beomi.github.io/gb-crawling/posts/2017-04-20-HowToMakeWebCrawler-Notice-with-Telegram.html
# 텔레그램 알림 채널 만들기 : https://blex.me/@mildsalmon/%ED%95%9C%EB%9D%BC%EB%8C%80%ED%95%99%EA%B5%90-%EA%B3%B5%EC%A7%80-%EC%95%8C%EB%A6%BC-%EB%B4%87-%EC%A0%9C%EC%9E%91%EA%B8%B0-3-%EC%BD%94%EB%93%9C%EB%B6%84%EC%84%9D-telegrambot

# 작업 내용을 삭제하고 origin/master로 덮어쓰기 => git fetch --all && git reset --hard origin/master
# BOT_INFO_URL = https://api.telegram.org/bot1372612160:AAHVyndGDmb1N2yEgvlZ_DmUgShqk2F0d4w/getUpdates
# https://api.telegram.org/bot1372612160:AAHVyndGDmb1N2yEgvlZ_DmUgShqk2F0d4w/getMe

# mac vscode shortcut: https://code.visualstudio.com/shortcuts/keyboard-shortcuts-macos.pdf
import os
import telegram
import requests
import time
import ssl
from bs4 import BeautifulSoup
from requests import get  # to make GET request


############이베스트 전용 상수############

# 발송한 연속키
nNxtIdx = [0, 0, 0, 0, 0] 
# 새로 올라온 게시글 개수
nNewFeedCnt = 0

############공용 상수############
# 게시글 갱신 시간
REFRESH_TIME = 600

# 게시판 이름
EBEST_BOARD_NAME  = ["이슈브리프" , "기업분석", "산업분석", "투자전략", "Quant"]
HEUNGKUK_BOARD_NAME = ["투자전략", "산업/기업분석"]
SANGSANGIN_BOARD_NAME = ["산업리포트", "기업리포트"]

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
    global nNxtIdx
    global nNewFeedCnt

    webpage = requests.get(TARGET_URL, verify=False)

    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")
    
    # 현재 최근 게시글 인덱스
    ntotalIdx = int( soup.select('span.info')[0].text.replace("Total", "").replace("Page 1", "").strip() )
    print('게시판 이름:', EBEST_BOARD_NAME[ARTICLE_BOARD_ORDER],'전체 게시글', ntotalIdx, '게시글 연속키', nNxtIdx[ARTICLE_BOARD_ORDER])
    if nNxtIdx[ARTICLE_BOARD_ORDER] == 0: # 첫 실행인 경우 임의로 가장 마지막 게시글을 발송
        print('###첫실행구간###')
        # 게시글 제목
        soup = soup.find_all('td', class_='subject')

        ARTICLE_BOARD_NAME  = EBEST_BOARD_NAME[ARTICLE_BOARD_ORDER]
        ARTICLE_TITLE       = soup[FIRST_ARTICLE_INDEX].find('a').text
        ARTICLE_URL         = 'https://www.ebestsec.co.kr/EtwFrontBoard/' + soup[FIRST_ARTICLE_INDEX].find('a').attrs['href'].replace("amp;", "")
        print('게시판 이름:', ARTICLE_BOARD_NAME) # 게시판 종류
        print('게시글 제목:', ARTICLE_TITLE) # 게시글 제목
        print('게시글URL:', ARTICLE_URL) # 주소
        print('############')

        EBEST_downloadFile(ARTICLE_URL)
        send(ARTICLE_BOARD_NAME = ARTICLE_BOARD_NAME, ARTICLE_TITLE = ARTICLE_TITLE , ARTICLE_URL = ARTICLE_URL) # 파일의 경우 전역변수로 처리 (downloadFile 함수) # 서버 재 실행시 첫 발송 주석

        nNxtIdx[ARTICLE_BOARD_ORDER] = ntotalIdx # 첫 실행시 인덱스 설정

    else: # 두번째 실행인 경우
        print('###ELSE구간###')
        soup = soup.find_all('td', class_='subject')
        #nIdx = int(soup.select('tbody > tr > td')[0]) # 현재 게시글 번호
        nNewFeedCnt = ntotalIdx - nNxtIdx[ARTICLE_BOARD_ORDER] # 새로 올라온 게시글 개수
        
        print('### 새로운 게시글 개수:', nNewFeedCnt,' ###')
        while nNewFeedCnt > 0: # 새 게시글이 올라옴
            print('현재 게시판 :',EBEST_BOARD_NAME[ARTICLE_BOARD_ORDER],' 새로운 게시글 수:', nNewFeedCnt)

            ARTICLE_BOARD_NAME  = EBEST_BOARD_NAME[ARTICLE_BOARD_ORDER]
            ARTICLE_TITLE       = soup[nNewFeedCnt-1].find('a').text
            ARTICLE_URL         = 'https://www.ebestsec.co.kr/EtwFrontBoard/' + soup[nNewFeedCnt-1].find('a').attrs['href'].replace("amp;", "")
            print('게시판 이름:', ARTICLE_BOARD_NAME) # 게시판 종류
            print('게시글 제목:', ARTICLE_TITLE) # 게시글 제목
            print('게시글URL:', ARTICLE_URL) # 주소

            EBEST_downloadFile(ARTICLE_URL)
            send(ARTICLE_BOARD_NAME = ARTICLE_BOARD_NAME , ARTICLE_TITLE = ARTICLE_TITLE , ARTICLE_URL = ARTICLE_URL) # 파일의 경우 전역변수로 처리 (downloadFile 함수)
            nNewFeedCnt -= 1
            print('nNewFeedCnt', nNewFeedCnt)
            if nNewFeedCnt == 0 : 
                print('새로운 게시글 모두 전송 완료')
                nNxtIdx[ARTICLE_BOARD_ORDER] = ntotalIdx

                print('ARTICLE_BOARD_ORDER',ARTICLE_BOARD_ORDER)
                print('ARTICLE_BOARD_ORDER',nNxtIdx[ARTICLE_BOARD_ORDER])
                return



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
    with open(ATTACH_FILE_NAME, "wb") as file:   # open in binary mode
        response = get(ATTACH_URL, verify=False)               # get request
        file.write(response.content)      # write to file
    
    time.sleep(5) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)

def send1(): # 기존 함수
    sendMessageText = ''
    #생성한 텔레그램 봇 정보 assign (@ebest_noti_bot)
    my_token_key = '1372612160:AAHVyndGDmb1N2yEgvlZ_DmUgShqk2F0d4w'
    bot = telegram.Bot(token = my_token_key)

    #생성한 텔레그램 봇 정보 출력
    #me = bot.getMe()
    #print('텔레그램 채널 정보 : ',me)

    #생성한 텔레그램 봇 /start 시작 후 사용자 id 받아 오기
    #chat_id = bot.getUpdates()[-1].message.chat.id

    #chat_id = '-1001431056975' # 이베스트 게시물 알림 채널
    chat_id = '-1001474652718' # 테스트 채널

    bot.sendMessage(chat_id = chat_id, text = sendMessageText)
    time.sleep(1) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)
    bot.sendDocument(chat_id = chat_id, document = open(ATTACH_FILE_NAME, 'rb') )
    os.remove(ATTACH_FILE_NAME) # 파일 전송 후 PDF 삭제
    time.sleep(8) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)


def send(ARTICLE_BOARD_NAME , ARTICLE_TITLE , ARTICLE_URL): # 파일의 경우 전역변수로 처리 (downloadFile 함수)
    print('send()')
    if SEC_FIRM_ORDER == 0:
        FIRM_NAME = "이베스트 투자증권"
    elif SEC_FIRM_ORDER == 1:
        FIRM_NAME = "흥국증권"
    elif SEC_FIRM_ORDER == 2:
        FIRM_NAME = "상상인증권"
    else:
        FIRM_NAME = ''

    if FIRM_NAME != '': FIRM_NAME += " - "
        

    # 실제 전송할 메시지 작성
    sendMessageText = ''
    sendMessageText += EMOJI_FIRE + FIRM_NAME + ARTICLE_BOARD_NAME + EMOJI_FIRE + "\n"
    sendMessageText += ARTICLE_TITLE + "\n"
    sendMessageText += EMOJI_PICK + ARTICLE_URL 

    #생성한 텔레그램 봇 정보 assign (@ebest_noti_bot)
    my_token_key = '1372612160:AAHVyndGDmb1N2yEgvlZ_DmUgShqk2F0d4w'
    bot = telegram.Bot(token = my_token_key)

    #생성한 텔레그램 봇 정보 출력
    #me = bot.getMe()
    #print('텔레그램 채널 정보 : ',me)

    #생성한 텔레그램 봇 /start 시작 후 사용자 id 받아 오기
    #chat_id = bot.getUpdates()[-1].message.chat.id

    # 사용자에게 직접 보내지 않고, 채널에 초대하여 채널에 메시지 보내기 방식으로 변경
    chat_id = '-1001431056975' # 이베스트 게시물 알림 채널
    #chat_id = '-1001474652718' # 테스트 채널

    bot.sendMessage(chat_id = chat_id, text = sendMessageText, disable_web_page_preview=True)
    time.sleep(1) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)
    bot.sendDocument(chat_id = chat_id, document = open(ATTACH_FILE_NAME, 'rb') )
    os.remove(ATTACH_FILE_NAME) # 파일 전송 후 PDF 삭제
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
    global nNxtIdx
    global nNewFeedCnt
    global NXT_KEY

    webpage = requests.get(TARGET_URL, verify=False)

    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")

    print('###첫실행구간###')
    soupList = soup.select('#content > table > tbody > tr > td.left > a')

    ARTICLE_BOARD_NAME = HEUNGKUK_BOARD_NAME[ARTICLE_BOARD_ORDER]
    ARTICLE_TITLE = soupList[0].text
    ARTICLE_URL = 'http://www.heungkuksec.co.kr/research/industry/view.do?' + soupList[0]['onclick'].replace("nav.go('view', '", "").replace("');", "").strip()
    
    # 연속키 저장 테스트 -> 테스트 후 연속키 지정 구간으로 변경
    KEY_DIR_FILE_NAME = './key/'+ str(SEC_FIRM_ORDER) + '-' + str(ARTICLE_BOARD_ORDER) + '.key' # => 파일형식 예시 : 1-0.key (앞자리: 증권사 순서, 뒷자리:게시판 순서)
    
    # 존재 여부 확인 후 연속키 파일 생성
    if not( os.path.isfile( KEY_DIR_FILE_NAME ) ): # 최초 실행 이거나 연속키 초기화
        # 연속키가 없는 경우 
        print('처음 조회된 게시판으로 게시물을 보내지 않습니다.')
        return Set_nxtKey(KEY_DIR_FILE_NAME, ARTICLE_URL)
    else:   # 이미 실행
        NXT_KEY = Get_nxtKey(KEY_DIR_FILE_NAME, NXT_KEY)

    print('게시판 이름:', ARTICLE_BOARD_NAME) # 게시판 종류
    print('게시글 제목:', ARTICLE_TITLE) # 게시글 제목
    print('게시글URL:', ARTICLE_URL) # 주소
    print('연속URL:', NXT_KEY) # 주소
    print('############')

    for list in soupList:
        LIST_ARTICLE_URL = 'http://www.heungkuksec.co.kr/research/industry/view.do?'+list['onclick'].replace("nav.go('view', '", "").replace("');", "").strip()
        ARTICLE_URL = 'http://www.heungkuksec.co.kr/research/industry/view.do?' + list[0]['onclick'].replace("nav.go('view', '", "").replace("');", "").strip()
        if NXT_KEY != LIST_ARTICLE_URL or NXT_KEY == '': #  
            HeungKuk_downloadFile(LIST_ARTICLE_URL)
            send(ARTICLE_BOARD_NAME = ARTICLE_BOARD_NAME, ARTICLE_TITLE = ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)        
            print('메세지 전송 URL:', LIST_ARTICLE_URL)
        else:
            print('새로운 게시물을 모두 발송하였습니다.')
            NXT_KEY = 'http://www.heungkuksec.co.kr/research/industry/view.do?' + soupList[0]['onclick'].replace("nav.go('view', '", "").replace("');", "").strip()
            Set_nxtKey(KEY_DIR_FILE_NAME, NXT_KEY)
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

    with open(ATTACH_FILE_NAME, "wb") as file:   # open in binary mode
        response = get(ATTACH_URL, verify=False)               # get request
        file.write(response.content)      # write to file
    
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
    global nNxtIdx
    global nNewFeedCnt
    global NXT_KEY

    webpage = requests.get(TARGET_URL, verify=False)

    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")

    print('###첫실행구간###')
    soupList = soup.select('#contents > div > div.bbs_a_type > table > tbody > tr > td.con > a')
    
    print(soupList)
    ARTICLE_BOARD_NAME = SANGSANGIN_BOARD_NAME[ARTICLE_BOARD_ORDER]
    ARTICLE_TITLE = soupList[0].text
    ARTICLE_URL = 'http://www.sangsanginib.com' + soupList[0]['href'] #.replace("nav.go('view', '", "").replace("');", "").strip()
    
    print(ARTICLE_URL)
    # 연속키 저장 테스트 -> 테스트 후 연속키 지정 구간으로 변경
    KEY_DIR_FILE_NAME = './key/'+ str(SEC_FIRM_ORDER) + '-' + str(ARTICLE_BOARD_ORDER) + '.key' # => 파일형식 예시 : 1-0.key (앞자리: 증권사 순서, 뒷자리:게시판 순서)
    
    # 존재 여부 확인 후 연속키 파일 생성
    if not( os.path.isfile( KEY_DIR_FILE_NAME ) ): # 최초 실행 이거나 연속키 초기화
        # 연속키가 없는 경우 
        print('처음 조회된 게시판으로 게시물을 보내지 않습니다.')
        return Set_nxtKey(KEY_DIR_FILE_NAME, ARTICLE_URL)
    else:   # 이미 실행
        NXT_KEY = Get_nxtKey(KEY_DIR_FILE_NAME, NXT_KEY)

    #print('게시판 이름:', ARTICLE_BOARD_NAME) # 게시판 종류
    #print('게시글 제목:', ARTICLE_TITLE) # 게시글 제목
    #print('게시글URL:', ARTICLE_URL) # 주소
    #print('연속URL:', NXT_KEY) # 주소
    print('############')

    for list in soupList:
        LIST_ARTICLE_URL = 'http://www.sangsanginib.com' +list['href']#.replace("nav.go('view', '", "").replace("');", "").strip()
        LIST_ARTICLE_TITLE = list.text

        if NXT_KEY != LIST_ARTICLE_URL or NXT_KEY == '': #  
            SangSangIn_downloadFile(LIST_ARTICLE_URL)
            send(ARTICLE_BOARD_NAME = ARTICLE_BOARD_NAME, ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)        
            print('메세지 전송 URL:', LIST_ARTICLE_URL)
        else:
            print('새로운 게시물을 모두 발송하였습니다.')
            NXT_KEY = 'http://www.heungkuksec.co.kr/research/industry/view.do?' + soupList[0]['onclick'].replace("nav.go('view', '", "").replace("');", "").strip()
            Set_nxtKey(KEY_DIR_FILE_NAME, NXT_KEY)
            return True

def SangSangIn_downloadFile(ARTICLE_URL):
    global ATTACH_FILE_NAME

    webpage = requests.get(ARTICLE_URL, verify=False)    
    
    # 첨부파일 URL
    attachFileCode = BeautifulSoup(webpage.content, "html.parser").select_one('#contents > div > div.bbs_a_view > dl.b_bottom > dd > em:nth-child(1) > a')['href']
    ATTACH_URL = 'http://www.sangsanginib.com' + attachFileCode
    print('첨부파일 URL : ',ATTACH_URL)
    # 첨부파일 이름
    ATTACH_FILE_NAME = BeautifulSoup(webpage.content, "html.parser").select_one('#contents > div > div.bbs_a_view > dl.b_bottom > dd > em:nth-child(1)').text.strip()
    print('첨부파일이름 : ',ATTACH_FILE_NAME)

    with open(ATTACH_FILE_NAME, "wb") as file:   # open in binary mode
        response = get(ATTACH_URL, verify=False)               # get request
        file.write(response.content)      # write to file
    
    time.sleep(5) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)

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

# 액션 플랜 
# 1. 10분 간격으로 게시글을 읽어옵니다.
# 2. 게시글이 마지막 게시글이 이전 게시글과 다른 경우(새로운 게시글이 올라온 경우) 
    # 메세지로 게시글 정보르 보냅니다
    # 아닌 경우 다시 1번을 반복합니다.
def main():
    global SEC_FIRM_ORDER  # 증권사 순번
    print('########Program Start Run########')
    print('key폴더가 존재하지 않는 경우 무조건 생성합니다.')
    os.makedirs('./key', exist_ok=True)

    # SEC_FIRM_ORDER는 임시코드 추후 로직 추가 예정 
    while True:
        SEC_FIRM_ORDER = 0 
        print("EBEST_checkNewArticle() => 새 게시글 정보 확인")
        EBEST_checkNewArticle()
        
        SEC_FIRM_ORDER = 1
        print("HeungKuk_checkNewArticle() => 새 게시글 정보 확인")
        HeungKuk_checkNewArticle()        

        SEC_FIRM_ORDER = 2
        print("SangSangIn_checkNewArticle() => 새 게시글 정보 확인")
        SangSangIn_checkNewArticle()        

        print('######',REFRESH_TIME,'초 후 게시글을 재 확인 합니다.######')        
        time.sleep(REFRESH_TIME)

if __name__ == "__main__":
	main()