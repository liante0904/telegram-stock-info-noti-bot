import requests
from bs4 import BeautifulSoup

# 함수 정의: 주어진 URL에서 데이터 추출
def extract_data(url):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        # 지정된 CSS 셀렉터로 데이터 추출
        elements = soup.select('#container > div > div > ul > li > div.daily_bbs.m-mb20 > ul > li > div.con > ul > li.mb4 > h3 > a')
        # 추출된 데이터 리스트로 반환
        return [element.get_text(strip=True) for element in elements]
    else:
        print(f'웹 페이지를 불러오는 데 실패했습니다. 상태 코드: {response.status_code}')
        return []

# 두 개의 URL에서 데이터 추출
url1 = 'https://www.hanaw.com/main/research/research/list.cmd?pid=0&cid=0&curPage=1'
url2 = 'https://www.hanaw.com/main/research/research/list.cmd?pid=0&cid=0&curPage=2'

data1 = extract_data(url1)
data2 = extract_data(url2)

# 두 리스트를 이어 붙임
combined_data = data1 + data2

# 결과 출력
for i, data in enumerate(combined_data, 1):
    print(f"{i}: {data}")
