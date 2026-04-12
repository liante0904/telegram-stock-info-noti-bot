import asyncio
import time
from datetime import datetime
from loguru import logger
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from modules.eugenefn_12 import eugene_checkNewArticle

async def session_test_loop(interval_minutes=30):
    logger.info(f"유진투자증권 세션 유지 테스트 시작 (주기: {interval_minutes}분)")
    
    while True:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"[{now}] 세션 체크 중...")
        
        try:
            # eugene_checkNewArticle 내부에 이미 로그인 여부 체크 로직이 포함되어 있습니다.
            articles = await eugene_checkNewArticle()
            if len(articles) > 0:
                logger.success(f"[{now}] 세션 유지 중! (가져온 기사 수: {len(articles)})")
            else:
                logger.warning(f"[{now}] 기사를 가져오지 못했습니다. 세션 만료 가능성이 있습니다.")
        except Exception as e:
            logger.error(f"[{now}] 테스트 중 오류 발생: {e}")
        
        logger.info(f"{interval_minutes}분 대기 후 재시도합니다...")
        # 테스트를 위해 30분 대기 (사용자가 직접 실행하여 확인)
        await asyncio.sleep(interval_minutes * 60)

if __name__ == "__main__":
    try:
        asyncio.run(session_test_loop(30))
    except KeyboardInterrupt:
        logger.info("테스트를 종료합니다.")
