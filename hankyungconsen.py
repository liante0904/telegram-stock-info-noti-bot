import requests
import asyncio
from bs4 import BeautifulSoup

from utils.json_util import save_data_to_local_json, get_unsent_main_ch_data_to_local_json, update_main_ch_send_yn_to_y # import the function from json_util
from utils.telegram_util import sendMarkDownText
from models.SecretKey import SecretKey

SECRET_KEY = SecretKey()
token = SECRET_KEY.TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET
# -*- coding:utf-8 -*- 

JSON_FILE_NAME = './json/hankyungconsen_research.json'

async def HankyungConsen_checkNewArticle():
    SEC_FIRM_ORDER = 100
    ARTICLE_BOARD_ORDER = 0
    
    requests.packages.urllib3.disable_warnings()

    # 한경 컨센서스
    TARGET_URL = 'https://consensus.hankyung.com/analysis/list?search_date=today&search_text=&pagenum=1000'

    sendMessageText = ''
    
    try:
        # 웹 페이지 가져오기
        webpage = requests.get(TARGET_URL, verify=False, headers={
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'
        })
        
        # HTML 파싱
        soup = BeautifulSoup(webpage.content, "html.parser")
        soupList = soup.select('#contents > div.table_style01 > table > tbody > tr')

        print('############')

        brokerName = soup.select('#contents > div.table_style01 > table > tbody > tr.first > td:nth-child(5)')[0].text
        first_article_processed = False
        
        for list in soupList:
            LIST_ARTICLE_CLASS = list.select_one('#contents > div.table_style01 > table > tbody > tr > td:nth-child(2)').text
            LIST_ARTICLE_TITLE = list.select_one('#contents > div.table_style01 > table > tbody > tr > td.text_l > a').text
            LIST_ARTICLE_URL = 'https://consensus.hankyung.com' + list.select_one('#contents > div.table_style01 > table > tbody > tr > td:nth-child(6) > div > a').attrs['href']
            LIST_ARTICLE_BROKER_NAME = list.select_one('#contents > div.table_style01 > table > tbody > tr > td:nth-child(5)').text

            # JSON 파일에 데이터 저장
            new_article_message = save_data_to_local_json(
                filename=JSON_FILE_NAME,
                sec_firm_order=SEC_FIRM_ORDER,
                article_board_order=ARTICLE_BOARD_ORDER,
                firm_nm=LIST_ARTICLE_BROKER_NAME,
                attach_url=LIST_ARTICLE_URL,
                article_title=LIST_ARTICLE_TITLE
            )

            if new_article_message:
                print(LIST_ARTICLE_CLASS)
                print(LIST_ARTICLE_TITLE)
                print(LIST_ARTICLE_URL)
                print('LIST_ARTICLE_BROKER_NAME=', LIST_ARTICLE_BROKER_NAME)

                if not first_article_processed or brokerName != LIST_ARTICLE_BROKER_NAME:
                    sendMessageText += "\n\n" + "●" + LIST_ARTICLE_BROKER_NAME + "\n"
                    brokerName = LIST_ARTICLE_BROKER_NAME  # 회사명 키 변경
                    first_article_processed = True

                sendMessageText += new_article_message

            if len(sendMessageText) >= 3000:
                print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다.")
                print(sendMessageText)
                await sendMarkDownText(token=token,
                chat_id=SECRET_KEY.TELEGRAM_CHANNEL_ID_HANKYUNG_CONSEN,
                sendMessageText=sendMessageText)
                sendMessageText = ''
            else:
                print('최신 게시글이 채널에 발송 되어 있습니다.')

    except Exception as e:
        print(f"오류 발생: {e}")
        if len(sendMessageText) > 3500:
            print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다.\n", sendMessageText)
            await sendMarkDownText(token=token,
            chat_id=SECRET_KEY.TELEGRAM_CHANNEL_ID_HANKYUNG_CONSEN,
            sendMessageText=sendMessageText)
            sendMessageText = ''

    if sendMessageText:
        print(sendMessageText)
        await sendMarkDownText(token=token,
        chat_id=SECRET_KEY.TELEGRAM_CHANNEL_ID_HANKYUNG_CONSEN,
        sendMessageText=sendMessageText)
    else:
        print('최신 게시글이 채널에 발송 되어 있습니다.')

    return sendMessageText

async def main():
    sendMessageText = ''

    print("HankyungConsen_checkNewArticle()=> 새 게시글 정보 확인") # 12
    await HankyungConsen_checkNewArticle()

    lists = get_unsent_main_ch_data_to_local_json(JSON_FILE_NAME)
    if lists:
        for sendMessageText in lists:
            await sendMarkDownText(token=token,
            chat_id=SECRET_KEY.TELEGRAM_CHANNEL_ID_REPORT_ALARM,
            sendMessageText=sendMessageText)
        update_main_ch_send_yn_to_y(JSON_FILE_NAME)

if __name__ == "__main__":
	asyncio.run(main())