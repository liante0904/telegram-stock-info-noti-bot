import subprocess
import json
import os
import requests
import sys
from datetime import datetime
from pypdf import PdfReader
from config import *

def run_remote_sql(sql_query):
    """SSH를 통해 OCI 서버에서 SQLite 쿼리를 실행합니다."""
    safe_query = sql_query.replace('"', '\\"')
    cmd = f'ssh {REMOTE_SSH_ALIAS} "sqlite3 {REMOTE_DB_PATH} \\"{safe_query}\\""'
    try:
        result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode().strip()
        return result
    except Exception as e:
        print(f"❌ 원격 SQL 실행 실패: {e}")
        return None

def fetch_pending_reports(limit=5):
    """요약이 필요한 리포트 리스트를 가져옵니다."""
    sql = f"SELECT id, ARTICLE_TITLE, ATTACH_URL, FIRM_NM, TELEGRAM_URL FROM data_main_daily_send WHERE (GEMINI_SUMMARY IS NULL OR GEMINI_SUMMARY = '') ORDER BY id DESC LIMIT {limit};"
    result = run_remote_sql(sql)
    
    reports = []
    if result:
        lines = result.split('\n')
        for line in lines:
            parts = line.split('|')
            if len(parts) >= 3:
                reports.append({
                    "id": parts[0],
                    "title": parts[1],
                    "url": parts[2] or (parts[4] if len(parts) > 4 else ""),
                    "firm": parts[3] if len(parts) > 3 else "Unknown"
                })
    return reports

def extract_text_from_pdf(pdf_path):
    """PDF에서 텍스트를 추출합니다."""
    text = ""
    try:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    except Exception as e:
        print(f"❌ PDF 텍스트 추출 실패: {e}")
    return text

def summarize_with_ollama(text):
    """로컬 Ollama를 이용해 요약합니다."""
    if not text: return "텍스트 추출 실패"
    
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": f"{SUMMARY_PROMPT}\n\n[레포트 내용]:\n{text[:12000]}",
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=600)
        return response.json().get('response', '요약 실패')
    except Exception as e:
        return f"Error: {e}"

def update_remote_databases(report_id, summary):
    """임시 실행 스크립트를 전송하여 원격 서버에서 통합 업데이트를 실행합니다."""
    # 1. 요약본 저장
    remote_summary_file = f"/tmp/summary_{report_id}.txt"
    with open(LOCAL_TEMP_SUMMARY, 'w', encoding='utf-8') as f:
        f.write(summary)
    
    # 2. 실행용 파이썬 스크립트 생성 (원격지용 - importlib 직접 로드 방식)
    model_tag = f"local-{OLLAMA_MODEL}"
    remote_script_file = f"/tmp/update_{report_id}.py"
    script_content = f"""
import sys
import os
import asyncio
import importlib.util

# 프로젝트 루트 및 모듈 경로 설정
PROJECT_ROOT = '{REMOTE_PROJECT_DIR}'
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

def get_data_manager():
    # 경로를 통해 DataManager 모듈을 직접 로드
    module_path = os.path.join(PROJECT_ROOT, 'models', 'DataManager.py')
    spec = importlib.util.spec_from_file_location("DataManager", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["DataManager"] = module
    spec.loader.exec_module(module)
    return module.DataManager

try:
    DataManagerClass = get_data_manager()
    
    async def run():
        if not os.path.exists('{remote_summary_file}'):
            print("Summary file not found on remote server", file=sys.stderr)
            return

        with open('{remote_summary_file}', 'r', encoding='utf-8') as f:
            summary = f.read()
        
        dm = DataManagerClass()
        await dm.update_report_summary({report_id}, summary, '{model_tag}')
        
        # 완료 후 파일 삭제
        os.remove('{remote_summary_file}')
        print("Remote Update Success")

    if __name__ == "__main__":
        asyncio.run(run())
except Exception as e:
    import traceback
    print(f"Remote Script Error: {{e}}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
"""
    local_script_path = f"./temp_update_{report_id}.py"
    with open(local_script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)

    try:
        # 3. SCP로 파일들 전송
        subprocess.run(f"scp {LOCAL_TEMP_SUMMARY} {REMOTE_SSH_ALIAS}:{remote_summary_file}", shell=True, check=True, capture_output=True)
        subprocess.run(f"scp {local_script_path} {REMOTE_SSH_ALIAS}:{remote_script_file}", shell=True, check=True, capture_output=True)

        # 4. SSH로 실행 (PYTHONPATH 강제 주입)
        ssh_cmd = f"ssh {REMOTE_SSH_ALIAS} \"PYTHONPATH={REMOTE_PROJECT_DIR} {REMOTE_PYTHON_PATH} {remote_script_file}\""
        result = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True)
        
        # 5. 원격지 스크립트 삭제
        subprocess.run(f"ssh {REMOTE_SSH_ALIAS} \"rm {remote_script_file}\"", shell=True)
        
        if "Remote Update Success" in result.stdout:
            return True
        else:
            print(f"❌ 원격 서버 에러:\n{result.stderr or result.stdout}")
            return False

    except Exception as e:
        print(f"🔥 업데이트 로직 오류: {e}")
        return False
    finally:
        if os.path.exists(local_script_path): os.remove(local_script_path)

def main():
    print(f"🚀 M4 맥미니 로컬 워커 시작 ({OLLAMA_MODEL})")
    reports = fetch_pending_reports(limit=5)
    if not reports:
        print("✅ 처리할 리포트가 없습니다.")
        return

    for report in reports:
        print(f"\n[작업 시작] {report['title']} ({report['firm']})")
        if not report['url'] or '.pdf' not in report['url'].lower(): continue

        try:
            # 1. 다운로드
            r = requests.get(report['url'], headers={'User-Agent': 'Mozilla/5.0'}, stream=True, timeout=30)
            with open(LOCAL_TEMP_PDF, 'wb') as f: f.write(r.content)
            
            # 2. 텍스트 추출 및 요약
            text = extract_text_from_pdf(LOCAL_TEMP_PDF)
            if not text.strip(): continue
            
            print("🤖 로컬 요약 및 서버 전송 중...")
            summary = summarize_with_ollama(text)
            
            # 3. 원격 업데이트 실행
            if update_remote_databases(report['id'], summary):
                print(f"✨ 원격 업데이트 완료! (ID: {report['id']})")
            else:
                print(f"⚠️ 원격 업데이트 중 오류 발생")
            
        except Exception as e:
            print(f"🔥 에러: {e}")
        finally:
            for f in [LOCAL_TEMP_PDF, LOCAL_TEMP_SUMMARY]:
                if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    main()
