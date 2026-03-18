#!/bin/bash

# 1. 프로젝트 경로 설정 (현재 스크립트가 있는 위치 기준)
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_DIR"

# 2. 가상 환경 활성화 (존재할 경우)
if [ -d "$PROJECT_DIR/venv" ]; then
    source "$PROJECT_DIR/venv/bin/activate"
fi

# 3. 파이썬 파일명 및 인자 처리
# 첫 번째 인자는 실행할 파이썬 파일 이름 (확장자 .py 생략 가능)
PY_FILE=$1
shift # 첫 번째 인자 제거, 나머지는 파이썬 스크립트의 인자로 사용

# .py 확장자가 없으면 붙여줌
if [[ ! $PY_FILE == *.py ]]; then
    PY_FILE="${PY_FILE}.py"
fi

# 파일 존재 확인
if [ ! -f "$PY_FILE" ]; then
    echo "Error: $PY_FILE not found in $PROJECT_DIR"
    exit 1
fi

# 4. 로그 디렉토리 설정 (logs/YYYYMMDD/)
LOG_DATE=$(date +%Y%m%d)
LOG_DIR="$PROJECT_DIR/logs/$LOG_DATE"
mkdir -p "$LOG_DIR"

LOG_TIME=$(date +%H%M%S)
LOG_FILE="$LOG_DIR/${PY_FILE%.*}_${LOG_TIME}.log"

# 5. 실행 및 로그 기록
# $@는 나머지 모든 인자를 파이썬에 전달함
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting $PY_FILE with arguments: $@" >> "$LOG_FILE"
python3 "$PY_FILE" "$@" >> "$LOG_FILE" 2>&1

# 실행 결과 상태 코드 확인
EXIT_CODE=$?
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Finished $PY_FILE with exit code $EXIT_CODE" >> "$LOG_FILE"

exit $EXIT_CODE
