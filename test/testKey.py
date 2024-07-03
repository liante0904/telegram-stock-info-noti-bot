from package.SecretKey import SecretKey

# SecretKey 클래스의 인스턴스를 전역 변수로 선언
SECRET_KEY = SecretKey()

def main():
    global SECRET_KEY
    SECRET_KEY.load_secrets()
    
    # main 함수 내에서 비밀 키 사용
    print(SECRET_KEY.TELEGRAM_BOT_INFO)
    # 애플리케이션 로직 작성

if __name__ == "__main__":
    main()

# main 함수 외부에서도 secret_key 사용 가능
def another_function():
    global SECRET_KEY
    print(SECRET_KEY.TELEGRAM_CHANNEL_ID_REPORT_ALARM)
    # 추가 로직 작성

# 다른 함수나 모듈에서도 필요할 때 secret_key 사용
