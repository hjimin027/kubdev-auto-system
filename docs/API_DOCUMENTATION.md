# KubeDev Auto System - API 문서

## 📋 개요

K8s 기반 자동 개발 환경 프로비저닝 시스템의 백엔드 API 문서입니다.

**기본 URL**: `http://localhost:8000/api/v1`

## 🔐 인증

모든 API 엔드포인트는 Bearer 토큰 인증을 사용합니다.

```bash
Authorization: Bearer <your-jwt-token>
```

### 로그인
```bash
POST /auth/login
{
  "email": "user@example.com",
  "password": "password123"
}
```

## 🚀 환경 관리 API

### 1. 새 환경 생성
```bash
POST /environments/
{
  "name": "My React Project",
  "template_id": 1,
  "git_repository": "https://github.com/user/project.git",
  "git_branch": "main",
  "expires_at": "2024-12-31T23:59:59Z"
}
```

**자동 수행 작업**:
- ✅ K8s Namespace 생성
- ✅ **ResourceQuota 자동 생성** (CPU: 1core, Memory: 2GB, Pod: 5개 제한)
- ✅ Deployment, Service, Ingress 생성
- ✅ Git 저장소 자동 클론 (Init Container)
- ✅ 웹 IDE (VS Code Server) 배포

### 2. 환경 목록 조회
```bash
GET /environments/
GET /environments/?status=running&user_id=1
```

### 3. 환경 제어
```bash
POST /environments/{id}/actions
{
  "action": "start"  // start, stop, restart, delete
}
```

### 4. 환경 로그 조회
```bash
GET /environments/{id}/logs?tail_lines=100
```

### 5. 환경 접속 정보
```bash
GET /environments/{id}/access-info
```

**응답 예시**:
```json
{
  "environment_id": 1,
  "access_url": "http://env-my-react-project.kubdev.local",
  "status": "running",
  "ports": [8080]
}
```

## 📋 템플릿 관리 API

### 1. 템플릿 생성
```bash
POST /templates/
{
  "name": "React + TypeScript Starter",
  "description": "React 18 + TypeScript + Vite 개발환경",
  "base_image": "codercom/code-server:latest",
  "stack_config": {
    "language": "javascript",
    "framework": "react",
    "version": "18"
  },
  "dependencies": ["nodejs", "npm", "git"],
  "resource_limits": {
    "cpu": "1000m",
    "memory": "2Gi",
    "storage": "10Gi"
  },
  "exposed_ports": [3000, 8080],
  "environment_variables": {
    "NODE_ENV": "development"
  }
}
```

### 2. 템플릿 목록
```bash
GET /templates/?status=active&organization_id=1
```

### 3. 템플릿 유효성 검증
```bash
POST /templates/{id}/validate
```

### 4. 템플릿 배포 테스트
```bash
POST /templates/{id}/test-deploy?timeout_seconds=300
```

## 📊 모니터링 API

### 1. 실시간 클러스터 현황
```bash
GET /admin/overview
```

**응답 예시**:
```json
{
  "cluster_overview": {
    "cluster_info": {
      "total_nodes": 3,
      "ready_nodes": 3,
      "total_pods": 25,
      "running_pods": 23
    },
    "kubdev_info": {
      "total_environments": 8,
      "active_environments": 6,
      "pending_environments": 2,
      "failed_environments": 0
    }
  }
}
```

### 2. 모든 환경 상태 조회 (Admin)
```bash
GET /admin/environments
```

**🎯 핵심 기능**: K8s에서 **실시간 상태**를 조회하여 다음 정보 제공:
- Pod 상태 (Running/Pending/Failed)
- **ResourceQuota 사용률** (CPU 65%, Memory 78% 등)
- 네임스페이스별 리소스 현황
- 컨테이너 Ready 상태

### 3. 특정 네임스페이스 상세 정보
```bash
GET /admin/namespace/{namespace}
```

### 4. 사용자별 환경 현황
```bash
GET /monitoring/user/{user_id}/environments
```

### 5. 리소스 메트릭 조회
```bash
GET /monitoring/environments/{id}/metrics?hours=24
```

### 6. 시스템 알림
```bash
GET /admin/alerts
```

**알림 예시**:
```json
{
  "alerts": [
    {
      "type": "warning",
      "category": "high_resource_usage",
      "message": "High CPU usage in namespace 'lisa-project-a'",
      "cpu_usage": "85%",
      "memory_usage": "72%"
    }
  ]
}
```

## 👤 Admin 대시보드 API

### 1. 전체 현황 요약
```bash
GET /admin/overview
```

### 2. 사용자 활동 현황
```bash
GET /admin/users-activity?limit=50
```

### 3. 템플릿 사용 통계
```bash
GET /admin/templates-usage
```

### 4. 만료된 환경 정리
```bash
POST /admin/cleanup/expired?dry_run=true
```

## 🔧 권한 관리

### 역할 체계
- **super_admin**: 모든 권한
- **org_admin**: 조직 내 모든 관리
- **team_leader**: 팀 내 환경 관리
- **developer**: 본인 환경만 관리

### API 키 생성
```bash
POST /auth/api-keys
{
  "description": "CI/CD 파이프라인용 API 키"
}
```

## 🚀 자동화 플로우 예시

### 신입 개발자 온보딩 시나리오

1. **Admin**: 템플릿 생성
```bash
POST /templates/
# "React 개발환경" 템플릿 생성
```

2. **신입 개발자**: 환경 생성 요청
```bash
POST /environments/
{
  "name": "Lisa의 첫 프로젝트",
  "template_id": 1,
  "git_repository": "https://github.com/company/onboarding-project"
}
```

3. **백엔드 자동 처리**:
   - ✅ `lisa-project-a` Namespace 생성
   - ✅ **ResourceQuota 자동 적용** (CPU 1개, 메모리 2GB 제한)
   - ✅ Init Container가 Git 저장소 클론
   - ✅ VS Code Server 컨테이너 시작
   - ✅ Ingress로 외부 접속 URL 생성

4. **결과**:
   - Lisa는 `http://env-lisa-project-a.kubdev.local`로 즉시 접속
   - 웹 브라우저에서 VS Code 사용
   - 프로젝트 코드 미리 로드됨

5. **Admin 모니터링**:
```bash
GET /admin/environments
# Lisa의 환경 상태 실시간 확인
# CPU 사용률: 45%, 메모리: 68% 등
```

## 🔍 K8s 자동화 확인 방법

### kubectl 명령어로 확인
```bash
# 1. 환경 생성 전
kubectl get namespaces
# lisa-project-a 없음

# 2. 환경 생성 후
kubectl get namespaces
# lisa-project-a Active

kubectl get all -n lisa-project-a
# Deployment, Service, Pod 모두 Running

kubectl get resourcequota -n lisa-project-a
# CPU 1개, 메모리 2GB 제한 적용됨
```

### K8s 대시보드 (Lens) 확인
- Lens 연결 후 실시간으로 Namespace 생성 과정 시각적 확인
- Pod 상태 변화: Pending → ContainerCreating → Running
- ResourceQuota 제한 실시간 모니터링

## 📈 자원 관리 핵심 기능

### 1. 예방적 관리 (ResourceQuota)
- **자동 생성**: 환경 생성시 ResourceQuota 자동 적용
- **과부하 방지**: 무한루프 코드 실행해도 CPU 1개로 제한
- **멀티테넌트**: 사용자별 독립된 리소스 할당량

### 2. 실시간 모니터링
- **K8s API 연동**: `kubectl get` 동급의 실시간 데이터
- **사용률 추적**: CPU 65%, 메모리 78% 등 정확한 수치
- **알림 시스템**: 임계값 초과시 자동 알림

### 3. Admin 대시보드
- **통합 모니터링**: 모든 환경 상태 한눈에 확인
- **리소스 효율화**: 비효율적 사용 패턴 식별
- **자동 정리**: 만료된 환경 자동 삭제

이 시스템은 **백엔드 자체가 자원 관리자**로 동작하며, Admin 대시보드는 이를 **조종하는 조종석** 역할을 합니다.