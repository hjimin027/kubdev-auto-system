"""
Kubernetes Service
K8s 클러스터와의 상호작용을 관리하는 서비스
"""

import os
import yaml
from typing import Dict, List, Optional, Any
from kubernetes import client, config
from kubernetes.client.rest import ApiException

from app.core.config import settings


class KubernetesService:
    """Kubernetes 클러스터 관리 서비스"""

    def __init__(self):
        """K8s 클라이언트 초기화"""
        try:
            if settings.KUBECONFIG_PATH and os.path.exists(settings.KUBECONFIG_PATH):
                config.load_kube_config(config_file=settings.KUBECONFIG_PATH)
            else:
                # 클러스터 내부에서 실행되는 경우
                config.load_incluster_config()
        except Exception:
            # 로컬 개발환경에서는 기본 kubeconfig 사용
            try:
                config.load_kube_config()
            except Exception as e:
                raise Exception(f"Failed to load Kubernetes config: {str(e)}")

        self.v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.networking_v1 = client.NetworkingV1Api()

    async def create_namespace(self, namespace: str) -> bool:
        """네임스페이스 생성"""
        try:
            namespace_manifest = client.V1Namespace(
                metadata=client.V1ObjectMeta(name=namespace)
            )
            self.v1.create_namespace(namespace_manifest)
            return True
        except ApiException as e:
            if e.status == 409:  # Already exists
                return True
            raise Exception(f"Failed to create namespace: {str(e)}")

    async def create_resource_quota(
        self,
        namespace: str,
        quota_name: str,
        cpu_limit: str = "1",
        memory_limit: str = "2Gi",
        storage_limit: str = "10Gi",
        pod_limit: int = 5
    ) -> Dict[str, Any]:
        """네임스페이스에 ResourceQuota 생성 - 자원 사용량 제한"""
        try:
            # ResourceQuota 스펙 정의
            resource_quota = client.V1ResourceQuota(
                api_version="v1",
                kind="ResourceQuota",
                metadata=client.V1ObjectMeta(name=quota_name),
                spec=client.V1ResourceQuotaSpec(
                    hard={
                        # CPU/메모리 제한
                        "limits.cpu": cpu_limit,
                        "limits.memory": memory_limit,
                        "requests.cpu": str(float(cpu_limit.rstrip('m')) * 0.5) + ("m" if cpu_limit.endswith('m') else ""),
                        "requests.memory": str(int(memory_limit.rstrip('Gi')) // 2) + "Gi",

                        # 스토리지 제한
                        "requests.storage": storage_limit,

                        # Pod 개수 제한
                        "pods": str(pod_limit),

                        # 서비스 개수 제한
                        "services": "5",

                        # PVC 개수 제한
                        "persistentvolumeclaims": "3",

                        # Secret/ConfigMap 제한
                        "secrets": "10",
                        "configmaps": "10"
                    }
                )
            )

            result = self.v1.create_namespaced_resource_quota(
                body=resource_quota,
                namespace=namespace
            )

            return {
                "name": quota_name,
                "namespace": namespace,
                "limits": {
                    "cpu": cpu_limit,
                    "memory": memory_limit,
                    "storage": storage_limit,
                    "pods": pod_limit
                },
                "status": "created",
                "uid": result.metadata.uid
            }

        except ApiException as e:
            if e.status == 409:  # Already exists
                return {
                    "name": quota_name,
                    "namespace": namespace,
                    "status": "already_exists"
                }
            raise Exception(f"Failed to create resource quota: {str(e)}")

    async def get_resource_quota_status(self, namespace: str, quota_name: str) -> Dict[str, Any]:
        """ResourceQuota 상태 및 사용량 조회"""
        try:
            quota = self.v1.read_namespaced_resource_quota(
                name=quota_name,
                namespace=namespace
            )

            hard_limits = quota.status.hard or {}
            used_resources = quota.status.used or {}

            return {
                "name": quota_name,
                "namespace": namespace,
                "limits": {
                    "cpu": hard_limits.get("limits.cpu", "0"),
                    "memory": hard_limits.get("limits.memory", "0"),
                    "storage": hard_limits.get("requests.storage", "0"),
                    "pods": hard_limits.get("pods", "0")
                },
                "usage": {
                    "cpu": used_resources.get("limits.cpu", "0"),
                    "memory": used_resources.get("limits.memory", "0"),
                    "storage": used_resources.get("requests.storage", "0"),
                    "pods": used_resources.get("pods", "0")
                },
                "utilization": {
                    "cpu_percent": self._calculate_utilization(
                        used_resources.get("limits.cpu", "0"),
                        hard_limits.get("limits.cpu", "1")
                    ),
                    "memory_percent": self._calculate_utilization(
                        used_resources.get("limits.memory", "0"),
                        hard_limits.get("limits.memory", "1Gi")
                    )
                }
            }

        except ApiException as e:
            if e.status == 404:
                return {"status": "not_found"}
            raise Exception(f"Failed to get resource quota status: {str(e)}")

    def _calculate_utilization(self, used: str, limit: str) -> float:
        """리소스 사용률 계산 (백분율)"""
        try:
            # CPU 계산 (millicores 단위)
            if 'm' in used and 'm' in limit:
                used_val = float(used.rstrip('m'))
                limit_val = float(limit.rstrip('m'))
                return round((used_val / limit_val) * 100, 2) if limit_val > 0 else 0

            # 메모리 계산 (Gi 단위)
            elif 'Gi' in used and 'Gi' in limit:
                used_val = float(used.rstrip('Gi'))
                limit_val = float(limit.rstrip('Gi'))
                return round((used_val / limit_val) * 100, 2) if limit_val > 0 else 0

            # 정수 단위 (pods, services 등)
            else:
                used_val = float(used)
                limit_val = float(limit)
                return round((used_val / limit_val) * 100, 2) if limit_val > 0 else 0

        except (ValueError, ZeroDivisionError):
            return 0.0

    async def create_deployment(
        self,
        namespace: str,
        deployment_name: str,
        image: str,
        environment_vars: Dict[str, str] = {},
        resource_limits: Dict[str, str] = {},
        git_repo: Optional[str] = None,
        git_branch: str = "main"
    ) -> Dict[str, Any]:
        """Deployment 생성"""

        try:
            # 컨테이너 환경변수 설정
            env_vars = [
                client.V1EnvVar(name=k, value=v) for k, v in environment_vars.items()
            ]

            # 리소스 제한 설정
            resources = client.V1ResourceRequirements(
                limits=resource_limits,
                requests=resource_limits  # 간단히 limits와 동일하게 설정
            )

            # 볼륨 마운트 설정 (워크스페이스용)
            volume_mounts = [
                client.V1VolumeMount(
                    name="workspace",
                    mount_path="/workspace"
                )
            ]

            # 메인 컨테이너 정의
            main_container = client.V1Container(
                name="ide",
                image=image,
                env=env_vars,
                resources=resources,
                volume_mounts=volume_mounts,
                ports=[client.V1ContainerPort(container_port=8080)],
                working_dir="/workspace"
            )

            # Init Container (Git 클론용)
            init_containers = []
            if git_repo:
                git_init_container = client.V1Container(
                    name="git-clone",
                    image="alpine/git:latest",
                    command=["sh", "-c"],
                    args=[
                        f"git clone -b {git_branch} {git_repo} /workspace || "
                        f"(mkdir -p /workspace && echo 'Git clone failed, using empty workspace')"
                    ],
                    volume_mounts=[
                        client.V1VolumeMount(
                            name="workspace",
                            mount_path="/workspace"
                        )
                    ]
                )
                init_containers.append(git_init_container)

            # 볼륨 정의
            volumes = [
                client.V1Volume(
                    name="workspace",
                    empty_dir=client.V1EmptyDirVolumeSource()
                )
            ]

            # Pod 스펙
            pod_spec = client.V1PodSpec(
                containers=[main_container],
                init_containers=init_containers,
                volumes=volumes,
                restart_policy="Always"
            )

            # Pod 템플릿
            pod_template = client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels={"app": deployment_name, "component": "ide"}
                ),
                spec=pod_spec
            )

            # Deployment 스펙
            deployment_spec = client.V1DeploymentSpec(
                replicas=1,
                selector=client.V1LabelSelector(
                    match_labels={"app": deployment_name}
                ),
                template=pod_template
            )

            # Deployment 생성
            deployment = client.V1Deployment(
                api_version="apps/v1",
                kind="Deployment",
                metadata=client.V1ObjectMeta(name=deployment_name),
                spec=deployment_spec
            )

            result = self.apps_v1.create_namespaced_deployment(
                body=deployment,
                namespace=namespace
            )

            return {
                "name": deployment_name,
                "namespace": namespace,
                "status": "created",
                "uid": result.metadata.uid
            }

        except ApiException as e:
            raise Exception(f"Failed to create deployment: {str(e)}")

    async def create_service(
        self,
        namespace: str,
        service_name: str,
        deployment_name: str,
        port: int = 8080
    ) -> Dict[str, Any]:
        """Service 생성"""

        try:
            service_spec = client.V1ServiceSpec(
                selector={"app": deployment_name},
                ports=[client.V1ServicePort(
                    port=port,
                    target_port=port,
                    name="http"
                )],
                type="ClusterIP"
            )

            service = client.V1Service(
                api_version="v1",
                kind="Service",
                metadata=client.V1ObjectMeta(name=service_name),
                spec=service_spec
            )

            result = self.v1.create_namespaced_service(
                body=service,
                namespace=namespace
            )

            return {
                "name": service_name,
                "namespace": namespace,
                "cluster_ip": result.spec.cluster_ip,
                "port": port
            }

        except ApiException as e:
            raise Exception(f"Failed to create service: {str(e)}")

    async def create_ingress(
        self,
        namespace: str,
        ingress_name: str,
        service_name: str,
        host: str,
        service_port: int = 8080
    ) -> Dict[str, Any]:
        """Ingress 생성"""

        try:
            # Ingress 규칙 정의
            ingress_rule = client.V1IngressRule(
                host=host,
                http=client.V1HTTPIngressRuleValue(
                    paths=[client.V1HTTPIngressPath(
                        path="/",
                        path_type="Prefix",
                        backend=client.V1IngressBackend(
                            service=client.V1IngressServiceBackend(
                                name=service_name,
                                port=client.V1ServiceBackendPort(number=service_port)
                            )
                        )
                    )]
                )
            )

            ingress_spec = client.V1IngressSpec(
                rules=[ingress_rule]
            )

            ingress = client.V1Ingress(
                api_version="networking.k8s.io/v1",
                kind="Ingress",
                metadata=client.V1ObjectMeta(name=ingress_name),
                spec=ingress_spec
            )

            result = self.networking_v1.create_namespaced_ingress(
                body=ingress,
                namespace=namespace
            )

            return {
                "name": ingress_name,
                "namespace": namespace,
                "host": host,
                "uid": result.metadata.uid
            }

        except ApiException as e:
            raise Exception(f"Failed to create ingress: {str(e)}")

    async def delete_deployment(self, namespace: str, deployment_name: str) -> bool:
        """Deployment 삭제"""
        try:
            self.apps_v1.delete_namespaced_deployment(
                name=deployment_name,
                namespace=namespace
            )
            return True
        except ApiException as e:
            if e.status == 404:
                return True  # 이미 삭제됨
            raise Exception(f"Failed to delete deployment: {str(e)}")

    async def delete_service(self, namespace: str, service_name: str) -> bool:
        """Service 삭제"""
        try:
            self.v1.delete_namespaced_service(
                name=service_name,
                namespace=namespace
            )
            return True
        except ApiException as e:
            if e.status == 404:
                return True
            raise Exception(f"Failed to delete service: {str(e)}")

    async def get_pod_logs(
        self,
        namespace: str,
        deployment_name: str,
        tail_lines: int = 100
    ) -> str:
        """Pod 로그 조회"""
        try:
            # Deployment의 Pod 찾기
            pods = self.v1.list_namespaced_pod(
                namespace=namespace,
                label_selector=f"app={deployment_name}"
            )

            if not pods.items:
                return "No pods found"

            # 첫 번째 Pod의 로그 가져오기
            pod_name = pods.items[0].metadata.name
            logs = self.v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                tail_lines=tail_lines
            )

            return logs

        except ApiException as e:
            raise Exception(f"Failed to get pod logs: {str(e)}")

    async def get_deployment_status(
        self,
        namespace: str,
        deployment_name: str
    ) -> Dict[str, Any]:
        """Deployment 상태 조회"""
        try:
            deployment = self.apps_v1.read_namespaced_deployment(
                name=deployment_name,
                namespace=namespace
            )

            return {
                "name": deployment.metadata.name,
                "namespace": deployment.metadata.namespace,
                "replicas": deployment.spec.replicas,
                "ready_replicas": deployment.status.ready_replicas or 0,
                "available_replicas": deployment.status.available_replicas or 0,
                "conditions": [
                    {
                        "type": condition.type,
                        "status": condition.status,
                        "reason": condition.reason,
                        "message": condition.message
                    }
                    for condition in (deployment.status.conditions or [])
                ]
            }

        except ApiException as e:
            if e.status == 404:
                return {"status": "not_found"}
            raise Exception(f"Failed to get deployment status: {str(e)}")

    async def get_cluster_overview(self) -> Dict[str, Any]:
        """클러스터 전체 현황 조회 - Admin 대시보드용"""
        try:
            # 전체 노드 정보
            nodes = self.v1.list_node()
            node_count = len(nodes.items)
            node_ready_count = sum(1 for node in nodes.items
                                 if any(condition.type == "Ready" and condition.status == "True"
                                       for condition in node.status.conditions))

            # 전체 Pod 정보
            all_pods = self.v1.list_pod_for_all_namespaces()
            total_pods = len(all_pods.items)
            running_pods = sum(1 for pod in all_pods.items if pod.status.phase == "Running")
            pending_pods = sum(1 for pod in all_pods.items if pod.status.phase == "Pending")
            failed_pods = sum(1 for pod in all_pods.items if pod.status.phase == "Failed")

            # KubeDev 환경 Pod만 필터링
            kubdev_pods = [pod for pod in all_pods.items
                          if pod.metadata.namespace and 'kubdev' in pod.metadata.namespace]

            return {
                "cluster_info": {
                    "total_nodes": node_count,
                    "ready_nodes": node_ready_count,
                    "total_pods": total_pods,
                    "running_pods": running_pods,
                    "pending_pods": pending_pods,
                    "failed_pods": failed_pods
                },
                "kubdev_info": {
                    "total_environments": len(kubdev_pods),
                    "active_environments": sum(1 for pod in kubdev_pods if pod.status.phase == "Running"),
                    "pending_environments": sum(1 for pod in kubdev_pods if pod.status.phase == "Pending"),
                    "failed_environments": sum(1 for pod in kubdev_pods if pod.status.phase == "Failed")
                },
                "timestamp": "now"
            }

        except ApiException as e:
            raise Exception(f"Failed to get cluster overview: {str(e)}")

    async def get_all_environments_status(self) -> List[Dict[str, Any]]:
        """모든 KubeDev 환경의 실시간 상태 조회"""
        try:
            environments = []

            # kubdev 관련 네임스페이스 찾기
            namespaces = self.v1.list_namespace()
            kubdev_namespaces = [ns for ns in namespaces.items
                               if ns.metadata.name.startswith('kubdev') or
                                  'kubdev' in ns.metadata.name]

            for namespace in kubdev_namespaces:
                ns_name = namespace.metadata.name

                try:
                    # 해당 네임스페이스의 모든 Pod 조회
                    pods = self.v1.list_namespaced_pod(namespace=ns_name)

                    # ResourceQuota 조회
                    quotas = self.v1.list_namespaced_resource_quota(namespace=ns_name)
                    quota_info = None

                    if quotas.items:
                        quota_name = quotas.items[0].metadata.name
                        quota_info = await self.get_resource_quota_status(ns_name, quota_name)

                    # Pod 정보 처리
                    for pod in pods.items:
                        if 'app' in pod.metadata.labels:
                            environments.append({
                                "namespace": ns_name,
                                "pod_name": pod.metadata.name,
                                "app_label": pod.metadata.labels.get('app', 'unknown'),
                                "status": pod.status.phase,
                                "created_at": pod.metadata.creation_timestamp,
                                "node_name": pod.spec.node_name,
                                "pod_ip": pod.status.pod_ip,
                                "resource_quota": quota_info,
                                "containers": [
                                    {
                                        "name": container.name,
                                        "image": container.image,
                                        "ready": self._is_container_ready(pod, container.name)
                                    }
                                    for container in pod.spec.containers
                                ]
                            })

                except ApiException as inner_e:
                    # 개별 네임스페이스 조회 실패는 무시하고 계속
                    continue

            return environments

        except ApiException as e:
            raise Exception(f"Failed to get environments status: {str(e)}")

    def _is_container_ready(self, pod, container_name: str) -> bool:
        """컨테이너가 Ready 상태인지 확인"""
        if not pod.status.container_statuses:
            return False

        for status in pod.status.container_statuses:
            if status.name == container_name:
                return status.ready or False
        return False

    async def get_namespace_details(self, namespace: str) -> Dict[str, Any]:
        """특정 네임스페이스의 상세 정보 조회"""
        try:
            # Pod 목록
            pods = self.v1.list_namespaced_pod(namespace=namespace)

            # Service 목록
            services = self.v1.list_namespaced_service(namespace=namespace)

            # Deployment 목록
            deployments = self.apps_v1.list_namespaced_deployment(namespace=namespace)

            # ResourceQuota 정보
            quotas = self.v1.list_namespaced_resource_quota(namespace=namespace)
            quota_info = None
            if quotas.items:
                quota_name = quotas.items[0].metadata.name
                quota_info = await self.get_resource_quota_status(namespace, quota_name)

            # 최근 이벤트
            events = self.v1.list_namespaced_event(namespace=namespace)
            recent_events = sorted(events.items,
                                 key=lambda x: x.metadata.creation_timestamp,
                                 reverse=True)[:10]

            return {
                "namespace": namespace,
                "pod_count": len(pods.items),
                "service_count": len(services.items),
                "deployment_count": len(deployments.items),
                "resource_quota": quota_info,
                "pods": [
                    {
                        "name": pod.metadata.name,
                        "status": pod.status.phase,
                        "ready": self._get_pod_ready_status(pod),
                        "created_at": pod.metadata.creation_timestamp,
                        "node": pod.spec.node_name,
                        "ip": pod.status.pod_ip
                    }
                    for pod in pods.items
                ],
                "recent_events": [
                    {
                        "type": event.type,
                        "reason": event.reason,
                        "message": event.message,
                        "timestamp": event.metadata.creation_timestamp,
                        "object": f"{event.involved_object.kind}/{event.involved_object.name}"
                    }
                    for event in recent_events
                ]
            }

        except ApiException as e:
            if e.status == 404:
                return {"status": "not_found"}
            raise Exception(f"Failed to get namespace details: {str(e)}")

    def _get_pod_ready_status(self, pod) -> str:
        """Pod의 Ready 상태를 문자열로 반환"""
        if not pod.status.container_statuses:
            return "0/0"

        total_containers = len(pod.status.container_statuses)
        ready_containers = sum(1 for status in pod.status.container_statuses if status.ready)

        return f"{ready_containers}/{total_containers}"

    async def get_live_resource_metrics(self, namespace: str) -> Dict[str, Any]:
        """실시간 리소스 메트릭 조회 (metrics-server 필요)"""
        try:
            # metrics-server API를 통한 메트릭 조회
            # 실제 환경에서는 metrics.k8s.io API를 사용

            pods = self.v1.list_namespaced_pod(namespace=namespace)

            metrics_data = {
                "namespace": namespace,
                "timestamp": "now",
                "pod_metrics": []
            }

            for pod in pods.items:
                if pod.status.phase == "Running":
                    # 기본 메트릭 정보 (실제로는 metrics-server에서 가져옴)
                    metrics_data["pod_metrics"].append({
                        "pod_name": pod.metadata.name,
                        "cpu_usage": "0m",  # 실제 구현에서는 metrics API 호출
                        "memory_usage": "0Mi",
                        "status": pod.status.phase,
                        "containers": len(pod.spec.containers)
                    })

            return metrics_data

        except ApiException as e:
            raise Exception(f"Failed to get resource metrics: {str(e)}")