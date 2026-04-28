from loguru import logger
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
from models.ConfigManager import config


def Hmsec_checkNewArticle():
    sec_firm_order      = 9
    article_board_order = 0
    json_data_list = []

    requests.packages.urllib3.disable_warnings()

    TARGET_URL_TUPLE = config.get_urls("Hmsec_9")
    if not TARGET_URL_TUPLE:
        logger.warning("No URLs found for Hmsec_9")
        return []

    # URL GET
    soupList = None
    for article_board_order, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        firm_info = FirmInfo(
            sec_firm_order=sec_firm_order,
            article_board_order=article_board_order
        )
        payload = {"curPage":1}

        scraper = SyncWebScraper(TARGET_URL, firm_info)

        # HTML parse
        jres = scraper.PostJson(params=payload)


        # REG_DATE = jres['data_list'][0]['REG_DATE'].strip()
        # FILE_NAME = jres['data_list'][0]['UPLOAD_FILE1'].strip()
        # logger.debug('REG_DATE:',REG_DATE)
        # logger.debug('FILE_NAME:',FILE_NAME)

        # logger.debug(jres)
        soupList = jres.get('data_list', [])

        # JSON To List
        for list in soupList:
            # logger.debug(list)
            # https://www.hmsec.com/documents/research/20230103075940673_ko.pdf
            download_url = 'https://www.hmsec.com/documents/research/{}'
            download_url = download_url.format(list['UPLOAD_FILE1'])

            # https://docs.hmsec.com/SynapDocViewServer/job?fid=#&sync=true&fileType=URL&filePath=#
            LIST_ARTICLE_URL = 'https://docs.hmsec.com/SynapDocViewServer/job?fid={}&sync=true&fileType=URL&filePath={}'
            LIST_ARTICLE_URL = LIST_ARTICLE_URL.format(download_url, download_url)

            LIST_ARTICLE_TITLE = list['SUBJECT']

            reg_dt = list['REG_DATE'].strip()
            list['NAME'] = (list.get('NAME') or '').strip()
            writer = list['NAME'].strip()
            # logger.debug(jres['data_list'])
            # SERIAL_NO = jres['data_list'][0]['SERIAL_NO']

            # LIST_ARTICLE_URL = DownloadFile(URL = LIST_ATTACHMENT_URL, FILE_NAME = LIST_ARTICLE_TITLE +'.pdf')
            # ATTACH_FILE_NAME = DownloadFile(URL = LIST_ATTACHMENT_URL, FILE_NAME = LIST_ARTICLE_TITLE +'.pdf')

            json_data_list.append({
                "sec_firm_order":sec_firm_order,
                "article_board_order":article_board_order,
                "firm_nm":firm_info.get_firm_name(),
                "article_title":LIST_ARTICLE_TITLE,
                "reg_dt":reg_dt,
                "article_url":LIST_ARTICLE_URL,
                "pdf_url": download_url,
                "download_url": download_url,
                "telegram_url": LIST_ARTICLE_URL,
                "key": LIST_ARTICLE_URL,
                "writer": writer,
                "save_time": datetime.now().isoformat()
            })


    # 메모리 정리
    if soupList is not None:
        del soupList
    gc.collect()    # logger.debug(json_data_list)
    return json_data_list


# # 비동기 함수 실행
# async def main():
#     result = await Sangsanginib_checkNewArticle()
# logger.debug(result)

def main():
    result = Hmsec_checkNewArticle()
    logger.debug(result)
    
if __name__ == '__main__':
    main()
    # asyncio.run(main())
