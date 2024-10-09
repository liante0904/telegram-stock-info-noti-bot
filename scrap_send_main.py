from package.json_to_sqlite import daily_select_data, daily_update_data
from utils.sqlite_util import convert_sql_to_telegram_messages
from utils.telegram_util import sendMarkDownText
from utils.file_util import download_file_wget
from utils.telegram_util import sendMarkDownText
from models.SecretKey import SecretKey

SECRET_KEY = SecretKey()
token = SECRET_KEY.TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET

async def daily_report(report_type):
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
    """
    if report_type == 'send':
        rows = daily_select_data(type=report_type)
        if rows:
            formatted_messages = convert_sql_to_telegram_messages(rows)
            print('=' * 30)

            # 메시지 발송
            for sendMessageText in formatted_messages:
                print(f"메시지 발송 중: {sendMessageText}")
                await sendMarkDownText(token=token,
                        chat_id=SECRET_KEY.TELEGRAM_CHANNEL_ID_REPORT_ALARM,
                        sendMessageText=sendMessageText)
            # 데이터 업데이트
            r = daily_update_data(fetched_rows=rows, type=report_type)
            if r: 
                print('성공')

    elif report_type == 'download':
        rows = daily_select_data(type='download')
        # print(rows)

        # 파일 다운로드 처리
        if rows:
            print('*'*30)
            for row in rows:
                # 파일 다운로드 시 성공 여부 반환 (성공 시 True, 실패 시 False)
                download_success = download_file_wget(report_info_row=row)
                
                if download_success:
                    # 파일이 정상적으로 다운로드되었거나 이미 존재하는 경우
                    # update_download_status_in_db(row)  # DB에 다운로드 완료 상태로 업데이트
                    r = daily_update_data(fetched_rows=row, type='download')
                else:
                    print(f"파일 다운로드 실패: {row['file_name']}")  # 실패한 파일 로그 출력


def main():
    # 발송될 내역
    daily_report(report_type='send')
    daily_report(report_type='download')
if __name__ == "__main__":
    main()