SECRETS := python3 $(HOME)/secrets/generate_env.py scraper
COMPOSE  := docker compose

.PHONY: up down restart restart-scraper restart-alert logs logs-scraper logs-alert ps env

## 시크릿 재생성 + 전체 서비스 기동
up: env
	$(COMPOSE) up -d

## 전체 서비스 중단
down:
	$(COMPOSE) down

## 시크릿 재생성 + 전체 재시작
restart: env
	$(COMPOSE) restart

## 시크릿 재생성 + main-scraper만 재시작
restart-scraper: env
	$(COMPOSE) restart main-scraper

## 시크릿 재생성 + keyword-alert만 재시작
restart-alert: env
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

## .env 재생성만 (확인용)
env:
	$(SECRETS)
