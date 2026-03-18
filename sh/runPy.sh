#!/bin/bash

# 1. 프로젝트 및 로그 경로 설정
# 현재 스크립트(sh/runPy.sh) 위치 기준으로 프로젝트 루트 찾기
SH_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SH_DIR/.." && pwd )"
HOME_DIR=$HOME
DATE=$(date +"%Y%m%d")

# 로그는 기존처럼 ~/log/ 폴더를 유지하되, 없으면 생성
LOG_DIR="${HOME_DIR}/log/${DATE}"
mkdir -p "$LOG_DIR"

# 2. 파라미터 처리
PY_FILE=$1
shift # 첫 번째 인자(파일명) 제거, 나머지는 $@에 담김

# .py 확장자 체크
if [[ ! $PY_FILE == *.py ]]; then
    SCRIPT_NAME="${PY_FILE}.py"
else
    SCRIPT_NAME="$PY_FILE"
    PY_FILE="${PY_FILE%.py}"
fi

# 로그 파일명 (슬래시를 언더바로 변경하여 폴더 구조 대응)
PY_FILE_MODIFIED=$(echo "${PY_FILE}" | sed 's/\//_/g')
LOG_FILE="${LOG_DIR}/${DATE}_${PY_FILE_MODIFIED}.log"
export LOG_FILE

# 3. 환경 활성화 (pyenv 또는 venv)
# 기존 pyenv 환경 유지
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init --path)"
eval "$(pyenv init -)"

# 가상환경 활성화 (기존 경로 유지하되, 실패 시 프로젝트 내 venv 시도)
if [ -f "$(pyenv root)/versions/3.10.12/envs/pyenv/bin/activate" ]; then
    source "$(pyenv root)/versions/3.10.12/envs/pyenv/bin/activate"
elif [ -d "$PROJECT_DIR/venv" ]; then
    source "$PROJECT_DIR/venv/bin/activate"
fi

# 4. 실행
cd "$PROJECT_DIR" || exit
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting $SCRIPT_NAME with arguments: $@" >> "$LOG_FILE"

# $@를 통해 모든 인자를 파이썬에 전달
python3 "$SCRIPT_NAME" "$@" >> "$LOG_FILE" 2>&1

EXIT_CODE=$?
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Finished with exit code $EXIT_CODE" >> "$LOG_FILE"

# 활성화된 가상환경 종료
if command -v deactivate &> /dev/null; then
    deactivate
fi

exit $EXIT_CODE
