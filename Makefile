SECRETS_SCRIPT := python3 $(HOME)/secrets/generate_env.py
COMPOSE        := docker compose

.PHONY: up down build restart restart-scraper restart-alert logs logs-scraper logs-alert ps env env-scraper env-alert env-api test lint

## 전체 서비스 기동 (빌드 포함, 환경 변수 갱신)
up: env build
	$(COMPOSE) up -d

## 전체 서비스 중단
down:
	$(COMPOSE) down

## 이미지 빌드
build:
	$(COMPOSE) build

## 전체 재시작
restart: env build
	$(COMPOSE) restart

## 서비스별 시크릿 갱신 및 빌드 후 재시작
restart-scraper: env-scraper
	$(COMPOSE) up -d --build main-scraper

restart-alert: env-alert
	$(COMPOSE) up -d --build report-keyword-alert

## 전체 로그 (follow)
logs:
	$(COMPOSE) logs -f

logs-scraper:
	$(COMPOSE) logs -f main-scraper

logs-alert:
	$(COMPOSE) logs -f report-keyword-alert

## 컨테이너 상태 확인
ps:
	$(COMPOSE) ps

## 테스트 실행 (표준 인터페이스)
test:
	uv run pytest tests/test_scrapers_health.py -v

## 린트 체크 (표준 인터페이스)
lint:
	uv run ruff check .

## 전체 환경 변수 생성
env:
	$(SECRETS_SCRIPT)

## 서비스별 환경 변수 생성 분리
env-scraper:
	$(SECRETS_SCRIPT) scraper

env-alert:
	$(SECRETS_SCRIPT) scraper

env-api:
	$(SECRETS_SCRIPT) api
