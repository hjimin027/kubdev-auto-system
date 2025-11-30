import os
import yaml
import httpx
from fastapi import FastAPI, Depends, HTTPException, Path, Query
from fastapi.responses import JSONResponse
from backend.auth import get_current_user
from backend.models import (
    WorkspaceCreateRequest,
    WorkspaceCreateResponse,
    WorkspaceItem,
    AdminBatchCreateRequest,
    AdminBatchCreateResponse,
)
from backend.k8s_client import (
    create_kubedev_environment,
    get_kubedev_environment,
    list_kubedev_environments,
    delete_kubedev_environment,
    scale_deployment,
    delete_namespace,
)


app = FastAPI(title="KubeDev Auto System API", version="0.2.0")


def parse_gitpod_yaml(repo_url: str):
    # Very thin subset: image, tasks.command, ports
    try:
        if repo_url.endswith('.git'):
            raw_base = repo_url[:-4]
        else:
            raw_base = repo_url
        if 'github.com' in raw_base:
            parts = raw_base.split('github.com/')[-1]
            raw_url = f"https://raw.githubusercontent.com/{parts}/HEAD/.gitpod.yml"
        elif 'gitlab.com' in raw_base:
            parts = raw_base.split('gitlab.com/')[-1]
            raw_url = f"https://gitlab.com/{parts}/-/raw/HEAD/.gitpod.yml"
        else:
            return {}
        r = httpx.get(raw_url, timeout=5.0)
        if r.status_code != 200:
            return {}
        data = yaml.safe_load(r.text) or {}
        out = {}
        if isinstance(data.get('image'), str):
            out['image'] = data['image']
        tasks = data.get('tasks')
        if isinstance(tasks, list) and tasks:
            t0 = tasks[0] or {}
            cmd = t0.get('command')
            if isinstance(cmd, str):
                out.setdefault('commands', {})['start'] = cmd
            init = t0.get('init')
            if isinstance(init, str):
                out.setdefault('commands', {})['init'] = init
        ports = data.get('ports')
        if isinstance(ports, list):
            out['ports'] = []
            for p in ports:
                if isinstance(p, int):
                    out['ports'].append(p)
                elif isinstance(p, dict) and isinstance(p.get('port'), int):
                    out['ports'].append(p['port'])
        return out
    except Exception:
        return {}


@app.post("/me/workspaces", response_model=WorkspaceCreateResponse)
async def create_workspace(payload: WorkspaceCreateRequest, user=Depends(get_current_user)):
    ctrl_ns = os.getenv("KUBEDEV_CTRL_NS", "kubedev-users")
    env_name = f"env-{user['id']}-{payload.name}"

    spec = {
        "userName": user["name"],
        "templateId": payload.template_id,
        "git": {"repoUrl": str(payload.git_repository), "ref": payload.ref or "main"} if payload.git_repository else None,
        "image": payload.image,
        "commands": {"start": payload.start_command, "init": payload.init_command},
        "ports": payload.ports or [],
        "mode": payload.mode,
    }
    spec = {k: v for k, v in spec.items() if v is not None}

    if payload.gitpod_compat and payload.git_repository:
        compat = parse_gitpod_yaml(str(payload.git_repository))
        for k, v in compat.items():
            if k == 'commands':
                spec.setdefault('commands', {})
                for ck, cv in v.items():
                    spec['commands'].setdefault(ck, cv)
            elif k == 'ports':
                existing = set(spec.get('ports', []))
                spec['ports'] = list(existing.union(set(v)))
            else:
                spec.setdefault(k, v)

    created = create_kubedev_environment(env_name, ctrl_ns, spec)
    status = created.get('status') or {}
    return WorkspaceCreateResponse(id=env_name, status=status.get('phase', 'Pending'), namespace=status.get('namespace'), ideUrl=status.get('ideUrl'))


@app.get("/me/workspaces", response_model=list[WorkspaceItem])
async def list_my_workspaces(user=Depends(get_current_user)):
    ctrl_ns = os.getenv("KUBEDEV_CTRL_NS", "kubedev-users")
    items = list_kubedev_environments(ctrl_ns)
    out: list[WorkspaceItem] = []
    for it in items:
        spec = it.get('spec', {})
        if spec.get('userName') != user['name']:
            continue
        st = it.get('status', {})
        out.append(
            WorkspaceItem(
                id=it['metadata']['name'],
                userName=spec.get('userName', ''),
                status=st.get('phase'),
                namespace=st.get('namespace'),
                ideUrl=st.get('ideUrl'),
                createdAt=it['metadata'].get('creationTimestamp'),
                templateId=spec.get('templateId'),
            )
        )
    return out


@app.post("/me/workspaces/{wid}/stop")
async def stop_workspace(wid: str = Path(...), user=Depends(get_current_user)):
    ctrl_ns = os.getenv("KUBEDEV_CTRL_NS", "kubedev-users")
    cr = get_kubedev_environment(wid, ctrl_ns)
    spec = cr.get('spec', {})
    if spec.get('userName') != user['name']:
        raise HTTPException(status_code=403, detail="Forbidden")
    ns = (cr.get('status') or {}).get('namespace')
    if not ns:
        raise HTTPException(status_code=409, detail="Workspace not ready")
    scale_deployment(ns, f"ide-{wid}", 0)
    return {"status": "Hibernating"}


@app.post("/me/workspaces/{wid}/start")
async def start_workspace(wid: str = Path(...), user=Depends(get_current_user)):
    ctrl_ns = os.getenv("KUBEDEV_CTRL_NS", "kubedev-users")
    cr = get_kubedev_environment(wid, ctrl_ns)
    spec = cr.get('spec', {})
    if spec.get('userName') != user['name']:
        raise HTTPException(status_code=403, detail="Forbidden")
    ns = (cr.get('status') or {}).get('namespace')
    if not ns:
        raise HTTPException(status_code=409, detail="Workspace not ready")
    scale_deployment(ns, f"ide-{wid}", 1)
    return {"status": "Running"}


@app.delete("/me/workspaces/{wid}")
async def delete_workspace(wid: str = Path(...),
                           delete_namespace_first: bool = Query(True),
                           user=Depends(get_current_user)):
    ctrl_ns = os.getenv("KUBEDEV_CTRL_NS", "kubedev-users")
    cr = get_kubedev_environment(wid, ctrl_ns)
    spec = cr.get('spec', {})
    if spec.get('userName') != user['name']:
        raise HTTPException(status_code=403, detail="Forbidden")
    ns = (cr.get('status') or {}).get('namespace')
    if delete_namespace_first and ns:
        delete_namespace(ns)
    delete_kubedev_environment(wid, ctrl_ns)
    return {"deleted": wid}


def _ensure_admin(user: dict):
    if user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin only")


@app.post("/admin/workspaces/batch", response_model=AdminBatchCreateResponse)
async def admin_batch_create(payload: AdminBatchCreateRequest, user=Depends(get_current_user)):
    _ensure_admin(user)
    ctrl_ns = os.getenv("KUBEDEV_CTRL_NS", "kubedev-users")
    created_list: list[WorkspaceCreateResponse] = []
    failed: list[str] = []
    for uname in payload.users:
        env_name = f"env-{uname}-{payload.name}"
        spec = {
            "userName": uname,
            "templateId": payload.template_id,
            "git": {"repoUrl": str(payload.git_repository), "ref": payload.ref or "main"} if payload.git_repository else None,
            "image": payload.image,
            "commands": {"start": payload.start_command, "init": payload.init_command},
            "ports": payload.ports or [],
            "mode": payload.mode,
        }
        spec = {k: v for k, v in spec.items() if v is not None}
        try:
            created = create_kubedev_environment(env_name, ctrl_ns, spec)
            st = created.get('status') or {}
            created_list.append(WorkspaceCreateResponse(id=env_name, status=st.get('phase', 'Pending'), namespace=st.get('namespace'), ideUrl=st.get('ideUrl')))
        except Exception as e:
            failed.append(f"{uname}: {e}")
    return AdminBatchCreateResponse(created=created_list, failed=failed)


@app.get("/healthz")
async def healthz():
    return JSONResponse({"status": "ok"})
