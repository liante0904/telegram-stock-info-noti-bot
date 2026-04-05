import os
import subprocess
import logging
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# 로그 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"/app/logs/scheduler_{datetime.now().strftime('%Y%m%d')}.log")
    ]
)

def run_job(limit):
    logging.info(f"--- AI Summary Batch Start (Limit: {limit}) ---")
    try:
        # capture_output=True를 제거하여 실시간으로 stdout/stderr가 출력되게 함
        # 이렇게 하면 docker logs -f에서 바로 확인 가능합니다.
        result = subprocess.run(
            ["uv", "run", "run/gemini_summary_batch.py", str(limit)],
            check=False
        )
        if result.returncode != 0:
            logging.error(f"Batch process exited with error code {result.returncode}")
    except Exception as e:
        logging.error(f"Execution Error: {e}")
    logging.info("--- AI Summary Batch End ---")

scheduler = BlockingScheduler()

# 스케줄 1: 15,45 0,5-12,13,14-23 * * * (Limit 20)
scheduler.add_job(
    run_job,
    CronTrigger(minute='15,45', hour='0,5-12,13,14-23'),
    args=[20],
    id="summary_batch_20"
)

# 스케줄 2: 0,15,30,45 1-4 * * * (Limit 30)
scheduler.add_job(
    run_job,
    CronTrigger(minute='0,15,30,45', hour='1-4'),
    args=[30],
    id="summary_batch_30"
)

if __name__ == "__main__":
    logging.info("🚀 Scheduler starting up...")
    logging.info("Registered Jobs:")
    for job in scheduler.get_jobs():
        logging.info(f"- {job.id}: {job.trigger}")
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logging.info("Scheduler stopped.")
