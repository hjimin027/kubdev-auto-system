import os
from typing import Dict, Any, List
from kubernetes import client, config
import datetime


def load_kube():
    try:
        config.load_incluster_config()
    except Exception:
        try:
            config.load_kube_config()
        except Exception:
            pass


def create_kubedev_environment(name: str, namespace: str, spec: Dict[str, Any]) -> Dict[str, Any]:
    # Mock mode for local tests without a cluster
    if os.getenv("KUBEDEV_MOCK", "").lower() in ("1", "true", "yes"):
        return {
            "apiVersion": "kubedev.my-project.com/v1alpha1",
            "kind": "KubeDevEnvironment",
            "metadata": {"name": name, "namespace": namespace, "creationTimestamp": datetime.datetime.utcnow().isoformat() + "Z"},
            "spec": spec,
            "status": {
                "phase": "Pending",
                "namespace": f"kubedev-{spec.get('userName','user')}-{name}",
                "ideUrl": "",
                "workspaceId": name,
            },
        }

    load_kube()
    co = client.CustomObjectsApi()
    group = "kubedev.my-project.com"
    version = "v1alpha1"
    plural = "kubedevenvironments"
    body = {
        "apiVersion": f"{group}/{version}",
        "kind": "KubeDevEnvironment",
        "metadata": {"name": name, "namespace": namespace},
        "spec": spec,
    }
    created = co.create_namespaced_custom_object(group, version, namespace, plural, body)
    return created


def get_kubedev_environment(name: str, namespace: str) -> Dict[str, Any]:
    load_kube()
    co = client.CustomObjectsApi()
    group = "kubedev.my-project.com"
    version = "v1alpha1"
    plural = "kubedevenvironments"
    return co.get_namespaced_custom_object(group, version, namespace, plural, name)


def list_kubedev_environments(namespace: str) -> List[Dict[str, Any]]:
    load_kube()
    co = client.CustomObjectsApi()
    group = "kubedev.my-project.com"
    version = "v1alpha1"
    plural = "kubedevenvironments"
    items = co.list_namespaced_custom_object(group, version, namespace, plural)
    return items.get('items', [])


def delete_kubedev_environment(name: str, namespace: str) -> None:
    load_kube()
    co = client.CustomObjectsApi()
    group = "kubedev.my-project.com"
    version = "v1alpha1"
    plural = "kubedevenvironments"
    co.delete_namespaced_custom_object(group, version, namespace, plural, name)


def scale_deployment(namespace: str, name: str, replicas: int) -> None:
    load_kube()
    apps = client.AppsV1Api()
    # Patch the scale subresource
    body = {"spec": {"replicas": replicas}}
    try:
        apps.patch_namespaced_deployment_scale(name=name, namespace=namespace, body=body)
    except Exception:
        # Fallback: patch deployment directly
        apps.patch_namespaced_deployment(name=name, namespace=namespace, body=body)


def delete_namespace(name: str) -> None:
    load_kube()
    core = client.CoreV1Api()
    try:
        core.delete_namespace(name)
    except client.exceptions.ApiException as e:
        if e.status != 404:
            raise
