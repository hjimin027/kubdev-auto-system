"""
Admin API Endpoints
관리자용 모니터링 및 관리 기능 API
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.core.database import get_session
from app.models.environment import EnvironmentInstance
from app.models.user import User
from app.models.project_template import ProjectTemplate
from app.models.organization import Organization
from app.services.kubernetes_service import KubernetesService

router = APIRouter()


@router.get("/overview")
async def get_admin_overview():
    """관리자 대시보드 전체 현황"""
    try:
        k8s_service = KubernetesService()

        # K8s 클러스터 전체 현황
        cluster_info = await k8s_service.get_cluster_overview()

        return {
            "cluster_overview": cluster_info,
            "last_updated": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get overview: {str(e)}")


@router.get("/environments")
async def get_all_environments_admin(
    status: Optional[str] = Query(None, description="Filter by status"),
    user_id: Optional[int] = Query(None, description="Filter by user"),
    namespace: Optional[str] = Query(None, description="Filter by namespace"),
    db: Session = Depends(get_session)
):
    """모든 환경의 상태 조회 (Admin용) - K8s 실시간 데이터"""
    try:
        k8s_service = KubernetesService()

        # K8s에서 실시간 환경 상태 조회
        k8s_environments = await k8s_service.get_all_environments_status()

        # 데이터베이스 환경 정보와 매칭
        db_environments = db.query(EnvironmentInstance).all()

        # 환경 정보 통합
        combined_environments = []

        for k8s_env in k8s_environments:
            # 데이터베이스에서 매칭되는 환경 찾기
            matching_db_env = None
            for db_env in db_environments:
                if db_env.k8s_namespace == k8s_env['namespace']:
                    matching_db_env = db_env
                    break

            # 필터 적용
            if status and k8s_env['status'].lower() != status.lower():
                continue
            if namespace and k8s_env['namespace'] != namespace:
                continue
            if user_id and matching_db_env and matching_db_env.user_id != user_id:
                continue

            combined_env = {
                "id": matching_db_env.id if matching_db_env else None,
                "name": matching_db_env.name if matching_db_env else k8s_env['app_label'],
                "namespace": k8s_env['namespace'],
                "pod_name": k8s_env['pod_name'],
                "status": k8s_env['status'],
                "created_at": k8s_env['created_at'],
                "node_name": k8s_env.get('node_name'),
                "pod_ip": k8s_env.get('pod_ip'),
                "resource_quota": k8s_env.get('resource_quota'),
                "containers": k8s_env.get('containers', []),
                "user_info": {
                    "id": matching_db_env.user_id if matching_db_env else None,
                    "email": matching_db_env.user.email if matching_db_env and matching_db_env.user else "unknown"
                } if matching_db_env else None,
                "template_info": {
                    "id": matching_db_env.template_id if matching_db_env else None,
                    "name": matching_db_env.template.name if matching_db_env and matching_db_env.template else "unknown"
                } if matching_db_env else None
            }

            combined_environments.append(combined_env)

        return {
            "environments": combined_environments,
            "total": len(combined_environments),
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get environments: {str(e)}")


@router.get("/namespace/{namespace}")
async def get_namespace_details_admin(namespace: str):
    """특정 네임스페이스 상세 정보 (Admin용)"""
    try:
        k8s_service = KubernetesService()

        # K8s에서 네임스페이스 상세 정보 조회
        namespace_info = await k8s_service.get_namespace_details(namespace)

        if namespace_info.get('status') == 'not_found':
            raise HTTPException(status_code=404, detail=f"Namespace '{namespace}' not found")

        return namespace_info

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get namespace details: {str(e)}")


@router.get("/resource-usage")
async def get_resource_usage_summary(
    timeframe: str = Query("1h", description="Timeframe: 1h, 6h, 24h"),
    db: Session = Depends(get_session)
):
    """전체 리소스 사용량 요약"""
    try:
        k8s_service = KubernetesService()

        # 클러스터 전체 현황
        cluster_overview = await k8s_service.get_cluster_overview()

        # 모든 KubeDev 환경의 리소스 사용량
        environments = await k8s_service.get_all_environments_status()

        # 리소스 사용량 집계
        total_cpu_usage = 0
        total_memory_usage = 0
        total_environments = len(environments)
        active_environments = sum(1 for env in environments if env['status'] == 'Running')

        # ResourceQuota 정보 집계
        quotas_summary = []
        for env in environments:
            if env.get('resource_quota'):
                quota = env['resource_quota']
                quotas_summary.append({
                    "namespace": env['namespace'],
                    "limits": quota.get('limits', {}),
                    "usage": quota.get('usage', {}),
                    "utilization": quota.get('utilization', {})
                })

        return {
            "summary": {
                "total_environments": total_environments,
                "active_environments": active_environments,
                "pending_environments": sum(1 for env in environments if env['status'] == 'Pending'),
                "failed_environments": sum(1 for env in environments if env['status'] == 'Failed')
            },
            "cluster_info": cluster_overview,
            "resource_quotas": quotas_summary,
            "timeframe": timeframe,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get resource usage: {str(e)}")


@router.get("/users-activity")
async def get_users_activity(
    limit: int = Query(50, ge=1, le=100, description="Number of users to return"),
    db: Session = Depends(get_session)
):
    """사용자 활동 현황"""
    try:
        # 최근 활동한 사용자들 조회
        active_users = db.query(User).join(EnvironmentInstance).filter(
            EnvironmentInstance.created_at >= datetime.utcnow() - timedelta(days=7)
        ).limit(limit).all()

        users_activity = []
        for user in active_users:
            # 해당 사용자의 환경 개수
            user_environments = db.query(EnvironmentInstance).filter(
                EnvironmentInstance.user_id == user.id
            ).all()

            users_activity.append({
                "user_id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role.value,
                "total_environments": len(user_environments),
                "active_environments": sum(1 for env in user_environments
                                         if env.status.value == 'running'),
                "last_activity": max([env.created_at for env in user_environments])
                                if user_environments else None,
                "organization": user.organization.name if user.organization else None
            })

        return {
            "users": users_activity,
            "total": len(users_activity),
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get users activity: {str(e)}")


@router.get("/templates-usage")
async def get_templates_usage(db: Session = Depends(get_session)):
    """템플릿 사용 현황"""
    try:
        # 모든 템플릿과 사용 횟수 조회
        templates = db.query(ProjectTemplate).all()

        templates_usage = []
        for template in templates:
            # 해당 템플릿으로 생성된 환경 개수
            environment_count = db.query(EnvironmentInstance).filter(
                EnvironmentInstance.template_id == template.id
            ).count()

            # 현재 활성화된 환경 개수
            active_count = db.query(EnvironmentInstance).filter(
                EnvironmentInstance.template_id == template.id,
                EnvironmentInstance.status.in_(['running', 'pending', 'creating'])
            ).count()

            templates_usage.append({
                "template_id": template.id,
                "name": template.name,
                "description": template.description,
                "status": template.status.value,
                "total_usage": environment_count,
                "current_active": active_count,
                "created_by": template.creator.email if template.creator else "unknown",
                "created_at": template.created_at,
                "resource_limits": template.resource_limits
            })

        return {
            "templates": templates_usage,
            "total": len(templates_usage),
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get templates usage: {str(e)}")


@router.post("/cleanup/expired")
async def cleanup_expired_environments(
    dry_run: bool = Query(False, description="Preview only, don't actually delete"),
    db: Session = Depends(get_session)
):
    """만료된 환경 정리"""
    try:
        # 만료된 환경 찾기
        expired_environments = db.query(EnvironmentInstance).filter(
            EnvironmentInstance.expires_at < datetime.utcnow(),
            EnvironmentInstance.status.in_(['running', 'stopped'])
        ).all()

        cleanup_results = []

        for env in expired_environments:
            result = {
                "environment_id": env.id,
                "name": env.name,
                "user_email": env.user.email,
                "expires_at": env.expires_at,
                "action": "would_delete" if dry_run else "deleted"
            }

            if not dry_run:
                try:
                    # 실제 정리 작업 수행
                    from app.services.environment_service import EnvironmentService
                    env_service = EnvironmentService(db)
                    await env_service.delete_environment(env.id)
                    result["status"] = "success"
                except Exception as cleanup_error:
                    result["status"] = "failed"
                    result["error"] = str(cleanup_error)

            cleanup_results.append(result)

        return {
            "cleaned_up": len(cleanup_results),
            "dry_run": dry_run,
            "results": cleanup_results,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cleanup environments: {str(e)}")


@router.get("/alerts")
async def get_system_alerts(db: Session = Depends(get_session)):
    """시스템 알림 및 경고"""
    try:
        alerts = []

        # 1. 만료 임박 환경
        soon_to_expire = db.query(EnvironmentInstance).filter(
            EnvironmentInstance.expires_at < datetime.utcnow() + timedelta(hours=1),
            EnvironmentInstance.expires_at > datetime.utcnow(),
            EnvironmentInstance.status.in_(['running'])
        ).all()

        for env in soon_to_expire:
            alerts.append({
                "type": "warning",
                "category": "expiration",
                "message": f"Environment '{env.name}' will expire in less than 1 hour",
                "environment_id": env.id,
                "user_email": env.user.email,
                "expires_at": env.expires_at
            })

        # 2. 오류 상태 환경
        failed_environments = db.query(EnvironmentInstance).filter(
            EnvironmentInstance.status == 'error'
        ).all()

        for env in failed_environments:
            alerts.append({
                "type": "error",
                "category": "environment_failed",
                "message": f"Environment '{env.name}' is in failed state",
                "environment_id": env.id,
                "user_email": env.user.email,
                "status_message": env.status_message
            })

        # 3. 리소스 사용률 높은 환경 (실제로는 K8s metrics에서 가져와야 함)
        try:
            k8s_service = KubernetesService()
            environments = await k8s_service.get_all_environments_status()

            for env in environments:
                if env.get('resource_quota'):
                    quota = env['resource_quota']
                    cpu_util = quota.get('utilization', {}).get('cpu_percent', 0)
                    mem_util = quota.get('utilization', {}).get('memory_percent', 0)

                    if cpu_util > 85 or mem_util > 85:
                        alerts.append({
                            "type": "warning",
                            "category": "high_resource_usage",
                            "message": f"High resource usage in namespace '{env['namespace']}'",
                            "namespace": env['namespace'],
                            "cpu_usage": f"{cpu_util}%",
                            "memory_usage": f"{mem_util}%"
                        })
        except Exception:
            # K8s 조회 실패는 무시
            pass

        return {
            "alerts": alerts,
            "total": len(alerts),
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get alerts: {str(e)}")


@router.get("/metrics/live/{namespace}")
async def get_live_metrics(namespace: str):
    """특정 네임스페이스의 실시간 메트릭"""
    try:
        k8s_service = KubernetesService()

        metrics = await k8s_service.get_live_resource_metrics(namespace)

        return metrics

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get live metrics: {str(e)}")