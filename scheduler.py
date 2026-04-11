# -*- coding:utf-8 -*- 
import os
import subprocess
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
import sys

# 1. 로그 설정 (scraper.py 스타일 참조)
logger.remove()

HOME_PATH = os.path.expanduser("~")
# 환경 변수 LOG_BASE_DIR이 있으면 사용, 없으면 ~/log 사용
log_base = os.getenv("LOG_BASE_DIR", os.path.join(HOME_PATH, "log"))
today = datetime.now().strftime('%Y%m%d')
log_dir = os.path.join(log_base, today)
os.makedirs(log_dir, exist_ok=True)

LOG_FORMAT = "<green>{time:YYYY-MM-DD HH:mm:ss.SS}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>"
FILE_FORMAT = "{time:YYYY-MM-DD HH:mm:ss.SS} | {level: <8} | {message}"

logger.add(sys.stdout, format=LOG_FORMAT, level="INFO", colorize=True)
logger.add(os.path.join(log_dir, f"{today}_scheduler.log"), format=FILE_FORMAT, level="INFO", rotation="10 MB", retention="30 days", encoding="utf-8")

def run_scraper():
    """메인 스크래퍼 실행 (scraper.py)"""
    logger.info("--- [Job Start] Main Scraper (scraper.py) ---")
    try:
        # uv run scraper.py 실행
        result = subprocess.run(
            ["uv", "run", "scraper.py"],
            check=False
        )
        if result.returncode != 0:
            logger.error(f"Scraper process exited with error code {result.returncode}")
        else:
            logger.success("Scraper job completed successfully.")
    except Exception as e:
        logger.error(f"Execution Error: {e}")
    logger.info("--- [Job End] Main Scraper ---")

def run_ai_summary(limit):
    """AI 요약 배치 실행 (현재 미사용 - 주석 처리용)"""
    logger.info(f"--- AI Summary Batch Start (Limit: {limit}) ---")
    try:
        result = subprocess.run(
            ["uv", "run", "run/gemini_summary_batch.py", str(limit)],
            check=False
        )
        if result.returncode != 0:
            logger.error(f"Batch process exited with error code {result.returncode}")
    except Exception as e:
        logger.error(f"Execution Error: {e}")
    logger.info("--- AI Summary Batch End ---")

scheduler = BlockingScheduler()

# [스케줄 1] 메인 스크래퍼: */30 0,5-12,14-23 * * * (기존 crontab 복제)
scheduler.add_job(
    run_scraper,
    CronTrigger(minute='*/30', hour='0,5-12,14-23'),
    id="main_scraper_job"
)

# [스케줄 2] AI 요약: 일단 주석 처리 (필요 시 해제)
"""
scheduler.add_job(
    run_ai_summary,
    CronTrigger(minute='15,45', hour='0,5-12,13,14-23'),
    args=[20],
    id="summary_batch_20"
)

scheduler.add_job(
    run_ai_summary,
    CronTrigger(minute='0,15,30,45', hour='1-4'),
    args=[30],
    id="summary_batch_30"
)
"""

if __name__ == "__main__":
    logger.info("🚀 Master Scheduler starting up...")
    logger.info("Registered Jobs:")
    for job in scheduler.get_jobs():
        logger.info(f"- {job.id}: {job.trigger}")
    
    # 시작 시 즉시 한 번 실행하려면 아래 주석 해제
    # run_scraper()
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.warning("Scheduler stopped.")
