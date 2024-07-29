import os
import pickle
import json
from datetime import datetime, timedelta
import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Google Calendar API의 권한 범위 설정
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly', 'https://www.googleapis.com/auth/calendar']

# 데이터 URL
DATA_URL = 'https://comp.fnguide.com/SVO2/json/data/05_01/202407.json'

# 저장할 캘린더
CALENDAR_ID = 'e77be08645e15d43b5e2e2595b774f55ffcad7ba5c9eddc39f89406926a477dd@group.calendar.google.com'

def get_calendar_service():
    """Google Calendar API 서비스 객체를 반환합니다."""
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    try:
        service = build('calendar', 'v3', credentials=creds)
        return service
    except Exception as e:
        print(f"서비스 생성 오류: {e}")
        return None

def parse_date(date_str):
    """일자 문자열을 파싱하여 datetime 객체를 반환합니다. 형식이 잘못된 경우 종일 이벤트로 처리합니다."""
    try:
        if '--:--' in date_str:
            return datetime.strptime(date_str[:8], '%Y-%m-%d').date()
        return datetime.strptime(date_str, '%Y-%m-%d %H:%M')
    except ValueError:
        try:
            return datetime.strptime(date_str[:8], '%Y-%m-%d').date()
        except ValueError:
            return None

def process_title(title):
    """제목에서 Q&amp;A를 Q&A로 변환합니다."""
    return title.replace('Q&amp;A', 'Q&A')

def fetch_event_data():
    """URL에서 JSON 데이터를 가져와 이벤트 목록을 반환합니다."""
    response = requests.get(DATA_URL)
    response.raise_for_status()  # 요청 오류 시 예외 발생

    # BOM을 제거하기 위해 utf-8-sig로 읽기
    json_str = response.content.decode('utf-8-sig')
    data = json.loads(json_str)

    events = []

    for item in data.get('comp', []):
        try:
            # 이벤트 코드가 "IR1" 또는 "IR2"인 항목만 필터링
            if item.get('이벤트코드') not in ['IR1', 'IR2']:
                continue

            # 날짜 및 시간 처리
            date_time_str = item.get('일자')
            if not date_time_str:
                continue

            parsed_date = parse_date(date_time_str)
            if parsed_date is None:
                continue

            # 제목에서 Q&amp;A를 Q&A로 변환
            title = process_title(item.get('총발행주식수', ''))

            if isinstance(parsed_date, datetime):
                start_time = parsed_date.strftime('%Y-%m-%dT%H:%M:%S')
                end_time = (parsed_date + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%S')
                event = {
                    'summary': f"{item.get('기업명')}_{title}",
                    'location': item.get('변동주식수'),
                    'description': item.get('일련번호'),
                    'start': {'dateTime': start_time, 'timeZone': 'Asia/Seoul'},
                    'end': {'dateTime': end_time, 'timeZone': 'Asia/Seoul'}
                }
            else:
                # 종일 이벤트 처리
                start_time = parsed_date.strftime('%Y-%m-%d')
                end_time = (parsed_date + timedelta(days=1)).strftime('%Y-%m-%d')
                event = {
                    'summary': f"{item.get('기업명')}_{title}",
                    'location': item.get('변동주식수'),
                    'description': item.get('일련번호'),
                    'start': {'date': start_time, 'timeZone': 'Asia/Seoul'},
                    'end': {'date': end_time, 'timeZone': 'Asia/Seoul'}
                }

            events.append(event)
        except Exception as e:
            print(f'데이터 처리 오류: {e}')
    
    return events

def create_calendar_events(events, calendar_id):
    """Google Calendar에 일정을 생성합니다."""
    service = get_calendar_service()
    
    if service is None:
        print("Google Calendar 서비스 객체를 생성할 수 없습니다.")
        return

    # 기존 이벤트 목록 가져오기
    existing_events = service.events().list(calendarId=calendar_id, timeMin='2024-07-01T00:00:00Z', timeMax='2024-07-31T23:59:59Z').execute()
    existing_event_ids = {event['description']: event['id'] for event in existing_events.get('items', [])}

    for event in events:
        try:
            # 이벤트가 이미 존재하는지 확인
            event_id = existing_event_ids.get(event['description'])
            if event_id:
                # 이벤트 수정
                print(f'이벤트 수정됨: {event["summary"]}')
                service.events().update(calendarId=calendar_id, eventId=event_id, body=event).execute()
            else:
                # 이벤트 생성
                print(f'API 요청 이벤트: {event}')  # 요청 이벤트 로그
                event_result = service.events().insert(calendarId=calendar_id, body=event).execute()
                print(f'일정 생성됨: {event_result.get("summary")} (ID: {event_result.get("id")})')
        except Exception as e:
            print(f'일정 생성 또는 수정 중 오류 발생: {e}')

def main():
    events = fetch_event_data()
    create_calendar_events(events, calendar_id=CALENDAR_ID)

if __name__ == '__main__':
    main()
