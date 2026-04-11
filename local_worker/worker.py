import asyncio
import aiohttp
import json
import os
import sys
from datetime import datetime
from pypdf import PdfReader
from bs4 import BeautifulSoup
import subprocess
from config import *

# --- 설정 ---
CONCURRENT_LIMIT = 3 # 동시에 처리할 리포트 수 (Ollama 요약 병렬화)
FETCH_LIMIT = 5     # 배치 처리를 위해 처리 건수를 더 늘림
UPDATE_ORACLE_BATCH = False # 배치 처리 시 Oracle 업데이트 여부

async def extract_text_from_html_async(session, url):
    """웹 페이지 URL에서 비동기로 HTML 텍스트를 추출합니다."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        async with session.get(url, headers=headers, timeout=20, ssl=False) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            for script_or_style in soup(["script", "style", "nav", "footer", "header"]):
                script_or_style.decompose()
            text = soup.get_text(separator='\n')
            lines = (line.strip() for line in text.splitlines())
            text = '\n'.join(line for line in lines if line)
            return text
    except Exception as e:
        return ""

def extract_text_from_pdf(pdf_path):
    """PDF에서 텍스트를 추출합니다."""
    text = ""
    try:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    except Exception as e:
        pass
    return text

async def summarize_with_ollama_async(session, text, title):
    """로컬 Ollama를 이용해 비동기로 요약합니다."""
    if not text: return None
    
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": f"{SUMMARY_PROMPT}\n\n[레포트 내용]:\n{text[:12000]}",
        "stream": False
    }
    try:
        logger.info(f"🤖 요약 중... ({title[:30]}...)")
        async with session.post(OLLAMA_URL, json=payload, timeout=600) as response:
            result = await response.json()
            return result.get('response')
    except Exception as e:
        logger.error(f"❌ 요약 실패 ({title}): {e}")
        return None

async def run_command(cmd):
    """쉘 명령어를 비동기로 실행합니다."""
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode, stdout.decode(), stderr.decode()

async def batch_update_remote_databases(results, update_oracle=True):
    """요약된 결과들을 모아서 한 번에 원격 DB에 업데이트합니다."""
    if not results: return
    
    batch_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    local_json_path = f"./batch_summary_{batch_id}.json"
    local_script_path = f"./batch_update_{batch_id}.py"
    
    remote_json_file = f"/tmp/batch_{batch_id}.json"
    remote_script_file = f"/tmp/update_{batch_id}.py"
    model_tag = f"local-{OLLAMA_MODEL}"

    # 결과를 JSON 파일로 저장
    with open(local_json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # 원격 일괄 업데이트 스크립트 생성
    script_content = f"""
import sys, os, asyncio, importlib.util, json
from loguru import logger
PROJECT_ROOT = '{REMOTE_PROJECT_DIR}'
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

def get_data_manager():
    module_path = os.path.join(PROJECT_ROOT, 'models', 'DataManager.py')
    spec = importlib.util.spec_from_file_location("DataManager", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["DataManager"] = module
    spec.loader.exec_module(module)
    return module.DataManager

try:
    DataManagerClass = get_data_manager()
    async def run():
        if not os.path.exists('{remote_json_file}'): return
        with open('{remote_json_file}', 'r', encoding='utf-8') as f:
            data_list = json.load(f)
        
        dm = DataManagerClass()
        stats = {{'success': 0, 'fail': 0, 'oracle_ok': 0}}
        
        for item in data_list:
            report_id = item['report_id']
            summary = item['summary']
            
            try:
                # 1. SQLite 업데이트
                res_sq = await dm.sqlite.update_report_summary(report_id, summary, '{model_tag}')
                if res_sq: 
                    stats['success'] += 1
                    # 2. Oracle 업데이트 (선택적)
                    if {'True' if update_oracle else 'False'}:
                        try:
                            res_ora = await dm.oracle_old.update_report_summary(report_id, summary, '{model_tag}')
                            if res_ora: stats['oracle_ok'] += 1
                        except: pass
                else:
                    stats['fail'] += 1
            except:
                stats['fail'] += 1
        
        os.remove('{remote_json_file}')
        logger.info(f"BATCH_RESULT: {{json.dumps(stats)}}")
    asyncio.run(run())
except Exception as e:
    logger.error(f"Batch Script Error: {{e}}", file=sys.stderr)
    sys.exit(1)
"""
    with open(local_script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)

    try:
        logger.info(f"\n📤 원격 서버로 {len(results)}건 일괄 전송 및 업데이트 중...")
        # SCP 전송
        await run_command(f"scp {local_json_path} {REMOTE_SSH_ALIAS}:{remote_json_file}")
        await run_command(f"scp {local_script_path} {REMOTE_SSH_ALIAS}:{remote_script_file}")

        # SSH 실행
        cmd = f"ssh {REMOTE_SSH_ALIAS} \"PYTHONPATH={REMOTE_PROJECT_DIR} {REMOTE_PYTHON_PATH} {remote_script_file}\""
        ret, stdout, stderr = await run_command(cmd)
        
        await run_command(f"ssh {REMOTE_SSH_ALIAS} \"rm {remote_script_file}\"")
        
        if "BATCH_RESULT:" in stdout:
            res = json.loads(stdout.split("BATCH_RESULT:")[1].strip())
            logger.info(f"✨ 업데이트 완료: 성공 {res['success']}건, 실패 {res['fail']}건, Oracle {res['oracle_ok'] if update_oracle else 'SKIP'}건")
        else:
            logger.info(f"❌ 배치 업데이트 실패: {stderr}")
    finally:
        for f in [local_json_path, local_script_path]:
            if os.path.exists(f): os.remove(f)

async def process_report(session, report, semaphore):
    """개별 리포트 요약 작업 (요약 결과만 반환)"""
    async with semaphore:
        if not report['url']: return None

        text = ""
        is_pdf = '.pdf' in report['url'].lower()
        temp_pdf = f"./temp_{report['report_id']}.pdf"

        try:
            if is_pdf:
                # Referer를 추가하여 봇 차단 우회 시도
                referer = "https://www.hmsec.com/" if "hmsec.com" in report['url'] else report['url']
                wget_cmd = f"wget --user-agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36' " \
                           f"--header='Referer: {referer}' " \
                           f"-O {temp_pdf} '{report['url']}' --max-redirect=10 --no-check-certificate --quiet --timeout=15 --tries=2"
                ret, _, _ = await run_command(wget_cmd)
                if ret == 0 and os.path.exists(temp_pdf) and os.path.getsize(temp_pdf) >= 1024:
                    text = extract_text_from_pdf(temp_pdf)
                if os.path.exists(temp_pdf): os.remove(temp_pdf)
            else:
                text = await extract_text_from_html_async(session, report['url'])

            if not text or not text.strip(): return None
            
            summary = await summarize_with_ollama_async(session, text, report['title'])
            if summary:
                return {"report_id": report['report_id'], "summary": summary, "title": report['title']}
        except Exception as e:
            logger.error(f"🔥 에러 ({report['title'][:20]}): {e}")
        return None

def run_remote_sql(sql_query):
    """동기식으로 원격 SQL 실행"""
    safe_query = sql_query.replace('"', '\\"')
    cmd = f'ssh {REMOTE_SSH_ALIAS} "sqlite3 {REMOTE_DB_PATH} \\"{safe_query}\\""'
    try:
        return subprocess.check_output(cmd, shell=True).decode().strip()
    except: return None

def fetch_pending_reports(limit=FETCH_LIMIT):
    sql = f"""
    SELECT report_id, ARTICLE_TITLE, ATTACH_URL, FIRM_NM, TELEGRAM_URL, DOWNLOAD_URL
    FROM data_main_daily_send 
    WHERE (GEMINI_SUMMARY IS NULL OR GEMINI_SUMMARY = '') 
    AND (ATTACH_URL IS NOT NULL AND ATTACH_URL != '') 
    AND SEC_FIRM_ORDER NOT IN (19) 
    ORDER BY SAVE_TIME DESC 
    LIMIT {limit};
    """
    result = run_remote_sql(sql)
    reports = []
    if result:
        for line in result.split('\n'):
            parts = line.split('|')
            if len(parts) >= 3:
                candidates = [u for u in [parts[5] if len(parts)>5 else None, parts[2], parts[4] if len(parts)>4 else None] if u]
                url = next((u for u in candidates if '.pdf' in u.lower()), candidates[0] if candidates else None)
                reports.append({"report_id": parts[0], "title": parts[1], "url": url})
    return reports

async def main():
    logger.info(f"🚀 M4 맥미니 비동기 배치 워커 (Model: {OLLAMA_MODEL}, Limit: {FETCH_LIMIT})")
    reports = fetch_pending_reports()
    if not reports:
        logger.info("✅ 처리할 리포트가 없습니다.")
        return

    semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)
    async with aiohttp.ClientSession() as session:
        tasks = [process_report(session, report, semaphore) for report in reports]
        results = await asyncio.gather(*tasks)
        
        # 유효한 요약 결과만 필터링
        valid_results = [r for r in results if r is not None]
        
        if valid_results:
            await batch_update_remote_databases(valid_results, update_oracle=UPDATE_ORACLE_BATCH)
        else:
            logger.info("ℹ️ 요약된 결과가 없습니다.")

if __name__ == "__main__":
    asyncio.run(main())
