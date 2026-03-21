#!/bin/bash
echo "==========================runPy.sh=========================="
# 파라미터를 변수에 담기
S1="$1"
S2="$2"
S3="$3"

# 현재 스크립트(sh/runPy_back.sh) 위치 기준으로 프로젝트 루트 찾기
SH_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SH_DIR/.." && pwd )"
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

# 파이썬 가상환경 활성화
echo "=====파이썬 가상환경 활성화===="
if [ -d "$PROJECT_ROOT/venv" ]; then
    source "$PROJECT_ROOT/venv/bin/activate"
elif [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

echo "=====프로젝트 경로 이동===="
echo "cd $PROJECT_ROOT"
cd "$PROJECT_ROOT"

echo "=========파이썬 스크립트 실행========="
echo "=====>  python3 $PROJECT_ROOT/$SCRIPT_NAME $S2 >> $LOG_DIR/${DATE}_$S1.log"

# 실행시킬 파이썬 파일 넣기
python3 "$PROJECT_ROOT/$SCRIPT_NAME" "$S2" >> "$LOG_DIR/${DATE}_$S1.log" 2>&1


# 가상환경 비활성화
deactivate
