# KubeDev Auto System - Makefile

.PHONY: help install dev build test clean deploy k8s-deploy

# 기본 도움말
help:
	@echo "KubeDev Auto System - Available commands:"
	@echo ""
	@echo "Development:"
	@echo "  install     - Install Python dependencies"
	@echo "  dev         - Start development environment with docker-compose"
	@echo "  dev-api     - Start only API server for development"
	@echo "  shell       - Access backend container shell"
	@echo ""
	@echo "Database:"
	@echo "  db-init     - Initialize database with Alembic"
	@echo "  db-migrate  - Create new migration"
	@echo "  db-upgrade  - Apply pending migrations"
	@echo "  db-reset    - Reset database (⚠️  destroys all data)"
	@echo ""
	@echo "Build & Deploy:"
	@echo "  build       - Build Docker images"
	@echo "  test        - Run tests"
	@echo "  k8s-deploy  - Deploy to Kubernetes cluster"
	@echo "  k8s-clean   - Clean up Kubernetes resources"
	@echo ""
	@echo "Utilities:"
	@echo "  clean       - Clean up development files"
	@echo "  logs        - Show docker-compose logs"

# 개발 환경 설정
install:
	cd backend && pip install -r requirements.txt

# 전체 개발 환경 시작
dev:
	docker-compose up -d
	@echo "✅ Development environment started!"
	@echo "📊 API Documentation: http://localhost:8000/docs"
	@echo "🗄️  Database: postgresql://kubdev:kubdev123@localhost:5432/kubdev"
	@echo "🔄 Redis: redis://localhost:6379"

# API 서버만 개발 모드로 시작
dev-api:
	cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 백엔드 컨테이너 쉘 접속
shell:
	docker-compose exec backend bash

# 데이터베이스 초기화
db-init:
	cd backend && alembic init alembic
	@echo "✅ Database migration initialized!"

# 새 마이그레이션 생성
db-migrate:
	cd backend && alembic revision --autogenerate -m "$(MESSAGE)"
	@echo "✅ Migration created: $(MESSAGE)"

# 마이그레이션 적용
db-upgrade:
	cd backend && alembic upgrade head
	@echo "✅ Database upgraded!"

# 데이터베이스 리셋
db-reset:
	@echo "⚠️  WARNING: This will destroy all data!"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ]
	docker-compose down -v
	docker-compose up -d postgres redis
	sleep 5
	$(MAKE) db-upgrade
	@echo "✅ Database reset complete!"

# Docker 이미지 빌드
build:
	docker-compose build
	@echo "✅ Docker images built!"

# 테스트 실행
test:
	cd backend && python -m pytest tests/ -v
	@echo "✅ Tests completed!"

# K8s 클러스터에 배포
k8s-deploy:
	@echo "🚀 Deploying to Kubernetes..."
	kubectl apply -f k8s/rbac/rbac.yaml
	kubectl apply -f k8s/configmaps/app-config.yaml
	kubectl apply -f k8s/deployments/database-deployment.yaml
	kubectl apply -f k8s/deployments/redis-deployment.yaml
	sleep 30  # 데이터베이스가 준비될 때까지 대기
	kubectl apply -f k8s/deployments/backend-deployment.yaml
	@echo "✅ Deployment complete!"
	@echo "🔍 Check status: kubectl get pods -n kubdev"

# K8s 리소스 정리
k8s-clean:
	@echo "🧹 Cleaning up Kubernetes resources..."
	kubectl delete -f k8s/deployments/ --ignore-not-found=true
	kubectl delete -f k8s/configmaps/ --ignore-not-found=true
	kubectl delete namespace kubdev --ignore-not-found=true
	@echo "✅ Cleanup complete!"

# 개발 파일 정리
clean:
	docker-compose down -v
	docker system prune -f
	find . -type d -name "__pycache__" -delete
	find . -name "*.pyc" -delete
	@echo "✅ Cleanup complete!"

# 로그 확인
logs:
	docker-compose logs -f

# 프로덕션 환경 체크
check-prod:
	@echo "🔍 Production readiness check:"
	@echo "  ✅ Database migrations"
	@echo "  ✅ Docker images"
	@echo "  ✅ K8s manifests"
	@echo "  ⚠️  Update secrets in k8s/configmaps/app-config.yaml"
	@echo "  ⚠️  Set proper resource limits"
	@echo "  ⚠️  Configure ingress domain"

# 로컬 K8s 클러스터 (minikube) 설정
minikube-setup:
	minikube start --cpus=4 --memory=8192
	minikube addons enable ingress
	minikube addons enable metrics-server
	@echo "✅ Minikube cluster ready!"
	@echo "🔗 Use: minikube tunnel (in another terminal)"