# 1. Base Image (Python 3.12)
FROM python:3.12-slim

# 2. 시스템 의존성 설치 (wget, Chrome, Oracle Client 관련 라이브러리)
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

# 3. uv 설치 (고성능 파이썬 패키지 관리자)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 4. 작업 디렉토리 설정
WORKDIR /app

# 5. 의존성 설치 (캐시 최적화를 위해 먼저 수행)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache

# 6. 소스 코드 복사
COPY . .

# 7. 실행 권한 부여 및 로그 디렉토리 생성
RUN mkdir -p /app/logs

# 기본 실행 명령 (추후 docker-compose에서 덮어쓸 수 있음)
CMD ["uv", "run", "scheduler.py"]
