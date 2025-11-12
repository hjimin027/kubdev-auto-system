# KubeDev Auto System - 배포 가이드

## 🚀 Quick Start

### 1. 로컬 개발 환경 시작
```bash
# 전체 스택 실행 (PostgreSQL + Redis + Backend)
make dev

# API 문서 확인
open http://localhost:8000/docs
```

### 2. 데이터베이스 설정
```bash
# 마이그레이션 실행
make db-upgrade

# 샘플 데이터 생성 (선택사항)
make db-seed
```

### 3. K8s 클러스터 배포
```bash
# 프로덕션 배포
make k8s-deploy

# 상태 확인
kubectl get pods -n kubdev
```

## 🏗️ 아키텍처 구성

### 백엔드 컴포넌트
```
┌─────────────────────────────────────────────────────────────────┐
│                    KubeDev Backend                              │
├─────────────────────────────────────────────────────────────────┤
│ 🔐 Authentication API  │ 🚀 Environment API  │ 📋 Template API │
│ - JWT 토큰 관리         │ - 환경 생성/삭제      │ - 템플릿 CRUD    │
│ - 권한 체크            │ - K8s 자동화         │ - 유효성 검증    │
│ - API 키 생성          │ - Git 연동           │ - 배포 테스트    │
├─────────────────────────────────────────────────────────────────┤
│ 📊 Monitoring API     │ 👤 Admin API         │ ⚙️ Core Services │
│ - 실시간 메트릭        │ - 대시보드 데이터     │ - K8s 클라이언트 │
│ - 로그 수집           │ - 사용자 관리         │ - Environment    │
│ - 알림 시스템         │ - 자원 정리           │ - Security       │
└─────────────────────────────────────────────────────────────────┘
                              │
                    Kubernetes API Server
                              │
┌─────────────────────────────────────────────────────────────────┐
│                        K8s 클러스터                              │
├─────────────────────────────────────────────────────────────────┤
│ 📦 Development Namespaces                                       │
│ ├─ lisa-project-a      ├─ john-react-app    ├─ team-backend    │
│ │  ├─ ResourceQuota    │  ├─ ResourceQuota   │  ├─ ResourceQuota│
│ │  ├─ Deployment       │  ├─ Deployment      │  ├─ Deployment  │
│ │  ├─ Service          │  ├─ Service         │  ├─ Service     │
│ │  └─ Ingress          │  └─ Ingress         │  └─ Ingress     │
└─────────────────────────────────────────────────────────────────┘
```

## 🔄 자동화 플로우

### 환경 생성 자동화 (4단계)

```mermaid
sequenceDiagram
    participant User
    participant API
    participant K8s
    participant Git

    User->>API: POST /environments
    Note over API: 1. 네임스페이스 생성
    API->>K8s: create namespace "user-project-x"
    Note over API: 2. ResourceQuota 생성 ⭐
    API->>K8s: create ResourceQuota (CPU: 1, Memory: 2GB)
    Note over API: 3. Deployment 생성
    API->>K8s: create deployment with init container
    Note over K8s: 4. Git 클론 + IDE 시작
    K8s->>Git: git clone (init container)
    K8s->>K8s: start VS Code Server (main container)
    K8s-->>API: environment ready
    API-->>User: access_url
```

### ResourceQuota 자동 적용 ⭐

**핵심**: 환경 생성시 자동으로 ResourceQuota가 적용되어 **과부하를 예방**합니다.

```yaml
# 자동 생성되는 ResourceQuota
apiVersion: v1
kind: ResourceQuota
metadata:
  name: quota-user-project-x
  namespace: user-project-x
spec:
  hard:
    limits.cpu: "1"        # CPU 1개 제한
    limits.memory: "2Gi"   # 메모리 2GB 제한
    pods: "5"              # Pod 5개 제한
    services: "5"          # Service 5개 제한
```

**효과**: 사용자가 실수로 무한루프를 돌려도 CPU 사용량이 1개를 초과할 수 없습니다.

## 📊 실시간 모니터링

### Admin 대시보드 데이터 조회

```python
# Backend에서 K8s 실시간 데이터 조회
k8s_service = KubernetesService()

# 1. 클러스터 전체 현황
cluster_info = await k8s_service.get_cluster_overview()

# 2. 모든 환경 상태
environments = await k8s_service.get_all_environments_status()

# 3. ResourceQuota 사용률
for env in environments:
    quota_status = await k8s_service.get_resource_quota_status(
        namespace=env['namespace'],
        quota_name=f"quota-{env['deployment_name']}"
    )
    # CPU 사용률: 65%, 메모리 사용률: 78% 등
```

**결과**: Admin은 React 대시보드에서 **"Lisa가 현재 CPU 0.5개/1개 사용중"** 정보를 실시간으로 볼 수 있습니다.

## 🔍 자동화 확인 방법

### 1. kubectl 명령어 확인

```bash
# 환경 생성 버튼 클릭 전
kubectl get namespaces
# NAME              STATUS   AGE
# default           Active   5d
# kube-system       Active   5d

# 환경 생성 버튼 클릭 후
kubectl get namespaces
# NAME              STATUS   AGE
# default           Active   5d
# kube-system       Active   5d
# lisa-project-a    Active   10s  ⭐ 새로 생성됨

# 상세 확인
kubectl get all -n lisa-project-a
# NAME                           READY   STATUS    RESTARTS   AGE
# pod/env-lisa-project-xxx       1/1     Running   0          2m
#
# NAME                       TYPE        CLUSTER-IP     PORT(S)
# service/svc-lisa-project   ClusterIP   10.96.1.100    8080/TCP
#
# NAME                         READY   UP-TO-DATE   AVAILABLE   AGE
# deployment/env-lisa-project  1/1     1            1           2m

# ResourceQuota 확인
kubectl get resourcequota -n lisa-project-a
# NAME                    AGE   REQUEST             LIMIT
# quota-env-lisa-project  2m    cpu: 500m/1, memory: 1Gi/2Gi
```

### 2. Lens (K8s GUI) 확인

1. **Lens 실행 및 클러스터 연결**
2. **Namespaces 섹션 모니터링**
3. **[환경 생성] 버튼 클릭**
4. **실시간으로 새 Namespace 생성 확인**
5. **Pods 탭에서 Creating → Running 상태 변화 관찰**

## 🛠️ 개발환경 설정

### 필수 요구사항
- **Docker** & **Docker Compose**
- **Python 3.11+**
- **PostgreSQL 15+**
- **Redis 7+**
- **Kubernetes 클러스터** (minikube/k3s/EKS 등)

### 로컬 K8s 클러스터 (minikube)
```bash
# minikube 클러스터 시작
make minikube-setup

# 다른 터미널에서 터널링 (로컬 접속용)
minikube tunnel
```

### 환경변수 설정
```bash
# .env 파일 생성
cp backend/.env.example backend/.env

# 필요한 값들 수정
DATABASE_URL=postgresql://kubdev:password@localhost:5432/kubdev
SECRET_KEY=your-super-secret-key
KUBECONFIG_PATH=/path/to/.kube/config
```

## 📋 API 엔드포인트 요약

### 🔐 인증 API (`/api/v1/auth/`)
- `POST /login` - 로그인 & JWT 토큰 발급
- `POST /register` - 사용자 등록
- `GET /me` - 현재 사용자 정보
- `POST /api-keys` - API 키 생성

### 🚀 환경 API (`/api/v1/environments/`)
- `POST /` - **새 환경 생성** (ResourceQuota 자동 적용)
- `GET /` - 환경 목록 조회
- `POST /{id}/actions` - 환경 제어 (start/stop/restart/delete)
- `GET /{id}/logs` - 환경 로그 조회
- `GET /{id}/access-info` - 접속 정보

### 📋 템플릿 API (`/api/v1/templates/`)
- `POST /` - 템플릿 생성
- `GET /` - 템플릿 목록
- `POST /{id}/validate` - 템플릿 유효성 검증
- `POST /{id}/test-deploy` - 배포 테스트

### 📊 모니터링 API (`/api/v1/monitoring/`)
- `GET /environments/{id}/metrics` - 환경 메트릭
- `GET /user/{id}/environments` - 사용자 환경 현황
- `GET /health` - 시스템 헬스체크
- `GET /alerts` - 사용자 알림

### 👤 Admin API (`/api/v1/admin/`)
- `GET /overview` - **클러스터 전체 현황**
- `GET /environments` - **모든 환경 실시간 상태** ⭐
- `GET /namespace/{namespace}` - 네임스페이스 상세 정보
- `GET /resource-usage` - 리소스 사용량 요약
- `POST /cleanup/expired` - 만료된 환경 정리

## 🔧 운영 도구

### Makefile 명령어
```bash
make help           # 도움말
make dev            # 개발환경 시작
make db-upgrade     # DB 마이그레이션
make build          # Docker 빌드
make test           # 테스트 실행
make k8s-deploy     # K8s 배포
make k8s-clean      # K8s 리소스 정리
make logs           # 로그 확인
```

### Docker Compose 서비스
```bash
# 개별 서비스 제어
docker-compose up postgres      # DB만 시작
docker-compose up backend       # API만 시작
docker-compose logs -f backend  # 백엔드 로그
```

## 🔒 보안 고려사항

### 1. 인증 & 권한
- **JWT 토큰**: 15분 만료 (설정 가능)
- **API 키**: 장기간 사용 (CI/CD용)
- **역할 기반 접근제어**: super_admin > org_admin > team_leader > developer

### 2. K8s 보안
- **ServiceAccount**: 최소 권한 원칙
- **RBAC**: 네임스페이스별 권한 분리
- **NetworkPolicy**: 네트워크 격리 (선택사항)

### 3. 데이터 보안
- **비밀번호 해싱**: bcrypt
- **민감정보 마스킹**: 로그에서 비밀번호/API키 숨김
- **환경변수**: Secret으로 K8s 배포

## 📈 성능 및 확장성

### 리소스 사용량
- **백엔드 컨테이너**: CPU 0.5개, 메모리 1GB
- **PostgreSQL**: CPU 0.25개, 메모리 512MB
- **Redis**: CPU 0.1개, 메모리 256MB

### 확장성
- **수평 확장**: 백엔드 Pod 복제 가능
- **DB 연결풀**: 최대 20개 연결
- **K8s API**: 레이트 리미팅 적용

## 🚨 문제 해결

### 일반적인 문제들

1. **K8s 연결 실패**
```bash
# kubeconfig 확인
kubectl cluster-info

# 권한 확인
kubectl auth can-i create pods --namespace=kubdev
```

2. **환경 생성 실패**
```bash
# 로그 확인
kubectl logs -n kubdev -l app=kubdev-backend

# 이벤트 확인
kubectl get events -n kubdev --sort-by='.lastTimestamp'
```

3. **ResourceQuota 오류**
```bash
# 할당량 확인
kubectl describe resourcequota -n user-project-x

# 사용량 확인
kubectl top pods -n user-project-x
```

이 시스템은 **백엔드 로직 자체가 자원 관리자**로 동작하며, K8s를 통해 **예방적 자원 관리**와 **실시간 모니터링**을 제공합니다.