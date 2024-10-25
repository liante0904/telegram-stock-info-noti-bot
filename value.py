import requests

# 이벤트별 벨류에이션 값
valuation_targets = {
    "2008년": 0.89,
    "2015~16년": 0.93,
    "2020년 3월": 0.67,
    "24/8월": 0.88
}

# 현재 코스피 PBR 값을 가져오는 함수 (가정: Naver Finance API 사용)
def get_kospi_pbr():
    url = "https://api.example.com/get_kospi_pbr"  # 실제 API 엔드포인트로 교체
    response = requests.get(url)
    data = response.json()
    return data["pbr"]

# 메시지를 발송하는 함수 (가정: 이메일 발송 서비스 사용)
def send_message(message):
    # 여기에 메시지 발송 로직을 추가합니다.
    # 예: 이메일, SMS, Slack, 등
    print(f"메시지 발송: {message}")

# 코스피 PBR이 특정 벨류에이션에 근접하는지 확인
def check_valuation_and_notify():
    print(valuation_targets)
    current_pbr = 0.89
    for event, target_valuation in valuation_targets.items():
        # 벨류에이션 근접 기준 (여기서는 ±0.05로 설정)
        if abs(current_pbr - target_valuation) <= 0.05:
            message = f"코스피 PBR이 {event}의 저점 벨류에이션({target_valuation}배)에 근접했습니다."
            print(message)

# 메인 실행 부분
if __name__ == "__main__":
    check_valuation_and_notify()
