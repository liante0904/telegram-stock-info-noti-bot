from pykrx import stock

def get_stock_codes_by_name_or_code(input_value):
    # KRX에서 제공하는 모든 상장 종목 리스트를 가져옵니다.
    tickers = stock.get_market_ticker_list()
    
    for ticker in tickers: 
        name = stock.get_market_ticker_name(ticker)
        print(f'종목명:{name} 종목코드:{ticker}')
    
    # 입력값이 6자리 숫자인 경우 종목코드로 검색
    if input_value.isdigit() and len(input_value) == 6:
        return [(stock.get_market_ticker_name(input_value), input_value)]

    # 종목명 부분 일치를 검사하여 해당하는 종목과 종목코드를 저장
    matching_stocks = []
    for ticker in tickers:
        name = stock.get_market_ticker_name(ticker)
        if input_value in name:
            matching_stocks.append((name, ticker))
    return matching_stocks

def get_stock_info():
    # 사용자로부터 종목명 부분 또는 종목코드를 입력받습니다.
    input_value = input("종목명 또는 종목코드의 일부를 입력하세요: ")

    # 일치하는 종목을 검색합니다.
    matching_stocks = get_stock_codes_by_name_or_code(input_value)

    if matching_stocks:
        if len(matching_stocks) == 1:
            # 일치하는 종목이 하나인 경우 바로 반환
            chosen_name, chosen_code = matching_stocks[0]
            print(f"선택한 종목명: {chosen_name}, 종목코드: {chosen_code}")
            return chosen_code, chosen_name
        else:
            # 일치하는 종목이 여러 개인 경우 리스트 출력
            print(f"'{input_value}'이(가) 포함된 종목명 리스트:")
            for i, (name, code) in enumerate(matching_stocks, start=1):
                print(f"{i}. 종목명: {name}, 종목코드: {code}")
            
            # 사용자로부터 선택할 종목을 입력받습니다.
            choice = input("\n원하는 종목을 선택하세요 (번호, 종목명 또는 종목코드): ")

            # 입력된 값이 번호인지 확인하고, 번호라면 인덱스로 변환
            if choice.isdigit() and len(choice) < 6:
                choice = int(choice) - 1
                if 0 <= choice < len(matching_stocks):
                    chosen_name, chosen_code = matching_stocks[choice]
                    print(f"선택한 종목명: {chosen_name}, 종목코드: {chosen_code}")
                    return chosen_code, chosen_name
                else:
                    print("잘못된 번호를 입력하셨습니다.")
            else:
                # 입력된 값이 종목명 또는 종목코드인지 확인하고, 해당하는 종목 찾기
                for name, code in matching_stocks:
                    if choice == name or choice == code:
                        print(f"선택한 종목명: {name}, 종목코드: {code}")
                        return code, name
                print("입력한 종목명을 찾을 수 없습니다.")
    else:
        print(f"'{input_value}'이(가) 포함된 종목명을 찾을 수 없습니다.")
        return None, None
