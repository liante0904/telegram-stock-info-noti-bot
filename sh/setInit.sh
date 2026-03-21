#!/bin/bash
# 현재 스크립트 위치 기준으로 프로젝트 루트 찾기
SH_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SH_DIR/.." && pwd )"

# 프로젝트 루트에서 .pdf 파일 정리
cd "$PROJECT_ROOT" || exit
rm -f *.pdf

# 로그 디렉토리 생성
mkdir -p "$HOME/log/$(date +'%Y%m%d')"

# 현재 스크립트들이 있는 폴더 권한 부여
chmod 755 "$SH_DIR"/*.sh



