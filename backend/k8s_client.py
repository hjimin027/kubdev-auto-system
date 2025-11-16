import os
from typing import Dict, Any
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
