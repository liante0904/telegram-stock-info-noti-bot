import os
import asyncio
import argparse
import telegram.error
from utils.sqlite_util import convert_sql_to_telegram_messages
from utils.telegram_util import sendMarkDownText
from utils.file_util import download_file_wget
from models.SQLiteManager import SQLiteManager
from dotenv import load_dotenv

load_dotenv()

token = os.getenv('TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET')
chat_id = os.getenv('TELEGRAM_CHANNEL_ID_REPORT_ALARM')


def format_date(date_str):
    """
    날짜 형식을 변환하는 함수입니다.
    
    입력이 'YYYYMMDD' 형식일 경우 'YYYY-MM-DD'로 변환하고,
    이미 'YYYY-MM-DD' 형식인 경우는 그대로 반환합니다.

    매개변수:
    ----------
    date_str : str
        변환할 날짜 문자열입니다.
    
    반환값:
    -------
    str
        변환된 날짜 문자열입니다.
    """
    if len(date_str) == 8 and date_str.isdigit():  # 20241012 형태인지 확인
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    return date_str  # 이미 'YYYY-MM-DD'인 경우 그대로 반환

async def daily_report(report_type, date_str=None):
    """
    매일 보고서를 처리하는 함수입니다.
    
    이 함수는 두 가지 타입의 작업을 지원합니다:
    
    - 'send': 
        텔레그램 메시지를 전송합니다. 데이터베이스에서 데이터를 선택하고 
        형식화하여 메시지를 생성한 후, 각 메시지를 전송합니다. 
        이후 데이터베이스의 데이터를 업데이트합니다.

    - 'download': 
        다운로드 작업을 수행합니다. 데이터베이스에서 다운로드할 데이터를 선택하고, 
        선택된 데이터에 대한 처리를 진행합니다. 
        이후 데이터베이스의 데이터를 업데이트합니다.

    매개변수:
    ----------
    report_type : str
        'send' 또는 'download' 중 하나를 지정합니다.
    date_str : str, optional
        처리할 날짜 (형식: YYYY-MM-DD). 기본값은 None입니다.
    """
    db = SQLiteManager()
    if report_type == 'send':
        rows = await db.daily_select_data(date_str=date_str, type=report_type)
        if rows:
            formatted_messages = await convert_sql_to_telegram_messages(rows)
            print('=' * 30)

            # 메시지 발송
            send_success = True  # 모든 메시지가 성공했는지 여부를 추적
            for sendMessageText in formatted_messages:
                try:
                    print(f"메시지 발송 중: {sendMessageText}")
                    await sendMarkDownText(token=token,
                                           chat_id=chat_id,
                                           sendMessageText=sendMessageText)
                except telegram.error.TelegramError as e:
                    print(f"텔레그램 API 오류로 메시지 발송 실패: {sendMessageText}, 오류: {e}")
                    send_success = False  # 실패한 경우, 성공 플래그를 False로 설정
                except Exception as e:
                    print(f"예상치 못한 오류 발생: {sendMessageText}, 오류: {e}")
                    send_success = False # 예상치 못한 오류도 실패로 처리

            # 모든 메시지가 성공적으로 전송된 경우에만 데이터 업데이트
            if send_success:
                r = await db.daily_update_data(date_str=date_str, fetched_rows=rows, type=report_type)
                if r:
                    print('DB 업데이트 성공')
            else:
                print('일부 메시지 발송 실패, DB 업데이트 생략')

    elif report_type == 'download':
        rows = await db.daily_select_data(date_str=date_str, type='download')
        # print(rows)

        # 파일 다운로드 처리
        if rows:
            print('*' * 30)
            for row in rows:
                # 파일 다운로드 시 성공 여부 반환 (성공 시 True, 실패 시 False)
                download_success = await download_file_wget(report_info_row=row)
                
                if download_success:
                    # 파일이 정상적으로 다운로드되었거나 이미 존재하는 경우
                    r = await db.daily_update_data(date_str=date_str, fetched_rows=row, type='download')
                else:
                    print(f"파일 다운로드 실패: {row.get('file_name', '')}")  # 실패한 파일 로그 출력
                    continue


async def main(date_str=None):
    # date_str = format_date(date_str)  # 날짜 형식 변환
    print('===================scrap_send_main===============')
    # 발송될 내역
    await daily_report(report_type='send', date_str=date_str)
    # await daily_report(report_type='download', date_str=date_str)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Daily report script.')
    parser.add_argument('date', type=str, nargs='?', default=None, help='Date in YYYY-MM-DD format.')

    args = parser.parse_args()
    asyncio.run(main(date_str=args.date))
