# 1. Base Image
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1

# 2. 필수 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    wget \
    libaio1t64 \
    ca-certificates \
    rclone \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# 3. uv 설치
RUN pip install uv

# 4. Create a non-root user and group
RUN groupadd --gid 1001 appgroup && useradd --uid 1001 --gid 1001 --shell /bin/bash --create-home appuser

# 5. 작업 디렉토리 설정
WORKDIR /app

# 6. 의존성 설치 (캐시 활용)
# 소유권을 appuser로 지정하여 파일 복사
COPY --chown=appuser:appgroup pyproject.toml uv.lock ./ 
RUN uv sync --frozen --no-cache

# 7. 필요한 소스 코드 복사
COPY --chown=appuser:appgroup run/ ./run/
COPY --chown=appuser:appgroup models/ ./models/
COPY --chown=appuser:appgroup utils/ ./utils/
COPY --chown=appuser:appgroup modules/ ./modules/
COPY --chown=appuser:appgroup *.py ./
# COPY .env ./ # .env는 docker-compose의 env_file을 통해 주입됩니다.

# 8. 실행 권한 부여 및 디렉토리 준비
RUN mkdir -p /log && chown -R appuser:appgroup /log

# 9. Switch to the non-root user
USER appuser

# 10. 기본 실행 명령 (스케줄러 실행)
CMD ["uv", "run", "scheduler.py"]
