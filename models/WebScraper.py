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
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            }
        elif self.firm_info.SEC_FIRM_ORDER == 2:
            # 회사 2번에 맞는 헤더 설정 (예시)
            return {
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G970F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36"
            }
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
        else:
            # 기본 CSS 선택자 (그 외의 경우)
            return '#defaultContent > div > table > tbody > tr'

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

        # SEC_FIRM_ORDER에 따른 CSS 선택자 적용
        css_selector = self._get_css_selector()
        soup_list = soup.select(css_selector)

        return soup_list

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
        css_selector = self._get_css_selector()
        soup_list = soup.select(css_selector)

        return soup_list

    def parse_table(self, soup_list):
        """
        파싱된 테이블 리스트를 처리하는 메서드
        :param soup_list: BeautifulSoup으로 파싱된 테이블 리스트
        :return: 테이블 행 데이터 출력 (예시)
        """
        for row in soup_list:
            print(f"테이블 행 데이터: {row.text}")
