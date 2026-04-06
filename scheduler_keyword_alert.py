import os
import subprocess
import logging
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# 로그 설정 (디렉토리 자동 생성 포함)
def get_log_path():
    today = datetime.now().strftime('%Y%m%d')
    log_base = os.getenv("LOG_BASE_DIR", "/log")
    log_dir = os.path.join(log_base, today)
    
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, f"{today}_send_report_by_keyword_to_user.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(get_log_path())
    ]
)

def run_job():
    logging.info("--- Keyword Alert Job Start ---")
    try:
        # RUN_ONCE=true로 설정하여 1회 실행 후 종료되게 함
        env = os.environ.copy()
        env["RUN_ONCE"] = "true"
        
        result = subprocess.run(
            ["uv", "run", "send_report_by_keyword_to_user.py"],
            env=env,
            check=False
        )
        if result.returncode != 0:
            logging.error(f"Job process exited with error code {result.returncode}")
    except Exception as e:
        logging.error(f"Execution Error: {e}")
    logging.info("--- Keyword Alert Job End ---")

scheduler = BlockingScheduler()

# 5분마다 실행 (*/5 * * * *)
scheduler.add_job(
    run_job,
    CronTrigger(minute='*/5'),
    id="keyword_alert_job"
)

if __name__ == "__main__":
    logging.info("🚀 Keyword Alert Scheduler starting up...")
    logging.info(f"Registered Jobs: {scheduler.get_jobs()}")
    
    # 시작할 때 한 번 즉시 실행하고 싶으면 아래 주석을 해제하세요.
    # run_job()
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logging.info("Scheduler stopped.")
