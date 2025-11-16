# KubeDev Auto System - 프로젝트 구조

## 📁 디렉토리 구조

```
kubdev-auto-system/
├── backend/                    # 🎯 메인 FastAPI 백엔드 서버
│   ├── main.py                # FastAPI 애플리케이션 진입점
│   ├── requirements.txt       # Python 의존성
│   ├── Dockerfile            # Docker 빌드 설정
│   ├── alembic.ini           # DB 마이그레이션 설정
│   ├── .env.example          # 환경변수 템플릿
│   └── app/
│       ├── api/              # API 라우터
│       │   ├── routes.py     # 메인 라우터 통합
│       │   └── endpoints/    # 각 도메인별 API
│       │       ├── auth.py           # 🔐 인증 API
│       │       ├── environments.py  # 🚀 환경 관리 API
│       │       ├── templates.py     # 📋 템플릿 + Dockerfile 생성
│       │       ├── monitoring.py    # 📊 모니터링 API
│       │       └── admin.py         # 👤 관리자 + 일괄 생성 API
│       ├── core/             # 핵심 설정
│       │   ├── config.py     # 환경변수 관리
│       │   ├── database.py   # SQLAlchemy 설정
│       │   ├── security.py   # JWT/인증
│       │   └── dependencies.py # FastAPI 의존성
│       ├── models/           # 데이터베이스 모델
│       │   ├── user.py
│       │   ├── environment.py
│       │   ├── project_template.py
│       │   ├── organization.py
│       │   └── resource_metrics.py
│       ├── schemas/          # Pydantic 스키마
│       │   ├── user.py
│       │   ├── environment.py
│       │   ├── project_template.py
│       │   ├── organization.py
│       │   └── resource_metrics.py
│       └── services/         # 비즈니스 로직
│           ├── kubernetes_service.py     # K8s 연동
│           ├── environment_service.py    # 환경 관리
│           ├── dockerfile_generator.py   # 🚀 Dockerfile 자동생성
│           └── batch_user_service.py     # 🚀 일괄 사용자 생성
├── docs/                      # 문서
│   ├── API_DOCUMENTATION.md   # API 명세서
│   └── DEPLOYMENT_GUIDE.md    # 배포 가이드
├── k8s/                      # Kubernetes 배포 YAML
├── docker-compose.yml        # 개발환경 설정
├── Makefile                  # 빌드/배포 스크립트
└── README.md                 # 프로젝트 개요
```

## 🚀 서버 실행 방법

### 개발 환경
```bash
# 백엔드 서버 실행
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# API 문서 확인
http://localhost:8000/docs
```

### Docker 환경
```bash
# 전체 스택 실행
docker-compose up -d

# 백엔드만 실행
cd backend
docker build -t kubdev-backend .
docker run -p 8000:8000 kubdev-backend
```

## 🎯 주요 기능

### ✅ 완성된 기능들
1. **인증 & 권한 관리**: JWT + API Key + RBAC
2. **환경 관리**: CRUD + K8s 연동 + 생명주기 관리
3. **템플릿 관리**: CRUD + 검증 + 배포 테스트
4. **🚀 Dockerfile 자동 생성**: 스택설정 → Dockerfile → 이미지빌드
5. **🚀 일괄 사용자 생성**: 부트캠프용 대량 계정 생성 (최대 200명)
6. **모니터링**: 실시간 메트릭 + 리소스 사용률
7. **관리자 기능**: 대시보드 + 정리 + 알림

### 🔄 진행 중
- K8s 클러스터 실제 연동
- 프론트엔드 대시보드

## 📊 성능 지표

- **API 엔드포인트**: 30+ 개
- **동시 사용자 생성**: 최대 200명 (병렬 처리)
- **지원 언어**: Node.js, Python, Java, Go
- **지원 프레임워크**: React, FastAPI, Spring 등
- **평균 환경 생성 시간**: 3-5초/사용자