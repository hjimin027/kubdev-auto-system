"""
User API Endpoints
사용자 관련 API 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.core.security import generate_access_code
from app.models.user import User, UserRole
from app.models.project_template import ProjectTemplate, TemplateStatus
from app.models.environment import EnvironmentInstance, EnvironmentStatus
from app.schemas.user import (
    UserCreateAdmin,
    UserCreateAdminResponse,
    UserCreateUser,
    UserCreateUserResponse,
)
from app.services.kubernetes_service import KubernetesService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/admin", response_model=UserCreateAdminResponse, status_code=status.HTTP_201_CREATED)
async def create_admin_user(
    user_data: UserCreateAdmin,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> UserCreateAdminResponse:
    """
    사용자 생성 - 관계자
    """
    logger.info(f"Creating admin user: {user_data.name} by user {user_data.current_user_id}")
    
    # 현재 사용자가 관리자인지 확인
    if current_user.role != UserRole.ADMIN:
        logger.warning(f"Non-admin user {current_user.id} attempted to create admin user")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create admin users"
        )
    
    # 5자리 접속 코드 생성 (중복 방지)
    max_attempts = 10
    access_code = None
    
    for _ in range(max_attempts):
        code = generate_access_code(length=5)
        # 중복 확인
        existing_user = db.query(User).filter(User.hashed_password == code).first()
        if not existing_user:
            access_code = code
            break
    
    if not access_code:
        logger.error("Failed to generate unique access code after multiple attempts")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate unique access code"
        )
    
    # 새 관리자 사용자 생성
    new_user = User(
        name=user_data.name,
        hashed_password=access_code,  # 개발 중이므로 접속 코드를 그대로 저장
        role=UserRole.ADMIN,
        is_active=True,
        created_by=user_data.current_user_id
    )
    
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"Admin user created successfully: ID={new_user.id}, access_code={access_code}")
        
        return UserCreateAdminResponse(
            id=new_user.id,
            name=new_user.name,
            role=new_user.role,
            access_code=access_code,
            is_active=new_user.is_active,
            created_at=new_user.created_at
        )
    
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create admin user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create admin user: {str(e)}"
        )


@router.post("/user", response_model=UserCreateUserResponse, status_code=status.HTTP_201_CREATED)
async def create_regular_user(
    user_data: UserCreateUser,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> UserCreateUserResponse:
    """
    사용자 생성 - 일반 사용자 (환경 자동 생성 포함)
    """
    logger.info(f"Creating regular user: {user_data.name} by user {user_data.current_user_id}")
    
    # 현재 사용자가 관리자인지 확인
    if current_user.role != UserRole.ADMIN:
        logger.warning(f"Non-admin user {current_user.id} attempted to create regular user")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create users"
        )
    
    # 5자리 접속 코드 생성 (중복 방지)
    max_attempts = 10
    access_code = None
    
    for _ in range(max_attempts):
        code = generate_access_code(length=5)
        # 중복 확인
        existing_user = db.query(User).filter(User.hashed_password == code).first()
        if not existing_user:
            access_code = code
            break
    
    if not access_code:
        logger.error("Failed to generate unique access code after multiple attempts")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate unique access code"
        )
    
    # 새 일반 사용자 생성
    new_user = User(
        name=user_data.name,
        hashed_password=access_code,
        role=UserRole.USER,
        is_active=True,
        created_by=user_data.current_user_id
    )
    
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"User created successfully: ID={new_user.id}, access_code={access_code}")
        
        # 아무 ACTIVE 템플릿 조회 (관리자는 모든 템플릿 사용 가능)
        template = db.query(ProjectTemplate).filter(
            ProjectTemplate.status == TemplateStatus.ACTIVE
        ).first()

        if not template:
            logger.error(f"No active template found in the system")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active template found. Please create a template first."
            )
        
        logger.info(f"Using template: ID={template.id}, name={template.name}")
        
        # Environment 생성
        k8s_namespace = f"user-{new_user.id}"
        k8s_deployment_name = f"env-{new_user.id}-{template.id}"
        
        new_environment = EnvironmentInstance(
            name=f"{new_user.name}'s Environment",
            template_id=template.id,
            user_id=new_user.id,
            k8s_namespace=k8s_namespace,
            k8s_deployment_name=k8s_deployment_name,
            k8s_service_name=f"svc-{new_user.id}",
            status=EnvironmentStatus.PENDING,
            environment_config=template.environment_variables or {},
            port_mappings=template.exposed_ports or [],
            auto_stop_enabled=True
        )
        
        db.add(new_environment)
        db.commit()
        db.refresh(new_environment)
        
        logger.info(f"Environment created successfully: ID={new_environment.id}, namespace={k8s_namespace}")

        # KubeDevEnvironment CRD 생성 (컨트롤러가 자동으로 환경 프로비저닝)
        k8s_service = KubernetesService()
        try:
            # CRD 이름은 고유해야 함
            crd_name = f"env-user-{new_user.id}"
            crd_namespace = "kubdev-users"  # 모든 CRD는 kubdev-users 네임스페이스에 생성

            # 템플릿에서 리소스 제한 추출
            cpu_limit = template.resource_limits.get("cpu", "1000m") if template.resource_limits else "1000m"
            memory_limit = template.resource_limits.get("memory", "2Gi") if template.resource_limits else "2Gi"
            service_port = template.exposed_ports[0] if template.exposed_ports else 8080

            # KubeDevEnvironment CRD 객체 생성
            crd_object = {
                "apiVersion": "kubedev.my-project.com/v1alpha1",
                "kind": "KubeDevEnvironment",
                "metadata": {
                    "name": crd_name,
                    "namespace": crd_namespace
                },
                "spec": {
                    "userName": new_user.name,
                    "gitRepository": template.default_git_repo or "",
                    "image": template.base_image,
                    "commands": {
                        "init": "\n".join(template.init_scripts) if template.init_scripts else "",
                        "start": "\n".join(template.post_start_commands) if template.post_start_commands else ""
                    },
                    "ports": template.exposed_ports or [8080],
                    "storage": {
                        "size": template.resource_limits.get("storage", "10Gi") if template.resource_limits else "10Gi"
                    }
                }
            }

            # CRD 생성
            logger.info(f"Creating KubeDevEnvironment CRD: {crd_name}")
            await k8s_service.create_custom_object(crd_object)

            # Environment DB 업데이트 (CRD가 생성되면 컨트롤러가 처리)
            new_environment.k8s_namespace = crd_namespace
            new_environment.k8s_deployment_name = crd_name
            new_environment.status = EnvironmentStatus.CREATING
            new_environment.external_port = service_port
            db.commit()
            db.refresh(new_environment)

            logger.info(f"KubeDevEnvironment CRD created for environment {new_environment.id}")

        except Exception as k8s_error:
            logger.error(f"Failed to create KubeDevEnvironment CRD: {str(k8s_error)}")
            # CRD 생성 실패 시 환경 상태를 ERROR로 업데이트
            new_environment.status = EnvironmentStatus.ERROR
            new_environment.status_message = f"CRD creation failed: {str(k8s_error)}"
            db.commit()
            db.refresh(new_environment)
        
        # 응답 데이터 구성
        environment_data = UserCreateUserResponse.EnvironmentData(
            id=new_environment.id,
            template_id=template.id,
            user_id=new_user.id,
            status=new_environment.status.value,
            port=new_environment.external_port or 0,
            cpu=int(template.resource_limits.get("cpu", "1000m").replace("m", "")) if template.resource_limits else 1000,
            memory=int(template.resource_limits.get("memory", "2Gi").replace("Gi", "")) * 1024 if template.resource_limits else 2048
        )
        
        user_info = UserCreateUserResponse.UserData(
            id=new_user.id,
            name=new_user.name,
            role=new_user.role,
            access_code=access_code,
            is_active=new_user.is_active,
            created_at=new_user.created_at
        )
        
        return UserCreateUserResponse(
            user=user_info,
            environment=environment_data
        )
    
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create regular user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create regular user: {str(e)}"
        )


