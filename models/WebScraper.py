import requests
from bs4 import BeautifulSoup

class WebScraper:
    def __init__(self, target_url, firm_info):
        """
        WebScraper 클래스의 초기화 메서드
        :param target_url: 요청할 URL
        :param firm_info: FirmInfo 인스턴스 (회사별 정보)
        """
        self.target_url = target_url
        self.firm_info = firm_info
        self.headers = self._set_headers()

    def _set_headers(self):
        """
        SEC_FIRM_ORDER 값에 따라 헤더를 설정하는 내부 메서드
        :return: 적절한 헤더 딕셔너리
        """
        if self.firm_info.SEC_FIRM_ORDER == 0 or self.firm_info is None:
            # SEC_FIRM_ORDER가 0번에 맞는 헤더 설정
            return {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            }
        elif self.firm_info.SEC_FIRM_ORDER == 1:
            # 회사 1번에 맞는 헤더 설정
            return {
                "User-Agent": "Mozilla/5.0"
            }
        elif self.firm_info.SEC_FIRM_ORDER == 2:
            # 회사 2번에 맞는 헤더 설정 (예시)
            return {
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G970F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36"
            }
        elif self.firm_info.SEC_FIRM_ORDER == 4:
            # 회사 4번에 맞는 헤더 설정 (예시)
            return {
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "ko,en-US;q=0.9,en;q=0.8",
                "Connection": "keep-alive",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
                "X-Requested-With": "XMLHttpRequest"
            }
        elif self.firm_info.SEC_FIRM_ORDER == 7:
            # SEC_FIRM_ORDER가 7번일 때 Referer 추가
            return {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "Referer": "https://www.shinyoung.com/?page=10078&head=0"
            }
        else:
            # 기본 Header
            return {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            }
 
    def Get(self, params=None):
        """
        GET 요청을 통해 데이터를 가져오는 메서드
        :param params: 요청 시 함께 보낼 파라미터 (기본값은 None)
        :return: 파싱된 soupList 또는 None
        """
        try:
            response = requests.get(self.target_url, params=params, headers=self.headers, verify=False)
            response.raise_for_status()  # 요청 실패 시 예외 발생
        except requests.exceptions.RequestException as e:
            print(f"GET 요청 에러: {e}")
            return None

        # HTML 파싱
        soup = BeautifulSoup(response.content, "html.parser")

        print('='*40)
        print('==================WebScraper Get==================' )

        return soup

    def GetJson(self, params=None):
        response = requests.get(self.target_url, headers=self.headers, params=params)
        print('='*40)
        print('==================WebScraper GetJson==================' )
        return response.json()
    
    def Post(self, data=None):
        """
        POST 요청을 통해 데이터를 가져오는 메서드
        :param data: 요청 시 보낼 데이터 (기본값은 None)
        :return: 파싱된 soupList 또는 None
        """
        try:
            response = requests.post(self.target_url, data=data, headers=self.headers, verify=False)
            response.raise_for_status()  # 요청 실패 시 예외 발생
        except requests.exceptions.RequestException as e:
            print(f"POST 요청 에러: {e}")
            return None

        # HTML 파싱
        soup = BeautifulSoup(response.content, "html.parser")

        print('='*40)
        print('==================WebScraper Post==================' )

        return soup

    def PostJson(self, params=None, json=None):
        response = requests.post(self.target_url, headers=self.headers, params=params, json=json)
        print('='*40)
        print('==================WebScraper PostJson==================' )
        return response.json()