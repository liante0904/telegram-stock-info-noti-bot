from package.json_to_sqlite import daily_select_data, daily_update_data
from package.sqlite_util import convert_sql_to_telegram_messages

def main():
    rows = daily_select_data(type='send')
    formatted_messages = convert_sql_to_telegram_messages(rows)
    print('='*30)

    # TODO SEND
    for message in formatted_messages:
        print(message)  # 텔레그램 발송 함수
    
    # TOTO UPDATE
    r = daily_update_data(rows)
    
    if r: print('성공')
    
    
    rows = daily_select_data(type='download')
    

if __name__ == "__main__":
    main()