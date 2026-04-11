import os
import requests
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

def send_n8n_webhook(payload: dict, webhook_url: str = None):
    """
    n8n Webhook으로 데이터를 발송합니다.
    :param payload: 발송할 JSON 데이터 (dict)
    :param webhook_url: n8n 웹훅 URL (없으면 환경변수 N8N_WEBHOOK_URL 사용)
    """
    url = webhook_url or os.getenv('N8N_WEBHOOK_URL')
    
    if not url:
        logger.error("n8n Webhook URL is not set. Please check your .env file (N8N_WEBHOOK_URL).")
        return False

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.success(f"Successfully sent data to n8n Webhook.")
        return True
    except Exception as e:
        logger.error(f"Failed to send n8n Webhook: {e}")
        return False

def send_error_to_n8n(error_msg: str, context: str = "Scraper"):
    """
    에러 전용 n8n 웹훅 발송 유틸리티
    """
    payload = {
        "type": "error",
        "context": context,
        "message": error_msg,
        "timestamp": os.popen('date "+%Y-%m-%d %H:%M:%S"').read().strip()
    }
    return send_n8n_webhook(payload)
