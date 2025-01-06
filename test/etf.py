import requests
from bs4 import BeautifulSoup
import json
import re

# URL 설정
url = "https://navercomp.wisereport.co.kr/v2/ETF/index.aspx?cmp_cd=497780"

# User-Agent 헤더 설정
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
}

# HTML 가져오기
response = requests.get(url, headers=headers)
if response.status_code == 200:
    soup = BeautifulSoup(response.text, "html.parser")
    
    # <script> 태그 찾기
    script_tags = soup.find_all("script", type="text/javascript")
    
    # 'CU_data' 포함된 스크립트 찾기
    for script in script_tags:
        if "CU_data" in script.text:
            script_content = script.text
            # 정규표현식으로 'CU_data' 값 추출
            match = re.search(r'var CU_data = ({.*?});', script_content, re.S)
            if match:
                cu_data_str = match.group(1)  # JSON 형태의 데이터 추출
                cu_data = json.loads(cu_data_str)  # JSON 파싱
                print(cu_data)
            else:
                print("CU_data를 찾을 수 없습니다.")
            break
else:
    print(f"요청 실패: {response.status_code}")
