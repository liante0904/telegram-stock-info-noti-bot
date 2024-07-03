import requests

def search_stock(query):
    url = 'https://ac.stock.naver.com/ac'
    params = {
        'q': query,
        'target': 'index,stock,marketindicator'
    }

    response = requests.get(url, params=params)
    data = response.json()

    # 필터링된 결과를 저장할 리스트
    filtered_items = [
        {
            'name': item['name'],
            'code': item['code']
        }
        for item in data['items']
        if item['typeCode'] in ['KOSPI', 'KOSDAQ']
    ]

    return filtered_items

def display_results(results):
    print("검색 결과:")
    for idx, result in enumerate(results, start=1):
        print(f"{idx}. 종목명: {result['name']}, 종목코드: {result['code']}")

def select_stock(results):
    if len(results) == 1:
        return results[0]

    user_input = input("선택할 종목을 입력하세요 (순번, 종목명, 6자리 숫자 종목코드): ")
    
    if user_input.isdigit() and 1 <= int(user_input) <= len(results):
        return results[int(user_input)-1]
    
    for result in results:
        if user_input == result['name'] or user_input == result['code']:
            return result
    
    print("잘못된 입력입니다. 다시 시도하세요.")
    return select_stock(results)

def main():
    user_input = input("종목정보를 입력하세요 (종목명, 종목코드): ")
    results = search_stock(user_input)

    if results:
        display_results(results)
        selected_stock = select_stock(results)
        print(f"선택한 종목 - 종목명: {selected_stock['name']}, 종목코드: {selected_stock['code']}")
    else:
        print("검색 결과가 없습니다.")

if __name__ == "__main__":
    stock_name = input("종목 이름을 입력하세요: ")
    stock_code = input("종목 코드를 입력하세요: ")
    print(f"{stock_name}의 종목 코드는 {stock_code}입니다.")

    # chart.py를 실행하여 차트 그리기
    import subprocess
    subprocess.run(["python", "chart.py", stock_code, stock_name])
