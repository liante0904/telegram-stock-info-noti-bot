import json
import os
import sqlite3


# JSON 파일 저장 경로 설정
directory = './json'
if not os.path.exists(directory):
    os.makedirs(directory)  # 경로가 없다면 생성
filename = os.path.join(directory, 'data_main_daily_send_all.json')


def print_different_urls():
    """JSON 파일을 읽고 ATTACH_URL과 ARTICLE_URL이 다른 경우 출력합니다."""
    try:
        with open(filename, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)  # JSON 파일 읽기

            for entry in data:
                attach_url = entry.get("ATTACH_URL")
                article_url = entry.get("ARTICLE_URL")

                # ATTACH_URL과 ARTICLE_URL이 다른 경우 출력
                if attach_url != article_url:
                    print(f"ATTACH_URL: {attach_url}")
                    print(f"ARTICLE_URL: {article_url}")
                    print("-" * 40)  # 구분선

    except FileNotFoundError:
        print(f"Error: {filename} 파일을 찾을 수 없습니다.")
    except json.JSONDecodeError:
        print("Error: JSON 파일을 읽는 중 오류가 발생했습니다.")


def update_urls():
    """JSON 파일을 읽고 ATTACH_URL과 ARTICLE_URL이 다른 경우 ARTICLE_URL을 ATTACH_URL로 업데이트합니다."""
    try:
        with open(filename, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)  # JSON 파일 읽기

            # URL이 다른 경우 업데이트
            for entry in data:
                attach_url = entry.get("ATTACH_URL")
                article_url = entry.get("ARTICLE_URL")

                # ATTACH_URL과 ARTICLE_URL이 다른 경우 업데이트
                if attach_url != article_url:
                    print(f"Updating ARTICLE_URL from {article_url} to {attach_url}")
                    entry["ARTICLE_URL"] = attach_url  # ARTICLE_URL을 ATTACH_URL로 업데이트

        # 변경된 데이터를 JSON 파일에 저장
        with open(filename, 'w', encoding='utf-8') as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=4)  # 업데이트된 데이터 저장

        print("URLs updated successfully.")

    except FileNotFoundError:
        print(f"Error: {filename} 파일을 찾을 수 없습니다.")
    except json.JSONDecodeError:
        print("Error: JSON 파일을 읽는 중 오류가 발생했습니다.")
        
def main():
    """메인 함수"""
    print_different_urls()  # 다른 URL을 출력하는 함수 호출
    # update_urls()
if __name__ == "__main__":
    main()  # 스크립트가 직접 실행될 때 main() 함수 호출