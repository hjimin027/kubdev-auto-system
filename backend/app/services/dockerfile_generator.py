"""
Dockerfile Generator Service
스택 설정에 따라 Dockerfile을 자동 생성하고 Docker 이미지를 빌드하는 서비스
"""

import os
import tempfile
import docker
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class DockerfileGenerator:
    """Dockerfile 자동 생성 및 Docker 이미지 빌드 서비스"""

    def __init__(self):
        """Docker 클라이언트 초기화"""
        try:
            self.docker_client = docker.from_env()
            # Docker 연결 테스트
            self.docker_client.ping()
            self.docker_available = True
            logger.info("Docker client connected successfully")
        except Exception as e:
            logger.warning(f"Docker not available: {str(e)}. Image building will be disabled.")
            self.docker_available = False

        self.base_images = {
            "node": {
                "16": "node:16-alpine",
                "18": "node:18-alpine",
                "20": "node:20-alpine",
                "21": "node:21-alpine"
            },
            "python": {
                "3.9": "python:3.9-slim",
                "3.10": "python:3.10-slim",
                "3.11": "python:3.11-slim",
                "3.12": "python:3.12-slim"
            },
            "java": {
                "11": "openjdk:11-jre-slim",
                "17": "openjdk:17-jre-slim",
                "21": "openjdk:21-jre-slim"
            },
            "go": {
                "1.19": "golang:1.19-alpine",
                "1.20": "golang:1.20-alpine",
                "1.21": "golang:1.21-alpine",
                "1.22": "golang:1.22-alpine"
            }
        }

    def _check_docker_availability(self):
        """Docker 연결 상태 확인"""
        if not self.docker_available:
            raise Exception("Docker is not available. Please check if Docker Desktop is running.")

    def generate_dockerfile(self, stack_config: Dict, environment_id: str) -> str:
        """스택 설정에 따라 Dockerfile 생성"""

        language = stack_config.get("language", "node")
        version = stack_config.get("version", "18")
        framework = stack_config.get("framework", "")
        packages = stack_config.get("packages", [])

        logger.info(f"Generating Dockerfile for {language} {version} with framework {framework}")

        # 베이스 이미지 선택
        base_image = self.base_images.get(language, {}).get(version, f"{language}:latest")

        # Dockerfile 생성
        dockerfile_lines = [
            f"# Auto-generated Dockerfile for KubeDev Environment {environment_id}",
            f"# Language: {language} {version}, Framework: {framework}",
            f"# Generated at: {datetime.utcnow().isoformat()}Z",
            "",
            f"FROM {base_image}",
            "",
            "# 시스템 업데이트 및 기본 도구 설치",
            "RUN apt-get update && apt-get install -y \\",
            "    curl \\",
            "    wget \\",
            "    git \\",
            "    vim \\",
            "    nano \\",
            "    && rm -rf /var/lib/apt/lists/*",
            "",
            "# 작업 디렉토리 설정",
            "WORKDIR /workspace",
            "",
        ]

        # 언어별 설정
        if language == "node":
            dockerfile_lines.extend(self._generate_node_config(framework, packages))
        elif language == "python":
            dockerfile_lines.extend(self._generate_python_config(framework, packages))
        elif language == "java":
            dockerfile_lines.extend(self._generate_java_config(framework, packages))
        elif language == "go":
            dockerfile_lines.extend(self._generate_go_config(framework, packages))

        # 공통 설정 추가
        dockerfile_lines.extend([
            "",
            "# VS Code Server 설치 (개발환경용)",
            "RUN curl -fsSL https://code-server.dev/install.sh | sh",
            "",
            "# 환경 변수 설정",
            "ENV KUBDEV_ENVIRONMENT=true",
            f"ENV KUBDEV_LANGUAGE={language}",
            f"ENV KUBDEV_VERSION={version}",
            f"ENV KUBDEV_FRAMEWORK={framework}",
            "",
            "# 포트 노출",
            "EXPOSE 8080",
            "",
            "# 헬스체크",
            "HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\",
            "  CMD curl -f http://localhost:8080/ || exit 1",
            "",
            "# 시작 명령",
            'CMD ["code-server", "--bind-addr", "0.0.0.0:8080", "--auth", "none", "/workspace"]'
        ])

        dockerfile_content = "\n".join(dockerfile_lines)
        logger.info(f"Generated Dockerfile with {len(dockerfile_lines)} lines")
        return dockerfile_content

    def _generate_node_config(self, framework: str, packages: List[str]) -> List[str]:
        """Node.js 설정 생성"""
        lines = [
            "# Node.js 설정",
            "RUN npm install -g npm@latest",
            "",
        ]

        if framework == "react":
            lines.extend([
                "# React 개발 환경",
                "RUN npm install -g create-react-app",
                "RUN npx create-react-app demo-app --template typescript",
                "WORKDIR /workspace/demo-app",
                "RUN npm install",
            ])
        elif framework == "vue":
            lines.extend([
                "# Vue.js 개발 환경",
                "RUN npm install -g @vue/cli",
                "RUN vue create demo-app --default",
                "WORKDIR /workspace/demo-app",
            ])
        elif framework == "express":
            lines.extend([
                "# Express.js 개발 환경",
                "RUN npm install -g express-generator",
                "RUN express demo-app",
                "WORKDIR /workspace/demo-app",
                "RUN npm install",
            ])
        elif framework == "nestjs":
            lines.extend([
                "# NestJS 개발 환경",
                "RUN npm install -g @nestjs/cli",
                "RUN nest new demo-app --package-manager npm",
                "WORKDIR /workspace/demo-app",
            ])
        elif framework == "next":
            lines.extend([
                "# Next.js 개발 환경",
                "RUN npx create-next-app@latest demo-app --typescript --tailwind --eslint",
                "WORKDIR /workspace/demo-app",
                "RUN npm install",
            ])

        # 추가 패키지 설치
        if packages:
            packages_str = " ".join(packages)
            lines.append(f"RUN npm install {packages_str}")

        return lines

    def _generate_python_config(self, framework: str, packages: List[str]) -> List[str]:
        """Python 설정 생성"""
        lines = [
            "# Python 설정",
            "RUN pip install --upgrade pip",
            "",
        ]

        if framework == "django":
            lines.extend([
                "# Django 개발 환경",
                "RUN pip install django djangorestframework",
                "RUN django-admin startproject demo_app /workspace/demo_app",
                "WORKDIR /workspace/demo_app",
                'RUN echo "ALLOWED_HOSTS = [\'*\']" >> demo_app/settings.py',
            ])
        elif framework == "flask":
            lines.extend([
                "# Flask 개발 환경",
                "RUN pip install flask flask-restful flask-cors",
                'RUN echo "from flask import Flask\\nfrom flask_cors import CORS\\n\\napp = Flask(__name__)\\nCORS(app)\\n\\n@app.route(\'/\')\\ndef hello():\\n    return {\'message\': \'Hello KubeDev!\', \'framework\': \'Flask\'}\\n\\nif __name__ == \'__main__\':\\n    app.run(debug=True, host=\'0.0.0.0\')" > /workspace/app.py',
            ])
        elif framework == "fastapi":
            lines.extend([
                "# FastAPI 개발 환경",
                "RUN pip install fastapi uvicorn python-multipart",
                'RUN echo "from fastapi import FastAPI\\nfrom fastapi.middleware.cors import CORSMiddleware\\n\\napp = FastAPI()\\n\\napp.add_middleware(\\n    CORSMiddleware,\\n    allow_origins=[\'*\'],\\n    allow_credentials=True,\\n    allow_methods=[\'*\'],\\n    allow_headers=[\'*\']\\n)\\n\\n@app.get(\'/\')\\ndef read_root():\\n    return {\'message\': \'Hello KubeDev!\', \'framework\': \'FastAPI\'}" > /workspace/main.py',
            ])
        elif framework == "jupyter":
            lines.extend([
                "# Jupyter 개발 환경",
                "RUN pip install jupyter notebook jupyterlab pandas numpy matplotlib seaborn",
                "RUN jupyter notebook --generate-config",
                'RUN echo "c.NotebookApp.ip = \'0.0.0.0\'\\nc.NotebookApp.port = 8080\\nc.NotebookApp.open_browser = False\\nc.NotebookApp.allow_root = True\\nc.NotebookApp.token = \'\'\\nc.NotebookApp.password = \'\'" >> ~/.jupyter/jupyter_notebook_config.py',
                'CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=8080", "--no-browser", "--allow-root"]',
            ])

        # 추가 패키지 설치
        if packages:
            packages_str = " ".join(packages)
            lines.append(f"RUN pip install {packages_str}")

        return lines

    def _generate_java_config(self, framework: str, packages: List[str]) -> List[str]:
        """Java 설정 생성"""
        lines = [
            "# Java 설정",
            "RUN apt-get update && apt-get install -y curl maven gradle && rm -rf /var/lib/apt/lists/*",
            "",
        ]

        if framework == "spring":
            lines.extend([
                "# Spring Boot 개발 환경",
                "RUN curl https://start.spring.io/starter.zip \\",
                "    -d dependencies=web,devtools,actuator \\",
                "    -d name=demo-app \\",
                "    -d packageName=com.kubdev.demo \\",
                "    -o demo-app.zip",
                "RUN unzip demo-app.zip && rm demo-app.zip",
                "WORKDIR /workspace/demo-app",
                "RUN mvn clean compile",
            ])
        elif framework == "maven":
            lines.extend([
                "# Maven 프로젝트 템플릿",
                "RUN mvn archetype:generate \\",
                "    -DgroupId=com.kubdev.demo \\",
                "    -DartifactId=demo-app \\",
                "    -DarchetypeArtifactId=maven-archetype-quickstart \\",
                "    -DinteractiveMode=false",
                "WORKDIR /workspace/demo-app",
                "RUN mvn clean compile",
            ])

        return lines

    def _generate_go_config(self, framework: str, packages: List[str]) -> List[str]:
        """Go 설정 생성"""
        lines = [
            "# Go 설정",
            "RUN apk add --no-cache git",
            "ENV GO111MODULE=on",
            "ENV GOPROXY=https://proxy.golang.org,direct",
            "",
        ]

        if framework == "gin":
            lines.extend([
                "# Gin 개발 환경",
                "RUN go mod init demo-app",
                "RUN go get github.com/gin-gonic/gin",
                'RUN echo "package main\\n\\nimport (\\n    \\"net/http\\"\\n    \\"github.com/gin-gonic/gin\\"\\n)\\n\\nfunc main() {\\n    r := gin.Default()\\n\\n    r.GET(\\"/\\", func(c *gin.Context) {\\n        c.JSON(http.StatusOK, gin.H{\\n            \\"message\\": \\"Hello KubeDev!\\",\\n            \\"framework\\": \\"Gin\\",\\n        })\\n    })\\n\\n    r.Run(\\\":8080\\")\\n}" > main.go',
                "RUN go mod tidy",
            ])
        elif framework == "echo":
            lines.extend([
                "# Echo 개발 환경",
                "RUN go mod init demo-app",
                "RUN go get github.com/labstack/echo/v4",
                'RUN echo "package main\\n\\nimport (\\n    \\"net/http\\"\\n    \\"github.com/labstack/echo/v4\\"\\n    \\"github.com/labstack/echo/v4/middleware\\"\\n)\\n\\nfunc main() {\\n    e := echo.New()\\n\\n    e.Use(middleware.Logger())\\n    e.Use(middleware.Recover())\\n\\n    e.GET(\\"/\\", func(c echo.Context) error {\\n        return c.JSON(http.StatusOK, map[string]string{\\n            \\"message\\": \\"Hello KubeDev!\\",\\n            \\"framework\\": \\"Echo\\",\\n        })\\n    })\\n\\n    e.Logger.Fatal(e.Start(\\\":8080\\"))\\n}" > main.go',
                "RUN go mod tidy",
            ])

        return lines

    async def build_and_push_image(self, dockerfile_content: str, image_tag: str,
                                   build_context: Optional[str] = None) -> Tuple[bool, str]:
        """Docker 이미지 빌드 및 푸시"""
        self._check_docker_availability()

        try:
            # 임시 디렉토리에 Dockerfile 생성
            with tempfile.TemporaryDirectory() as temp_dir:
                dockerfile_path = os.path.join(temp_dir, "Dockerfile")

                with open(dockerfile_path, "w", encoding="utf-8") as f:
                    f.write(dockerfile_content)

                # 빌드 컨텍스트 설정
                build_path = build_context if build_context else temp_dir

                logger.info(f"Building Docker image: {image_tag}")

                # 이미지 빌드 (동기 방식)
                def build_image():
                    try:
                        image, build_logs = self.docker_client.images.build(
                            path=build_path,
                            tag=image_tag,
                            rm=True,
                            forcerm=True
                        )

                        # 빌드 로그 출력
                        for log in build_logs:
                            if 'stream' in log:
                                logger.debug(f"Build: {log['stream'].strip()}")

                        return image, "Build successful"
                    except Exception as e:
                        logger.error(f"Build failed: {str(e)}")
                        raise

                # 비동기로 실행
                loop = asyncio.get_event_loop()
                image, message = await loop.run_in_executor(None, build_image)

                logger.info(f"Successfully built image: {image_tag}")

                # 옵션: 이미지를 레지스트리에 푸시 (현재는 로컬에만 저장)
                # if settings.DOCKER_REGISTRY:
                #     await self._push_image(image_tag)

                return True, f"Successfully built image: {image_tag}"

        except Exception as e:
            error_msg = f"Failed to build image: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    async def _push_image(self, image_tag: str) -> bool:
        """이미지를 레지스트리에 푸시"""
        try:
            def push_image():
                return self.docker_client.images.push(image_tag)

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, push_image)

            logger.info(f"Successfully pushed image: {image_tag}")
            return True
        except Exception as e:
            logger.error(f"Failed to push image: {str(e)}")
            return False

    async def validate_dockerfile(self, dockerfile_content: str) -> Tuple[bool, str]:
        """Dockerfile 유효성 검사"""
        try:
            # 기본 구문 검사
            if "FROM " not in dockerfile_content:
                return False, "Dockerfile must contain a FROM instruction"

            if "WORKDIR " not in dockerfile_content:
                return False, "Dockerfile should contain a WORKDIR instruction"

            # 보안 검사
            dangerous_commands = ["rm -rf /", "chmod 777", "sudo", "--privileged"]
            for cmd in dangerous_commands:
                if cmd in dockerfile_content:
                    return False, f"Potentially dangerous command detected: {cmd}"

            # 베이스 이미지 검증
            from_lines = [line.strip() for line in dockerfile_content.split('\n')
                         if line.strip().startswith('FROM ')]

            if not from_lines:
                return False, "No FROM instruction found"

            # Docker 빌드 시뮬레이션 (선택사항)
            if self.docker_available:
                try:
                    # 임시 파일로 빌드 테스트 (실제로는 빌드하지 않음)
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.dockerfile', delete=False) as f:
                        f.write(dockerfile_content)
                        f.flush()

                        # Docker 파일 구문 검사만 수행
                        # self.docker_client.api.build(path=os.path.dirname(f.name),
                        #                             dockerfile=os.path.basename(f.name),
                        #                             rm=True, pull=False, nocache=False)

                    os.unlink(f.name)
                except Exception as e:
                    return False, f"Docker validation failed: {str(e)}"

            logger.info("Dockerfile validation passed")
            return True, "Dockerfile validation passed"

        except Exception as e:
            logger.error(f"Dockerfile validation error: {str(e)}")
            return False, f"Validation error: {str(e)}"

    def get_supported_stacks(self) -> Dict[str, Any]:
        """지원되는 스택 목록 조회"""
        return {
            "languages": list(self.base_images.keys()),
            "frameworks": {
                "node": ["react", "vue", "express", "nestjs", "next"],
                "python": ["django", "flask", "fastapi", "jupyter"],
                "java": ["spring", "maven", "gradle"],
                "go": ["gin", "echo", "fiber"]
            },
            "versions": self.base_images,
            "features": {
                "docker_available": self.docker_available,
                "build_supported": self.docker_available,
                "push_supported": self.docker_available and bool(getattr(settings, 'DOCKER_REGISTRY', None))
            }
        }

    async def cleanup_temp_files(self, environment_id: str):
        """임시 파일 정리"""
        try:
            # 환경 ID로 생성된 임시 파일들 정리
            temp_pattern = f"kubdev-{environment_id}-*"
            temp_dir = tempfile.gettempdir()

            for filename in os.listdir(temp_dir):
                if filename.startswith(f"kubdev-{environment_id}-"):
                    file_path = os.path.join(temp_dir, filename)
                    try:
                        os.remove(file_path)
                        logger.debug(f"Cleaned up temp file: {file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to clean up {file_path}: {str(e)}")

            logger.info(f"Cleaned up temp files for environment {environment_id}")
        except Exception as e:
            logger.error(f"Failed to cleanup temp files: {str(e)}")

    async def list_images(self, kubdev_only: bool = True) -> List[Dict[str, Any]]:
        """로컬 Docker 이미지 목록 조회"""
        if not self.docker_available:
            return []

        try:
            def get_images():
                return self.docker_client.images.list()

            loop = asyncio.get_event_loop()
            images = await loop.run_in_executor(None, get_images)

            image_list = []
            for image in images:
                tags = image.tags or ["<none>:<none>"]

                # KubeDev 이미지만 필터링
                if kubdev_only:
                    kubdev_tags = [tag for tag in tags if "kubdev" in tag.lower()]
                    if not kubdev_tags:
                        continue
                    tags = kubdev_tags

                image_list.append({
                    "id": image.id,
                    "tags": tags,
                    "created": image.attrs.get("Created"),
                    "size": image.attrs.get("Size", 0),
                    "size_mb": round(image.attrs.get("Size", 0) / (1024 * 1024), 2)
                })

            return sorted(image_list, key=lambda x: x["created"], reverse=True)
        except Exception as e:
            logger.error(f"Failed to list images: {str(e)}")
            return []

    async def remove_image(self, image_tag: str) -> Tuple[bool, str]:
        """Docker 이미지 삭제"""
        self._check_docker_availability()

        try:
            def remove_image():
                self.docker_client.images.remove(image_tag, force=True)
                return True

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, remove_image)

            logger.info(f"Removed Docker image: {image_tag}")
            return True, f"Successfully removed image: {image_tag}"
        except Exception as e:
            error_msg = f"Failed to remove image: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def get_docker_info(self) -> Dict[str, Any]:
        """Docker 시스템 정보 조회"""
        if not self.docker_available:
            return {"available": False, "error": "Docker not available"}

        try:
            info = self.docker_client.info()
            return {
                "available": True,
                "version": self.docker_client.version(),
                "containers": info.get("Containers", 0),
                "images": info.get("Images", 0),
                "server_version": info.get("ServerVersion"),
                "storage_driver": info.get("Driver"),
                "total_memory": info.get("MemTotal", 0),
                "cpus": info.get("NCPU", 0)
            }
        except Exception as e:
            logger.error(f"Failed to get Docker info: {str(e)}")
            return {"available": False, "error": str(e)}