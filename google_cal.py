import os
import pickle
import json
import argparse
from datetime import datetime, timedelta
import requests
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Google Calendar API의 권한 범위 설정
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly', 'https://www.googleapis.com/auth/calendar']

# 저장할 캘린더
CALENDAR_ID = 'e77be08645e15d43b5e2e2595b774f55ffcad7ba5c9eddc39f89406926a477dd@group.calendar.google.com'
# 저장 경로
EVENTS_JSON_DIR = os.path.join(os.getcwd(), 'json')
EVENTS_JSON_FILE = os.path.join(EVENTS_JSON_DIR, 'google_cal_event.json')

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
    today = datetime.today()
    end_date = today + timedelta(days=90)
    months = [today.strftime('%Y%m'), (today + timedelta(days=30)).strftime('%Y%m'), (today + timedelta(days=60)).strftime('%Y%m')]
    
    events = []
    for month in months:
        url = f'https://comp.fnguide.com/SVO2/json/data/05_01/{month}.json'
        response = requests.get(url)
        
        if response.status_code != 200:
            print(f"URL {url}에 대한 요청이 실패했습니다. 응답 코드: {response.status_code}")
            continue
        
        json_str = response.content.decode('utf-8-sig')
        data = json.loads(json_str)
        
        for item in data.get('comp', []):
            try:
                if item.get('이벤트코드') not in ['IR1', 'IR2']:
                    continue

                date_time_str = item.get('일자')
                if not date_time_str:
                    continue

                parsed_date = parse_date(date_time_str)
                if parsed_date is None:
                    continue

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

def ensure_events_json_dir_exists():
    """이벤트 JSON 디렉토리가 존재하지 않으면 생성합니다."""
    if not os.path.exists(EVENTS_JSON_DIR):
        os.makedirs(EVENTS_JSON_DIR)

def load_existing_events():
    """이벤트 JSON 파일에서 기존 이벤트를 로드합니다."""
    ensure_events_json_dir_exists()
    if not os.path.exists(EVENTS_JSON_FILE):
        return {}
    
    try:
        with open(EVENTS_JSON_FILE, 'r', encoding='utf-8') as file:
            return json.load(file)
    except json.JSONDecodeError as e:
        print(f'JSON 디코딩 오류: {e}')
        return {}
    except IOError as e:
        print(f'파일 읽기 오류: {e}')
        return {}

def save_existing_events(events):
    """기존 이벤트를 JSON 파일에 저장합니다."""
    ensure_events_json_dir_exists()
    try:
        with open(EVENTS_JSON_FILE, 'w', encoding='utf-8') as file:
            json.dump(events, file, ensure_ascii=False, indent=4)
    except IOError as e:
        print(f'파일 쓰기 오류: {e}')

def create_or_update_events(events, calendar_id):
    """Google Calendar에 일정을 생성하거나 업데이트합니다."""
    service = get_calendar_service()
    
    if service is None:
        print("Google Calendar 서비스 객체를 생성할 수 없습니다.")
        return

    now = datetime.utcnow().isoformat() + 'Z'
    future = (datetime.utcnow() + timedelta(days=90)).isoformat() + 'Z'
    existing_events = service.events().list(calendarId=calendar_id, timeMin=now, timeMax=future).execute()
    
    existing_event_map = {}
    for event in existing_events.get('items', []):
        key = (
            event.get('summary'),
            event['start'].get('dateTime') or event['start'].get('date'),
            event['end'].get('dateTime') or event['end'].get('date'),
            event.get('description')
        )
        existing_event_map[key] = event['id']  # 이벤트의 ID를 저장

    # 기존 이벤트 데이터 로드
    registered_events = load_existing_events()
    
    # 중복을 방지하기 위한 추가 로직
    events_to_insert = []
    events_to_update = []

    for event in events:
        event_key = (
            event['summary'],
            event['start'].get('dateTime') or event['start'].get('date'),
            event['end'].get('dateTime') or event['end'].get('date'),
            event.get('description')
        )
        
        # 중복 체크
        event_key_str = json.dumps(event_key, ensure_ascii=False)  # 튜플을 문자열로 변환
        if event_key_str in registered_events:
            print(f"중복 이벤트 발견: {event['summary']}")
            continue
        
        event_id = existing_event_map.get(event_key)
        if event_id:
            # 이벤트가 수정된 경우에만 업데이트
            existing_event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
            needs_update = (
                existing_event['summary'] != event['summary']
                or existing_event['start'] != event['start']
                or existing_event['end'] != event['end']
                or existing_event.get('location') != event.get('location')
                or existing_event.get('description') != event.get('description')
            )
            if needs_update:
                events_to_update.append((event_id, event))
        else:
            events_to_insert.append(event)

    # 이벤트 업데이트
    for event_id, event in events_to_update:
        try:
            print(f'이벤트 수정됨: {event["summary"]}')
            service.events().update(calendarId=calendar_id, eventId=event_id, body=event).execute()
        except Exception as e:
            print(f'이벤트 수정 중 오류 발생: {e}')

    # 새 이벤트 추가
    for event in events_to_insert:
        try:
            print(f'API 요청 이벤트: {event}')  # 요청 이벤트 로그
            event_result = service.events().insert(calendarId=calendar_id, body=event).execute()
            print(f'일정 생성됨: {event_result.get("summary")} (ID: {event_result.get("id")})')
            
            # 새로 등록된 이벤트를 registered_events에 추가하고 파일에 저장
            event_key = (
                event['summary'],
                event['start'].get('dateTime') or event['start'].get('date'),
                event['end'].get('dateTime') or event['end'].get('date'),
                event.get('description')
            )
            event_key_str = json.dumps(event_key, ensure_ascii=False)
            registered_events[event_key_str] = event_result.get("id")
            save_existing_events(registered_events)  # 이벤트 등록 후 파일 업데이트
        except Exception as e:
            print(f'일정 생성 중 오류 발생: {e}')

def delete_all_events(calendar_id):
    """Google Calendar에서 모든 이벤트를 삭제합니다."""
    service = get_calendar_service()
    
    if service is None:
        print("Google Calendar 서비스 객체를 생성할 수 없습니다.")
        return

    now = datetime.utcnow().isoformat() + 'Z'
    future = (datetime.utcnow() + timedelta(days=90)).isoformat() + 'Z'
    events = service.events().list(calendarId=calendar_id, timeMin=now, timeMax=future).execute()
    
    for event in events.get('items', []):
        try:
            event_id = event['id']
            service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
            print(f'이벤트 삭제됨: {event.get("summary")} (ID: {event_id})')
        except Exception as e:
            print(f'이벤트 삭제 중 오류 발생: {e}')

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='Google Calendar 이벤트 관리')
    parser.add_argument('--delete_all', action='store_true', help='모든 이벤트를 삭제합니다.')
    args = parser.parse_args()
    
    if args.delete_all:
        delete_all_events(calendar_id=CALENDAR_ID)
    else:
        events = fetch_event_data()
        create_or_update_events(events, calendar_id=CALENDAR_ID)

if __name__ == '__main__':
    main()
