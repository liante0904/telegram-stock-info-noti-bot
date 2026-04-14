import os
import sys
from loguru import logger
from datetime import datetime

def setup_logger(log_name="scraper"):
    """
    서비스 전체의 로깅 설정을 초기화합니다.
    - ~/log/YYYYMMDD/YYYYMMDD_파일명.log 형식을 따름
    - 매일 자정 로테이션 및 ZIP 압축
    - 30일 경과 로그 자동 삭제
    """
    # Loguru의 동적 경로 기능을 활용 (날짜별 폴더 자동 생성)
    # {time:YYYYMMDD} 패턴을 사용하여 ~/log/20240414/20240414_scraper.log 형태 구현
    log_format_path = os.path.expanduser("~/log/{time:YYYYMMDD}/{time:YYYYMMDD}_" + log_name + ".log")

    # 기존 핸들러 제거 (중복 방지)
    logger.remove()

    # 1. 콘솔 출력 설정
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )

    # 2. 파일 출력 및 자동 관리 설정 (사용자 규칙 적용)
    logger.add(
        log_format_path,
        rotation="00:00",      # 매일 자정에 새 파일(및 새 폴더) 생성
        retention="30 days",   # 30일치 로그만 보관
        compression="zip",     # 지난 로그는 ZIP으로 압축
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        encoding="utf-8"
    )

    logger.info(f"Logger initialized with user rule. Logs: ~/log/YYYYMMDD/YYYYMMDD_{log_name}.log")
    return logger

# 싱글톤 패턴처럼 사용할 수 있도록 기본 초기화
if __name__ == "__main__":
    setup_logger("test")
    logger.info("Logging system test.")
