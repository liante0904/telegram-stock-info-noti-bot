#!/bin/bash

PROJECT_DIR=~/dev/telegram-stock-info-noti-bot

echo "Running setup.sh in $PROJECT_DIR..."

# 필수 시스템 패키지 설치
echo "Installing required system packages..."
sudo apt update
sudo apt install -y libsystemd-dev libdbus-1-dev libgirepository1.0-dev libcairo2-dev libgirepository1.0-dev gir1.2-gtk-3.0

# 파이썬 패키지 설치를 위한 가상 환경 생성 및 활성화
cd $PROJECT_DIR
python3 -m venv venv
source venv/bin/activate

# setuptools와 wheel, Cython 설치
pip install --upgrade pip
pip install --upgrade setuptools wheel Cython

# pycairo 설치
pip install pycairo

# 나머지 패키지 설치
pip install --no-build-isolation -r requirements.txt

echo "Setup completed in $PROJECT_DIR."
 