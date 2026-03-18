#!/bin/bash

# 1. 경로 이동
cd /home/ubuntu/dev/docker-flask || {
  echo "Error: Failed to change directory to /home/ubuntu/dev/docker-flask"
  exit 1
}

# 2. Git 업데이트
echo "Fetching and resetting Git repository..."
git fetch --all && git reset --hard origin/master || {
  echo "Error: Failed to fetch and reset Git repository"
  exit 1
}

# 3. Docker Compose 재시작
echo "Stopping, building, and restarting Docker containers..."
docker-compose down &&
docker-compose build --no-cache &&
docker-compose up -d || {
  echo "Error: Failed to restart Docker containers"
  exit 1
}

echo "Update and restart completed successfully!"

