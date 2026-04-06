# 1. Base Image
FROM python:3.12-slim

# 2. 필수 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    wget \
    libaio1t64 \
    ca-certificates \
    rclone \
    && rm -rf /var/lib/apt/lists/*

# 3. uv 설치
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 4. 작업 디렉토리 설정
WORKDIR /app

# 5. 의존성 설치 (캐시 활용)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache

# 6. 필요한 소스 코드 복사
COPY run/ ./run/
COPY models/ ./models/
COPY utils/ ./utils/
COPY modules/ ./modules/
COPY *.py ./
# COPY .env ./ # .env는 docker-compose의 env_file을 통해 주입됩니다.

# 7. 실행 권한 부여 및 디렉토리 준비
RUN mkdir -p /log

# 8. 기본 실행 명령 (스케줄러 실행)
CMD ["uv", "run", "scheduler.py"]
