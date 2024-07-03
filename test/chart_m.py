import matplotlib.pyplot as plt
from pykrx import stock
from datetime import datetime, timedelta
import pandas as pd
from isu_no import get_stock_info

# 사용자로부터 종목명을 입력받습니다.
stock_code, stock_name = get_stock_info()

if stock_code is None:
    print(f"{stock_name}에 해당하는 종목코드를 찾을 수 없습니다.")
else:
    # 현재 시스템 일자
    now = datetime.now()

    # end_date 설정 (오후 6시 이전이면 어제 날짜, 이후면 오늘 날짜)
    if now.hour < 18:
        end_date = (now - timedelta(days=1)).strftime('%Y-%m-%d')
    else:
        end_date = now.strftime('%Y-%m-%d')

    # start_date 설정 (end_date로부터 120일 이전)
    start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=120)).strftime('%Y-%m-%d')

    try:
        # 외국인과 기관의 순매수 대금 데이터 가져오기
        trading_value = stock.get_market_trading_value_by_date(start_date, end_date, stock_code)

        # 데이터프레임 구조 확인
        print("Trading Value Data:")
        print(trading_value.head())

        # 5일 단위로 합산
        trading_value['외국인_순매수_5일합'] = trading_value['외국인합계'].rolling(window=5).sum()
        trading_value['기관_순매수_5일합'] = trading_value['기관합계'].rolling(window=5).sum()

        # 수급 오실레이터 계산 (외국인 순매수 합산 + 기관 순매수 합산)
        data = pd.DataFrame({
            '외국인_순매수_5일합': trading_value['외국인_순매수_5일합'],
            '기관_순매수_5일합': trading_value['기관_순매수_5일합']
        })
        data['수급오실레이터'] = data['외국인_순매수_5일합'] + data['기관_순매수_5일합']

        # 5일치 데이터 제거하여 시작일 맞추기
        data = data.dropna()

        print("Merged Data with Oscillator:")
        print(data.head())

        # 시가총액 데이터 가져오기
        market_cap = stock.get_market_cap_by_date(start_date, end_date, stock_code)

        print("Market Cap Data:")
        print(market_cap.head())

        # 시가총액과 오실레이터 데이터 병합
        data = data.join(market_cap[['시가총액']], how='inner')

        print("Final Merged Data:")
        print(data.head())

        # 차트 그리기
        fig, ax1 = plt.subplots(figsize=(14, 7))

        color = 'tab:blue'
        ax1.set_xlabel('날짜')
        ax1.set_ylabel('시가총액', color=color)
        ax1.plot(data.index, data['시가총액'], label=f'{stock_name or stock_code} 시가총액', color=color)
        ax1.tick_params(axis='y', labelcolor=color)
        ax1.set_ylim([data['시가총액'].min() * 0.95, data['시가총액'].max() * 1.05])  # 시가총액 y축 범위 조정

        ax2 = ax1.twinx()
        color = 'tab:red'
        ax2.set_ylabel('수급 오실레이터', color=color)
        ax2.plot(data.index, data['수급오실레이터'], label=f'{stock_name or stock_code} 수급 오실레이터', color=color)
        ax2.tick_params(axis='y', labelcolor=color)

        # 수급 오실레이터 y축 범위 조정
        osc_min = data['수급오실레이터'].min()
        osc_max = data['수급오실레이터'].max()
        osc_range = osc_max - osc_min
        ax2.set_ylim([osc_min - osc_range * 0.1, osc_max + osc_range * 0.1])

        fig.tight_layout()
        plt.title(f'{stock_name or stock_code} 시가총액과 수급 오실레이터')
        fig.legend(loc='upper left', bbox_to_anchor=(0.1, 0.9))
        # plt.show()

        # 차트를 이미지 파일로 저장
        chart_filename = f'{stock_name or stock_code}_chart.png'
        fig.savefig(chart_filename, format='png')
        plt.close(fig)
        print(f"차트가 {chart_filename} 파일로 저장되었습니다.")
    except Exception as e:
        print("차트를 그릴 수 없습니다. 관리자에게 문의해주세요.")
        print(f"오류 내용: {e}")
