import os
import json
from loguru import logger

class ConfigManager:
    _instance = None
    _secrets = {}
    _env = 'prod'

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        # 1. 환경변수 ENV (dev or prod) 확인
        raw_env = os.getenv('ENV', 'prod').lower()
        if 'dev' in raw_env:
            self._env = 'dev'
        else:
            self._env = 'prod'

        # 2. 외부 JSON 로드
        secrets_path = os.path.expanduser("~/secrets/ssh-reports-scraper/secrets.json")
        try:
            if os.path.exists(secrets_path):
                with open(secrets_path, 'r', encoding='utf-8') as f:
                    self._secrets = json.load(f)
                # logger는 설정에 따라 지연 로딩될 수 있으므로 직접 출력
                # print(f"ConfigManager: Loaded secrets for environment: {self._env}")
            else:
                self._secrets = {"common": {}, "dev": {}, "prod": {}}
        except Exception as e:
            self._secrets = {"common": {}, "dev": {}, "prod": {}}

    @property
    def ENV(self):
        return self._env

    @property
    def DB_PATH(self):
        # 1순위: 환경변수 SQLITE_DB_PATH
        env_path = os.getenv('SQLITE_DB_PATH')
        if env_path: return os.path.expanduser(env_path)
        
        # 2순위: 환경별 전용 DB_PATH (dev -> telegram_dev.db / prod -> telegram.db)
        env_secrets = self._secrets.get(self._env, {})
        path = env_secrets.get("DB_PATH")
        
        if not path:
            # 3순위: 공통 설정 (common -> SQLITE_DB_PATH)
            path = self._secrets.get("common", {}).get("SQLITE_DB_PATH")
            
        return os.path.expanduser(path or "~/sqlite3/telegram.db")

    @property
    def BOT_TOKEN(self):
        return self._secrets.get(self._env, {}).get("BOT_TOKEN") or self._secrets.get("common", {}).get("TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET")

    @property
    def CHANNEL_ID(self):
        return self._secrets.get(self._env, {}).get("CHANNEL_ID") or self._secrets.get("common", {}).get("TELEGRAM_CHANNEL_ID_REPORT_ALARM")

    def get_secret(self, key, default=None):
        """특정 환경 변수 또는 공통 변수를 가져옵니다."""
        val = os.getenv(key)
        if val: return val
        return self._secrets.get("common", {}).get(key, default)

# 싱글톤 인스턴스
config = ConfigManager()

if __name__ == "__main__":
    # 디버깅 출력 추가
    # print(f"Raw Secrets Dev: {config._secrets.get('dev')}")
    print(f"Current ENV: {config.ENV}")
    print(f"DB Path: {config.DB_PATH}")
    print(f"Token (First 5): {str(config.BOT_TOKEN)[:5]}...")
