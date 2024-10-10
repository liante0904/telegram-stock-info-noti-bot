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
            # SEC_FIRM_ORDER가 0이거나 회사 정보가 없을 경우 기본 헤더 사용
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
        # elif self.firm_info.SEC_FIRM_ORDER == 8:
        #     # 회사 2번에 맞는 헤더 설정 (예시)
        #     return {
        #         "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        #         "Accept-Encoding": "gzip, deflate, br",
        #         "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        #         "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36"
        #     }
        # ... 필요한 경우 다른 회사별 헤더 추가 가능
        else:
            # 기본적으로 SEC_FIRM_ORDER 값이 0이 아닌 경우의 기본 헤더 설정
            return {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.182 Safari/537.36"
            }

    def _get_css_selector(self):
        """
        SEC_FIRM_ORDER 값에 따라 CSS 선택자를 반환하는 메서드
        :return: 적절한 CSS 선택자 문자열
        """
        if self.firm_info.SEC_FIRM_ORDER == 0 or self.firm_info is None:
            # 기본 CSS 선택자 (SEC_FIRM_ORDER가 0일 때)
            return '#contents > table > tbody > tr'
        elif self.firm_info.SEC_FIRM_ORDER == 1:
            # 회사 1번에 대한 CSS 선택자
            return '#mainContent > div > table > tbody > tr'
        elif self.firm_info.SEC_FIRM_ORDER == 2:
            # 회사 2번에 대한 CSS 선택자 (예시)
            return '#customContent > section > div > table > tr'
        # ... 필요한 경우 다른 회사별 CSS 선택자 추가 가능
        elif self.firm_info.SEC_FIRM_ORDER == 16:
            return '#sub-container > div.table-wrap > table > tbody > tr'
        else:
            pass
            # 기본 CSS 선택자 (그 외의 경우)
            # return '#defaultContent > div > table > tbody > tr'

    def _parse_list_item(self, soup_list):
        """
        SEC_FIRM_ORDER 값에 따라 각기 다른 방식으로 리스트 데이터를 파싱하는 메서드
        :param soup_list: BeautifulSoup으로 파싱된 리스트 데이터
        :return: 파싱된 데이터를 포함하는 리스트
        """
        result = []

        if self.firm_info.SEC_FIRM_ORDER == 0:
            # SEC_FIRM_ORDER가 0일 때 처리 (제공된 코드 기반)
            for item in soup_list:
                date = item.select('td')[3].get_text()
                list_links = item.select('a')

                LIST_ARTICLE_URL = 'https://www.ls-sec.co.kr/EtwFrontBoard/' + list_links[0]['href'].replace("amp;", "")
                LIST_ARTICLE_TITLE = list_links[0].get_text()
                LIST_ARTICLE_TITLE = LIST_ARTICLE_TITLE[LIST_ARTICLE_TITLE.find("]") + 1:].strip()
                POST_DATE = date.strip()

                result.append({
                    'LIST_ARTICLE_URL': LIST_ARTICLE_URL,
                    'LIST_ARTICLE_TITLE': LIST_ARTICLE_TITLE,
                    'POST_DATE': POST_DATE
                })

        elif self.firm_info.SEC_FIRM_ORDER == 1:
            pass
            # # 회사 1번에 대한 파싱 로직 (추가적인 파싱 로직 필요)
            # for item in soup_list:
            #     # 예시: 리스트의 첫 번째 링크와 날짜 가져오기
            #     date = item.select('td')[2].get_text()  # 다른 칸의 데이터를 가져올 수도 있음
            #     list_links = item.select('a')

            #     LIST_ARTICLE_URL = 'https://www.company1.com' + list_links[0]['href']
            #     LIST_ARTICLE_TITLE = list_links[0].get_text().strip()
            #     POST_DATE = date.strip()

            #     result.append({
            #         'LIST_ARTICLE_URL': LIST_ARTICLE_URL,
            #         'LIST_ARTICLE_TITLE': LIST_ARTICLE_TITLE,
            #         'POST_DATE': POST_DATE
            #     })

        elif self.firm_info.SEC_FIRM_ORDER == 2:
            # 회사 2번에 대한 파싱 로직 (추가적인 파싱 로직 필요)
            for item in soup_list:
                # 예시: 리스트의 제목과 링크 가져오기
                list_links = item.select('a')
                date = item.select('td')[1].get_text()

                LIST_ARTICLE_URL = 'https://www.company2.com' + list_links[0]['href']
                LIST_ARTICLE_TITLE = list_links[0].get_text().strip()
                POST_DATE = date.strip()

                result.append({
                    'LIST_ARTICLE_URL': LIST_ARTICLE_URL,
                    'LIST_ARTICLE_TITLE': LIST_ARTICLE_TITLE,
                    'POST_DATE': POST_DATE
                })
        else: return
        # 필요한 경우 다른 SEC_FIRM_ORDER에 대한 로직 추가 가능

        return result
    
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
        # print(soup)
        # SEC_FIRM_ORDER에 따른 CSS 선택자 적용
        # css_selector = self._get_css_selector()
        # soup_list = soup.select(css_selector)

        # # SEC_FIRM_ORDER에 따른 파싱 로직 적용
        # result = self._parse_list_item(soup_list)
        return soup

    def GetJson(self, params=None):
        response = requests.get(self.target_url, headers=self.headers, params=params)
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

        # SEC_FIRM_ORDER에 따른 CSS 선택자 적용
        # css_selector = self._get_css_selector()
        # soup_list = soup.select(css_selector)

        # return soup_list
        return soup

    def PostJson(self, params=None):
        response = requests.post(self.target_url, headers=self.headers, params=params)
        return response.json()
    
    def parse_table(self, soup_list):
        """
        파싱된 테이블 리스트를 처리하는 메서드
        :param soup_list: BeautifulSoup으로 파싱된 테이블 리스트
        :return: 테이블 행 데이터 출력 (예시)
        """
        for row in soup_list:
            print(f"테이블 행 데이터: {row.text}")
