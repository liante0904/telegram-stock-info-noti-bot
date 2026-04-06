#!/bin/bash
set -e

echo "1. Docker GPG 키 등록 중..."
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor --yes -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "2. Docker 저장소 추가 중..."
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

echo "3. 패키지 리스트 업데이트 및 Docker Compose Plugin 설치 중..."
sudo apt-get update
sudo apt-get install -y docker-compose-plugin

echo "4. 설치 확인..."
docker compose version
