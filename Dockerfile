# 1. Base Image
FROM python:3.12-slim

# 2. 필수 시스템 패키지만 설치 (wget: PDF 다운로드용, libaio1: Oracle Client용)
RUN apt-get update && apt-get install -y \
    wget \
    libaio1 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 3. uv 설치
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 4. 작업 디렉토리 설정
WORKDIR /app

# 5. 의존성 설치 (캐시 활용)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache

# 6. 필요한 소스 코드만 복사
COPY run/ ./run/
COPY models/ ./models/
COPY utils/ ./utils/
COPY scheduler.py ./
COPY .env ./ 

# 7. 실행 권한 부여 및 디렉토리 준비
RUN mkdir -p /log

# 8. 기본 실행 명령 (스케줄러 실행)
CMD ["uv", "run", "scheduler.py"]
