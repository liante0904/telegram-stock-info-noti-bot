# -*- coding:utf-8 -*- 
import os
import gc
import requests
from datetime import datetime

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.WebScraper import SyncWebScraper


def Hmsec_checkNewArticle():
    SEC_FIRM_ORDER      = 9
    ARTICLE_BOARD_ORDER = 0
    json_data_list = []

    requests.packages.urllib3.disable_warnings()

    # 현대차증권 투자전략
    TARGET_URL_0 =  'https://www.hmsec.com/research/research_list_ajax.do?Menu_category=1'
    
    # 현대차증권 Report & Note 
    TARGET_URL_1 =  'https://www.hmsec.com/research/research_list_ajax.do?Menu_category=2'
    
    # 현대차증권 해외주식
    TARGET_URL_2 =  'https://www.hmsec.com/research/research_list_ajax.do?Menu_category=8'
    
    
    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1, TARGET_URL_2)
    
    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        firm_info = FirmInfo(
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER
        )
        payload = {"curPage":1}

        scraper = SyncWebScraper(TARGET_URL, firm_info)
        
        # HTML parse
        jres = scraper.PostJson(params=payload)
        
        
        # REG_DATE = jres['data_list'][0]['REG_DATE'].strip()
        # FILE_NAME = jres['data_list'][0]['UPLOAD_FILE1'].strip()
        # print('REG_DATE:',REG_DATE)
        # print('FILE_NAME:',FILE_NAME)

        # print(jres)
        soupList = jres['data_list']
        
        # JSON To List
        for list in soupList:
            # print(list)
            # https://www.hmsec.com/documents/research/20230103075940673_ko.pdf
            DOWNLOAD_URL = 'https://www.hmsec.com/documents/research/{}' 
            DOWNLOAD_URL = DOWNLOAD_URL.format(list['UPLOAD_FILE1'])

            # https://docs.hmsec.com/SynapDocViewServer/job?fid=#&sync=true&fileType=URL&filePath=#
            LIST_ARTICLE_URL = 'https://docs.hmsec.com/SynapDocViewServer/job?fid={}&sync=true&fileType=URL&filePath={}' 
            LIST_ARTICLE_URL = LIST_ARTICLE_URL.format(DOWNLOAD_URL, DOWNLOAD_URL)

            LIST_ARTICLE_TITLE = list['SUBJECT']

            REG_DT = list['REG_DATE'].strip()
            list['NAME'] = (list.get('NAME') or '').strip()
            WRITER = list['NAME'].strip()
            # print(jres['data_list'])
            # SERIAL_NO = jres['data_list'][0]['SERIAL_NO']

            # LIST_ARTICLE_URL = DownloadFile(URL = LIST_ATTACHMENT_URL, FILE_NAME = LIST_ARTICLE_TITLE +'.pdf')
            # ATTACH_FILE_NAME = DownloadFile(URL = LIST_ATTACHMENT_URL, FILE_NAME = LIST_ARTICLE_TITLE +'.pdf')

            json_data_list.append({
                "SEC_FIRM_ORDER":SEC_FIRM_ORDER,
                "ARTICLE_BOARD_ORDER":ARTICLE_BOARD_ORDER,
                "FIRM_NM":firm_info.get_firm_name(),
                "ARTICLE_TITLE":LIST_ARTICLE_TITLE,
                "REG_DT":REG_DT,
                "ATTACH_URL":LIST_ARTICLE_URL,
                "ARTICLE_URL":LIST_ARTICLE_URL,
                "DOWNLOAD_URL": DOWNLOAD_URL,
                "TELEGRAM_URL": LIST_ARTICLE_URL,
                "KEY": LIST_ARTICLE_URL,
                "WRITER": WRITER,
                "SAVE_TIME": datetime.now().isoformat()
            })
            

    # 메모리 정리
    del soupList
    gc.collect()
    # print(json_data_list)
    return json_data_list


# # 비동기 함수 실행
# async def main():
#     result = await Sangsanginib_checkNewArticle()
#     print(result)

def main():
    result = Hmsec_checkNewArticle()
    print(result)
    
if __name__ == '__main__':
    main()
    # asyncio.run(main())