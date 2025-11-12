"""
Environment Service
개발 환경 생명주기 관리 서비스
"""

import asyncio
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models.environment import EnvironmentInstance, EnvironmentStatus
from app.models.project_template import ProjectTemplate
from app.services.kubernetes_service import KubernetesService
from app.core.config import settings


class EnvironmentService:
    """개발 환경 관리 서비스"""

    def __init__(self, db: Session):
        self.db = db
        self.k8s_service = KubernetesService()

    async def deploy_environment(self, environment_id: int) -> Dict[str, Any]:
        """환경을 K8s 클러스터에 배포"""

        environment = self.db.query(EnvironmentInstance).filter(
            EnvironmentInstance.id == environment_id
        ).first()

        if not environment:
            raise Exception("Environment not found")

        template = self.db.query(ProjectTemplate).filter(
            ProjectTemplate.id == environment.template_id
        ).first()

        if not template:
            raise Exception("Template not found")

        try:
            # 환경 상태 업데이트
            environment.status = EnvironmentStatus.CREATING
            environment.status_message = "Deploying to Kubernetes..."
            self.db.commit()

            # 네임스페이스 생성 (없으면)
            await self.k8s_service.create_namespace(environment.k8s_namespace)

            # ResourceQuota 생성 (자원 사용량 제한)
            quota_name = f"quota-{environment.k8s_deployment_name}"
            await self.k8s_service.create_resource_quota(
                namespace=environment.k8s_namespace,
                quota_name=quota_name,
                cpu_limit=template.resource_limits.get("cpu", settings.DEFAULT_CPU_LIMIT),
                memory_limit=template.resource_limits.get("memory", settings.DEFAULT_MEMORY_LIMIT),
                storage_limit=template.resource_limits.get("storage", settings.DEFAULT_STORAGE_LIMIT),
                pod_limit=5  # 기본값: 사용자당 최대 5개 Pod
            )

            # 환경변수 준비
            env_vars = {
                "ENVIRONMENT_ID": str(environment.id),
                "TEMPLATE_NAME": template.name,
                "USER_ID": str(environment.user_id),
                **template.environment_variables
            }

            # 리소스 제한 설정
            resource_limits = template.resource_limits or {
                "cpu": settings.DEFAULT_CPU_LIMIT,
                "memory": settings.DEFAULT_MEMORY_LIMIT
            }

            # Deployment 생성
            deployment_result = await self.k8s_service.create_deployment(
                namespace=environment.k8s_namespace,
                deployment_name=environment.k8s_deployment_name,
                image=template.base_image,
                environment_vars=env_vars,
                resource_limits=resource_limits,
                git_repo=environment.git_repository,
                git_branch=environment.git_branch or "main"
            )

            # Service 생성
            service_result = await self.k8s_service.create_service(
                namespace=environment.k8s_namespace,
                service_name=environment.k8s_service_name,
                deployment_name=environment.k8s_deployment_name,
                port=8080
            )

            # Ingress 생성 (외부 접속용)
            ingress_host = f"{environment.k8s_deployment_name}.kubdev.local"
            ingress_name = f"ing-{environment.k8s_deployment_name}"

            await self.k8s_service.create_ingress(
                namespace=environment.k8s_namespace,
                ingress_name=ingress_name,
                service_name=environment.k8s_service_name,
                host=ingress_host,
                service_port=8080
            )

            # 환경 정보 업데이트
            environment.k8s_ingress_name = ingress_name
            environment.access_url = f"http://{ingress_host}"
            environment.status = EnvironmentStatus.RUNNING
            environment.status_message = "Environment is ready"
            environment.started_at = datetime.utcnow()

            # 만료 시간 설정 (기본 8시간)
            if not environment.expires_at:
                environment.expires_at = datetime.utcnow() + timedelta(
                    hours=settings.ENVIRONMENT_TIMEOUT_HOURS
                )

            # 포트 매핑 정보 저장
            environment.port_mappings = template.exposed_ports or []

            self.db.commit()

            # 배포 완료 대기 (백그라운드에서)
            asyncio.create_task(self._wait_for_deployment_ready(environment_id))

            return {
                "environment_id": environment.id,
                "status": "deployed",
                "access_url": environment.access_url,
                "deployment": deployment_result,
                "service": service_result
            }

        except Exception as e:
            # 에러 발생 시 상태 업데이트
            environment.status = EnvironmentStatus.ERROR
            environment.status_message = f"Deployment failed: {str(e)}"
            self.db.commit()
            raise

    async def _wait_for_deployment_ready(self, environment_id: int, max_wait_time: int = 300):
        """Deployment가 Ready 상태가 될 때까지 대기"""

        environment = self.db.query(EnvironmentInstance).filter(
            EnvironmentInstance.id == environment_id
        ).first()

        if not environment:
            return

        start_time = datetime.utcnow()

        while (datetime.utcnow() - start_time).seconds < max_wait_time:
            try:
                status = await self.k8s_service.get_deployment_status(
                    namespace=environment.k8s_namespace,
                    deployment_name=environment.k8s_deployment_name
                )

                if status.get("ready_replicas", 0) >= 1:
                    # Deployment 준비 완료
                    environment.status = EnvironmentStatus.RUNNING
                    environment.status_message = "Environment is running and ready"
                    self.db.commit()
                    break

                # 30초 대기
                await asyncio.sleep(30)

            except Exception as e:
                environment.status = EnvironmentStatus.ERROR
                environment.status_message = f"Health check failed: {str(e)}"
                self.db.commit()
                break

        else:
            # 타임아웃
            environment.status = EnvironmentStatus.ERROR
            environment.status_message = "Deployment timeout - environment did not become ready"
            self.db.commit()

    async def start_environment(self, environment_id: int) -> Dict[str, Any]:
        """환경 시작"""

        environment = self.db.query(EnvironmentInstance).filter(
            EnvironmentInstance.id == environment_id
        ).first()

        if not environment:
            raise Exception("Environment not found")

        if environment.status == EnvironmentStatus.RUNNING:
            return {"message": "Environment is already running"}

        # Deployment 스케일 업
        try:
            deployment_status = await self.k8s_service.get_deployment_status(
                namespace=environment.k8s_namespace,
                deployment_name=environment.k8s_deployment_name
            )

            if deployment_status.get("status") == "not_found":
                # Deployment가 없으면 새로 생성
                await self.deploy_environment(environment_id)
            else:
                # 존재하면 시작
                environment.status = EnvironmentStatus.RUNNING
                environment.started_at = datetime.utcnow()
                environment.last_accessed_at = datetime.utcnow()
                self.db.commit()

            return {"message": "Environment started successfully"}

        except Exception as e:
            environment.status = EnvironmentStatus.ERROR
            environment.status_message = f"Failed to start: {str(e)}"
            self.db.commit()
            raise

    async def stop_environment(self, environment_id: int) -> Dict[str, Any]:
        """환경 중지"""

        environment = self.db.query(EnvironmentInstance).filter(
            EnvironmentInstance.id == environment_id
        ).first()

        if not environment:
            raise Exception("Environment not found")

        try:
            # Deployment 삭제 (리소스 해제)
            await self.k8s_service.delete_deployment(
                namespace=environment.k8s_namespace,
                deployment_name=environment.k8s_deployment_name
            )

            # 상태 업데이트
            environment.status = EnvironmentStatus.STOPPED
            environment.stopped_at = datetime.utcnow()
            environment.status_message = "Environment stopped"
            self.db.commit()

            return {"message": "Environment stopped successfully"}

        except Exception as e:
            environment.status = EnvironmentStatus.ERROR
            environment.status_message = f"Failed to stop: {str(e)}"
            self.db.commit()
            raise

    async def restart_environment(self, environment_id: int) -> Dict[str, Any]:
        """환경 재시작"""

        await self.stop_environment(environment_id)
        await asyncio.sleep(10)  # 완전히 중지될 때까지 대기
        await self.start_environment(environment_id)

        return {"message": "Environment restarted successfully"}

    async def delete_environment(self, environment_id: int) -> Dict[str, Any]:
        """환경 완전 삭제"""

        environment = self.db.query(EnvironmentInstance).filter(
            EnvironmentInstance.id == environment_id
        ).first()

        if not environment:
            raise Exception("Environment not found")

        try:
            # K8s 리소스 삭제
            await self.k8s_service.delete_deployment(
                namespace=environment.k8s_namespace,
                deployment_name=environment.k8s_deployment_name
            )

            if environment.k8s_service_name:
                await self.k8s_service.delete_service(
                    namespace=environment.k8s_namespace,
                    service_name=environment.k8s_service_name
                )

            # 데이터베이스에서 삭제
            self.db.delete(environment)
            self.db.commit()

            return {"message": "Environment deleted successfully"}

        except Exception as e:
            raise Exception(f"Failed to delete environment: {str(e)}")

    async def get_environment_metrics(self, environment_id: int) -> Dict[str, Any]:
        """환경 메트릭 조회"""

        environment = self.db.query(EnvironmentInstance).filter(
            EnvironmentInstance.id == environment_id
        ).first()

        if not environment:
            raise Exception("Environment not found")

        # K8s 메트릭 조회 (실제 구현에서는 metrics-server나 Prometheus 사용)
        # 여기서는 기본값 반환
        return {
            "environment_id": environment_id,
            "cpu_usage": 45.2,
            "memory_usage": 68.5,
            "storage_usage": 23.1,
            "uptime_seconds": 3600
        }