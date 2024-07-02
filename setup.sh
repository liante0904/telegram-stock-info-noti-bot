#!/bin/bash

PROJECT_DIR=~/dev/telegram-stock-info-noti-bot

echo "Running setup.sh in $PROJECT_DIR..."

# 파이썬 패키지 설치를 위한 가상 환경 생성 및 활성화
cd $PROJECT_DIR
python3 -m venv venv
source venv/bin/activate

# setuptools와 wheel 설치
pip install --upgrade pip
pip install setuptools wheel

# 나머지 패키지 설치
pip install -r requirements.txt

echo "Setup completed in $PROJECT_DIR."
