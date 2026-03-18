import aiohttp
import requests
import json
import re
import chardet  # 인코딩 감지용 (필요 시 설치: pip install chardet)
from bs4 import BeautifulSoup

class SyncWebScraper:
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
            # return {
            #     "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.182 Safari/537.36"
            # }
        # elif self.firm_info.SEC_FIRM_ORDER == 8:
        #     # 회사 2번에 맞는 헤더 설정 (예시)
        #     return {
        #         "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        #         "Accept-Encoding": "gzip, deflate, br",
        #         "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        #         "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36"
        #     }
        # ... 필요한 경우 다른 회사별 헤더 추가 가능

    def _clean_response_text(self, text):
            """응답 텍스트에서 제어 문자 및 비표준 문자를 제거하고 정규화"""
            try:
                # 제어 문자(ASCII 0x00-0x1F, 0x7F) 제거
                cleaned_text = re.sub(r'[\x00-\x1F\x7F]+', '', text)
                # 연속된 공백을 단일 공백으로 변환
                cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
                return cleaned_text
            except Exception as e:
                print(f"[텍스트 정규화 오류] {e}")
                return text

    def _detect_encoding(self, response):
        """응답 데이터의 인코딩 감지"""
        try:
            result = chardet.detect(response.content)
            encoding = result['encoding'] or 'utf-8'
            print(f"[감지된 인코딩] {encoding}")
            return encoding
        except Exception as e:
            print(f"[인코딩 감지 오류] {e}")
            return 'utf-8'
         
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

        return soup

    def GetJson(self, params=None):
        """HTTP GET 요청을 보내고 JSON 응답을 반환"""
        try:
            # HTTP GET 요청
            response = requests.get(self.target_url, headers=self.headers, params=params, timeout=10, verify=False)
            print('='*40)
            print('==================WebScraper GetJson==================')
            print('='*40)

            # HTTP 상태 코드 확인
            response.raise_for_status()

            # 인코딩 감지 및 설정
            try:
                result = chardet.detect(response.content)
                encoding = result['encoding'] or 'utf-8'
                print(f"[감지된 인코딩] {encoding}")
            except Exception as e:
                print(f"[인코딩 감지 오류] {e}")
                encoding = 'utf-8'
            response.encoding = encoding
            raw_text = response.text

            # 응답 텍스트 출력 (디버깅용)
            print(f"[원본 응답 (앞부분)]: {raw_text[:500]}...")

            # 응답 텍스트 정규화
            try:
                # 제어 문자(ASCII 0x00-0x1F, 0x7F) 및 BOM(\uFEFF) 제거
                cleaned_text = re.sub(r'[\x00-\x1F\x7F-\x9F\uFEFF]+', '', raw_text)
                # 연속된 공백을 단일 공백으로 변환
                cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
            except Exception as e:
                print(f"[텍스트 정규화 오류] {e}")
                cleaned_text = raw_text

            if raw_text != cleaned_text:
                print("[경고] 응답 텍스트가 정규화되었습니다. 제어 문자 또는 비표준 문자가 제거됨.")

            # JSON 파싱 시도
            try:
                json_data = json.loads(cleaned_text)
                print("[JSON 파싱 성공] 데이터 크기:", len(str(json_data)))
                return json_data
            except json.JSONDecodeError as e:
                print(f"[JSON 파싱 오류] {e}")
                print(f"[오류 위치] Line {e.lineno}, Column {e.colno}, Char {e.pos}")
                print(f"[문제가 되는 응답 내용 일부]: {cleaned_text[max(0, e.pos-100):e.pos+100]}")
                
                # 제어 문자 디버깅
                error_snippet = cleaned_text[max(0, e.pos-10):e.pos+10]
                print("[오류 위치 근처 문자]:")
                for i, char in enumerate(error_snippet):
                    print(f"Char {i}: {char!r} (ASCII: {ord(char)})")
                
                # 디버깅용 응답 저장
                with open("error_response.txt", "w", encoding="utf-8") as f:
                    f.write(raw_text)
                print("[디버깅] 원본 응답이 error_response.txt에 저장되었습니다.")
                
                return None

        except requests.exceptions.Timeout:
            print("[HTTP 요청 오류] 요청 시간이 초과되었습니다.")
            return None
        except requests.exceptions.HTTPError as e:
            print(f"[HTTP 요청 오류] 상태 코드: {e.response.status_code}, 메시지: {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"[HTTP 요청 오류] {e}")
            return None
        except Exception as e:
            print(f"[알 수 없는 오류] {e}")
            return None

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

        print('='*40)
        print('==================WebScraper Post==================' )

        return soup

    def PostJson(self, params=None, json=None):
        response = requests.post(self.target_url, headers=self.headers, params=params, json=json)
        print('='*40)
        print('==================WebScraper PostJson==================' )
        return response.json()


class AsyncWebScraper:
    def __init__(self, target_url, headers=None):
        """
        AsyncWebScraper 클래스의 초기화 메서드
        :param target_url: 요청할 URL
        :param headers: 요청에 사용할 헤더 (기본값은 None)
        """
        self.target_url = target_url
        self.headers = headers or {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"}

    async def Get(self, session=None, params=None):
        """비동기 GET 요청을 통해 데이터를 가져오는 메서드"""
        # 세션이 없으면 새 세션을 생성하여 사용
        close_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True

        try:
            response = await session.get(self.target_url, headers=self.headers, params=params)
            response.raise_for_status()
            html = await response.text()
            return BeautifulSoup(html, "html.parser")
        finally:
            if close_session:
                await session.close()  # 세션을 닫아 메모리 누수 방지
                
    async def Post(self, session=None, data=None):
        """비동기 POST 요청을 통해 데이터를 가져오는 메서드"""
        async with session or aiohttp.ClientSession() as new_session:
            response = await (session or new_session).post(self.target_url, headers=self.headers, data=data)
            response.raise_for_status()
            html = await response.text()
            return BeautifulSoup(html, "html.parser")

    async def GetJson(self, session=None, params=None):
        """비동기 GET 요청을 통해 JSON 데이터를 가져오는 메서드"""
        async with session or aiohttp.ClientSession() as new_session:
            response = await (session or new_session).get(self.target_url, headers=self.headers, params=params)
            response.raise_for_status()
            print('=' * 40)
            print('==================AsyncWebScraper GetJson==================')
            return await response.json()

    async def PostJson(self, headers=None, session=None, params=None, json_data=None):
        """
        비동기 POST 요청을 통해 JSON 데이터를 가져오는 메서드.
        :param session: aiohttp ClientSession 인스턴스 (선택적)
        :param params: 요청 시 보낼 URL 인코딩 데이터 (기본값 None)
        :param json_data: JSON 데이터 (기본값 None)
        """
        conn = aiohttp.TCPConnector(ssl=False, force_close=True)  # SSL 인증 비활성화
        self.headers = headers
        if headers is None:
            self.headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                "Referrer": self.target_url  # Referrer 헤더 추가
            }
        async with session or aiohttp.ClientSession(connector=conn) as new_session:
            response = await (session or new_session).post(self.target_url, headers=self.headers, data=params, json=json_data)
            response.raise_for_status()
            print('=' * 40)
            print('==================AsyncWebScraper PostJson==================')
            return await response.json()



        