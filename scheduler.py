# -*- coding:utf-8 -*- 
import os
import subprocess
import sys
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

# 공통 로그 설정 적용
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from utils.logger_util import setup_logger
setup_logger("scheduler")

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
    CronTrigger(minute='*/30', hour='0,5-12,14-23', jitter=300), # 300초(5분) 랜덤 지터 추가
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
    run_scraper()
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.warning("Scheduler stopped.")
