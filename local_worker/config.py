# OCI 서버 설정 (SQLite용)
REMOTE_SSH_ALIAS = "oci"
REMOTE_DB_PATH = "/home/ubuntu/sqlite3/telegram.db"
# 리눅스 서버 프로젝트 경로 (SQLite 업데이트 시 DataManager 사용용)
REMOTE_PROJECT_DIR = "/home/ubuntu/dev/telegram-stock-info-noti-bot"
# 리눅스 서버 파이썬 경로
REMOTE_PYTHON_PATH = "/home/ubuntu/.pyenv/versions/pyenv/bin/python3"

# 오라클 로컬 접속 설정 (월렛 경로)
WALLET_LOCATION = "/Users/seunghoonshin/wallet"

# 로컬 설정
LOCAL_TEMP_PDF = "./temp_report.pdf"
LOCAL_TEMP_SUMMARY = "./temp_summary.txt"
OLLAMA_MODEL = "llama3.1:8b" 
OLLAMA_URL = "http://localhost:11434/api/generate"

# 요약 프롬프트 (기존 GeminiManager와 동일하게 설정)
SUMMARY_PROMPT = """당신은 금융 전문가입니다. 제공된 증권사 레포트(PDF)를 분석하여 다음 형식으로 요약해 주세요:
1. 핵심 요약 (3줄 이내)
2. 주요 포인트 (불렛 포인트)
3. 투자의견 및 목표주가 (있는 경우)
한국어로 답변해 주세요."""
