#!/bin/bash
echo "==========================runPy.sh=========================="

# pyenv와 pyenv-virtualenv 초기화
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init --path)"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

# 프로젝트명 변수로 정의
PROJECT_NAME="telegram-stock-info-bot"

# 파라미터를 변수에 담기
S1="$1"
S2="$2"
S3="$3"

HOME_DIR=$HOME
DATE=$(date +"%Y%m%d")

# 로그 디렉토리 경로 설정
LOG_DIR="${HOME_DIR}/log/${DATE}"

# 로그 디렉토리가 존재하지 않으면 생성
if [ ! -d "$LOG_DIR" ]; then
  echo "=====로그 디렉토리 생성====="
  mkdir -p "$LOG_DIR"
fi

# 변수 출력
echo "S1 변수의 값: $S1"
echo "S2 변수의 값: $S2"
echo "S3 변수의 값: $S3"

# S1에 .py가 있는지 확인하고 없으면 추가
if [ "${S1##*.}" != "py" ]; then
  SCRIPT_NAME="${S1}.py"  # S1에 .py가 없으면 .py를 추가
else
  SCRIPT_NAME="$S1"       # S1에 .py가 있으면 그대로 사용
  S1="${S1%.py}"          # S1에서 .py를 제거한 값을 S1에 저장
fi


# .py 붙여주는 기존 로직 전에 간단히 분기
if [[ "$S1" == "make_us_excel_quant.py" ]]; then
  if pgrep -f "make_us_excel_quant.py" > /dev/null; then
    echo "이미 실행 중입니다. (make_us_excel_quant.py) 중복 실행 방지"
    exit 0
  fi
fi

echo "=====프로젝트 경로 이동===="
cd "${HOME_DIR}/dev/${PROJECT_NAME}" || { echo "디렉토리 이동 실패"; exit 1; }

# 파이썬 가상환경 활성화
echo "=====파이썬 가상환경 활성화===="
pyenv activate "pyenv" || { echo "가상환경 활성화 실패"; exit 1; }

echo "=========파이썬 스크립트 실행========="
python3 "${SCRIPT_NAME}" >> "${LOG_DIR}/${DATE}_${S1}.log" 2>&1 || { echo "파이썬 스크립트 실행 실패"; exit 1; }

# 가상환경 비활성화
pyenv deactivate || { echo "가상환경 비활성화 실패"; exit 1; }

echo "==========================완료=========================="
