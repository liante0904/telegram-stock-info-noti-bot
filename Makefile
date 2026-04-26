SECRETS_SCRIPT := python3 $(HOME)/secrets/generate_env.py
COMPOSE        := docker compose

.PHONY: up down restart restart-scraper restart-alert logs logs-scraper logs-alert ps env env-scraper env-alert env-api

## 전체 서비스 기동 (모든 환경 변수 갱신)
up: env
	$(COMPOSE) up -d

## 전체 서비스 중단
down:
	$(COMPOSE) down

## 전체 재시작
restart: env
	$(COMPOSE) restart

## 서비스별 시크릿 갱신 후 재시작
restart-scraper: env-scraper
	$(COMPOSE) restart main-scraper

restart-alert: env-alert
	$(COMPOSE) restart report-keyword-alert

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

## 전체 환경 변수 생성 (architecture.md 원칙 준수)
env:
	$(SECRETS_SCRIPT)

## 서비스별 환경 변수 생성 분리
env-scraper:
	$(SECRETS_SCRIPT) scraper

env-alert:
	$(SECRETS_SCRIPT) scraper

env-api:
	$(SECRETS_SCRIPT) api
