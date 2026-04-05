import asyncio
import os
import sys
import time
import logging
import re
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# 프로젝트 루트 경로 추가 (run 폴더의 상위 경로)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.SQLiteManager import SQLiteManager
from models.OracleManager import OracleManager
from models.GeminiManager import GeminiManager
from utils.file_util import download_file_wget

# rclone 설정 (pdf_archiver 참조)
RCLONE_BIN = shutil.which("rclone") or os.path.expanduser("~/.local/bin/rclone")
RCLONE_REMOTE = "onedrive:/archive/pdf"
LOCAL_BUFFER_DIR = os.path.expanduser("~/downloads/pdf_archive_temp")

def _clean_title(title):
    if not title: return "no_title"
    # 특수문자 및 불필요한 태그 제거
    text = re.sub(r'\[.*?\]|\(.*?\)|\【.*?\】', '', title)
    text = re.sub(r'[\\/:*?"<>|!@#$%^&*.ⓒ,]', ' ', text)
    return "_".join(text.split())[:60].strip('_')

# 로그 설정 (디렉토리 자동 생성 포함)
def setup_logging():
    today = datetime.now().strftime('%Y%m%d')
    # 환경변수 LOG_BASE_DIR이 있으면 사용, 없으면 홈 디렉토리의 log 폴더 사용
    log_base = os.getenv("LOG_BASE_DIR", os.path.expanduser("~/log"))
    log_dir = os.path.join(log_base, today)
    
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"{today}_gemini_summary.log")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file)
        ]
    )

async def run_batch_summary(batch_limit=10):
    logging.info(f"🚀 AI 요약 배치 작업을 시작합니다...")
    
    db_manager = SQLiteManager()
    oracle_manager = OracleManager()

    # 요약이 없는 최신 레포트 목록 조회
    pending_reports = await db_manager.fetch_pending_summary_reports(limit=batch_limit)
    
    if not pending_reports:
        logging.info("✅ 요약할 대상 레포트가 없습니다. 작업을 종료합니다.")
        return

    logging.info(f"📋 총 {len(pending_reports)}개의 레포트 요약을 시도합니다.")
    gemini = GeminiManager() # 모델: models/gemini-2.5-flash-lite
    
    success_count = 0
    fail_count = 0

    for report in pending_reports:
        # logging.info(f"\n[작업 시작] {report['ARTICLE_TITLE']} ({report['FIRM_NM']})")
        
        # 0. 아카이빙 경로 및 파일명 생성 (pdf_archiver_async.py 로직 참조)
        report_id = report['report_id']
        firm = report['FIRM_NM']
        title = report['ARTICLE_TITLE']
        reg_dt = report.get('REG_DT', '00000000')
        
        clean_dt = re.sub(r'[^0-9]', '', str(reg_dt)) if reg_dt else "00000000"
        y_m = f"{clean_dt[:4]}-{clean_dt[4:6]}"
        yy_mm_dd = clean_dt[2:8]
        clean_title = _clean_title(title)
        canonical_filename = f"{yy_mm_dd}_{clean_title}_{report_id}.pdf"
        
        # 유효한 PDF URL 확인
        download_url = report.get('ATTACH_URL') or report.get('TELEGRAM_URL') or report.get('DOWNLOAD_URL')
        
        file_name = f"temp_batch_{report['report_id']}.pdf"
        
        try:
            # 1. PDF 다운로드
            success = await download_file_wget(report, URL=download_url, FILE_NAME=file_name)
            
            if not success or not os.path.exists(file_name) or os.path.getsize(file_name) < 1024:
                size = os.path.getsize(file_name) if os.path.exists(file_name) else 0
                logging.error(f"❌ 다운로드 실패 또는 파일 손상. (Size: {size} bytes)")
                fail_count += 1
                continue

            # 2. 제미나이 요약 (재시도 로직 포함)
            max_retries = 2
            summary_result = None
            
            for attempt in range(max_retries + 1):
                if attempt > 0:
                    logging.info(f"🔄 재시도 중... ({attempt}/{max_retries})")
                
                logging.info(f"🤖 제미나이 분석 중...")
                result = await gemini.summarize_pdf(file_name)
                
                if result['status'] == 'success':
                    summary_result = result
                    break
                elif "429" in str(result.get('error')):
                    logging.warning(f"🛑 쿼터 초과(429). 50초 대기 후 다시 시도합니다...")
                    await asyncio.sleep(50)
                    continue
                else:
                    logging.error(f"❌ 요약 실패: {result.get('error')}")
                    break
            
            if summary_result:
                # 3. DB 업데이트 (TELEGRAM_URL 기준, 발송 완료된 최신 레코드만)
                target_url = report.get('TELEGRAM_URL') or report.get('ATTACH_URL')
                
                # SQLite 업데이트
                await db_manager.update_report_summary_by_telegram_url(
                    telegram_url=target_url,
                    summary=summary_result['summary'],
                    model_name=summary_result['model']
                )
                
                # Oracle 업데이트 (통합된 OracleManager 사용)
                await oracle_manager.update_report_summary_by_telegram_url(
                    telegram_url=target_url,
                    summary=summary_result['summary'],
                    model_name=summary_result['model']
                )
                
                logging.info(f"✨ 요약 완료 및 SQLite/Oracle 저장 성공! (URL 기준)")
                success_count += 1
            else:
                fail_count += 1
                # 쿼터 에러로 재시도 실패 시 이번 배치 중단
                if attempt >= max_retries:
                    logging.error("🛑 재시도 횟수 초과 또는 심각한 쿼터 에러. 배치를 중단합니다.")
                    # break는 하되 아카이빙 시도는 할 수 있도록 처리할 것인가? 
                    # 요약 실패하더라도 다운로드가 성공했다면 아카이빙은 진행하는 것이 효율적
            
            # 4. 아카이빙 및 rclone 업로드
            if os.path.exists(file_name):
                # 로컬 정리용 경로 생성
                local_target_dir = Path(LOCAL_BUFFER_DIR) / y_m / firm
                local_target_dir.mkdir(parents=True, exist_ok=True)
                local_canonical_path = local_target_dir / canonical_filename
                
                # 파일 이동 (임시 -> 로컬 버퍼)
                shutil.move(file_name, str(local_canonical_path))
                
                # rclone 업로드 (move 명령어 사용 시 로컬 파일 삭제됨)
                remote_dest_dir = f"{RCLONE_REMOTE}/{y_m}/{firm}"
                rclone_cmd = [
                    RCLONE_BIN, "move", str(local_canonical_path), remote_dest_dir,
                    "--quiet", "--ignore-existing"
                ]
                
                try:
                    proc = await asyncio.create_subprocess_exec(
                        *rclone_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    _, stderr = await proc.communicate()
                    
                    if proc.returncode == 0:
                        logging.info(f"📁 rclone 업로드 성공: {canonical_filename}")
                        # SQLite 상태 업데이트 (sync_status = 2)
                        await db_manager.execute_query(
                            "UPDATE data_main_daily_send SET sync_status = 2 WHERE report_id = ?",
                            (report_id,)
                        )
                    else:
                        logging.error(f"❌ rclone 업로드 실패: {stderr.decode().strip()}")
                except Exception as r_e:
                    logging.error(f"❌ rclone 예외 발생: {r_e}")

            # 5. API 부하 방지를 위한 대기 (무료 티어 안정성 확보를 위해 20초 권장)
            await asyncio.sleep(20)

        except Exception as e:
            logging.error(f"🔥 예기치 못한 에러 발생: {e}")
            fail_count += 1
        finally:
            if os.path.exists(file_name):
                os.remove(file_name)

    logging.info(f"\n📊 작업 종료: 성공 {success_count}, 실패 {fail_count}")

if __name__ == "__main__":
    load_dotenv()
    setup_logging()
    
    # 실행 인자로 batch_limit을 받을 수 있도록 수정 (기본값 10)
    import sys
    limit = 10
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            limit = 10
            
    # 배치 실행
    asyncio.run(run_batch_summary(batch_limit=limit))
