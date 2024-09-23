from package.json_to_sqlite import daily_select_data
from package.sqlite_util import convert_sql_to_telegram_messages

def main():
    rows = daily_select_data()
    formatted_messages = convert_sql_to_telegram_messages(rows)
    print('='*30)

    for message in formatted_messages:
        print(message)  # 텔레그램 발송 함수
    

if __name__ == "__main__":
    main()