"""
Dockerfile Generator Service (Development Mock Version)
개발용 Dockerfile 생성 서비스 목업 - Docker 클라이언트 없이 테스트 가능
"""

import os
import tempfile
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class DockerfileGenerator:
    """Dockerfile 자동 생성 서비스 (개발용 목업)"""

    def __init__(self):
        # 개발용: 실제 Docker 클라이언트 연결 없이 목업 사용
        self.mock_mode = True
        print("🐳 DockerfileGenerator initialized in mock mode for development")

        self.base_images = {
            "node": {
                "16": "node:16-alpine",
                "18": "node:18-alpine",
                "20": "node:20-alpine"
            },
            "python": {
                "3.9": "python:3.9-slim",
                "3.10": "python:3.10-slim",
                "3.11": "python:3.11-slim"
            },
            "java": {
                "11": "openjdk:11-jre-slim",
                "17": "openjdk:17-jre-slim",
                "21": "openjdk:21-jre-slim"
            },
            "go": {
                "1.19": "golang:1.19-alpine",
                "1.20": "golang:1.20-alpine",
                "1.21": "golang:1.21-alpine"
            }
        }

    def generate_dockerfile(self, stack_config: Dict, environment_id: str) -> str:
        """스택 설정에 따라 Dockerfile 생성 (목업)"""

        language = stack_config.get("language", "node")
        version = stack_config.get("version", "18")
        framework = stack_config.get("framework", "")
        packages = stack_config.get("packages", [])

        print(f"🔨 Mock: Generating Dockerfile for {language} {version} with framework {framework}")

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
            "# 포트 노출",
            "EXPOSE 8080",
            "",
            "# 시작 명령",
            'CMD ["code-server", "--bind-addr", "0.0.0.0:8080", "--auth", "none", "/workspace"]'
        ])

        dockerfile_content = "\n".join(dockerfile_lines)
        print(f"📄 Mock: Generated Dockerfile with {len(dockerfile_lines)} lines")
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
                "RUN pip install django",
                "RUN django-admin startproject demo_app /workspace/demo_app",
                "WORKDIR /workspace/demo_app",
            ])
        elif framework == "flask":
            lines.extend([
                "# Flask 개발 환경",
                "RUN pip install flask",
                "COPY app.py /workspace/",
                'RUN echo "from flask import Flask\\napp = Flask(__name__)\\n@app.route(\'/\')\\ndef hello():\\n    return \'Hello KubeDev!\'\\nif __name__ == \'__main__\':\\n    app.run(debug=True)" > /workspace/app.py',
            ])
        elif framework == "fastapi":
            lines.extend([
                "# FastAPI 개발 환경",
                "RUN pip install fastapi uvicorn",
                "COPY main.py /workspace/",
                'RUN echo "from fastapi import FastAPI\\napp = FastAPI()\\n@app.get(\'/\')\\ndef read_root():\\n    return {\'Hello\': \'KubeDev\'}" > /workspace/main.py',
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
            "RUN apt-get update && apt-get install -y curl maven",
            "",
        ]

        if framework == "spring":
            lines.extend([
                "# Spring Boot 개발 환경",
                "RUN curl https://start.spring.io/starter.zip -d dependencies=web -d name=demo-app -o demo-app.zip",
                "RUN unzip demo-app.zip && rm demo-app.zip",
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
            "",
        ]

        if framework == "gin":
            lines.extend([
                "# Gin 개발 환경",
                "RUN go mod init demo-app",
                "RUN go get github.com/gin-gonic/gin",
                'RUN echo "package main\\nimport \\"github.com/gin-gonic/gin\\"\\nfunc main() {\\n    r := gin.Default()\\n    r.GET(\\"/\\", func(c *gin.Context) {\\n        c.JSON(200, gin.H{\\"message\\": \\"Hello KubeDev!\\"})\\n    })\\n    r.Run(\\\":8080\\")\\n}" > main.go',
            ])

        return lines

    async def build_and_push_image(self, dockerfile_content: str, image_tag: str) -> Tuple[bool, str]:
        """Docker 이미지 빌드 및 푸시 (목업)"""
        print(f"🚢 Mock: Building and pushing image '{image_tag}'")

        # 목업: 실제로는 빌드하지 않고 성공으로 반환
        await asyncio.sleep(1)  # 빌드 시간 시뮬레이션

        return True, f"Successfully built and pushed {image_tag}"

    async def validate_dockerfile(self, dockerfile_content: str) -> Tuple[bool, str]:
        """Dockerfile 유효성 검사 (목업)"""
        print("✅ Mock: Validating Dockerfile")

        # 기본 유효성 검사
        if "FROM " not in dockerfile_content:
            return False, "Dockerfile must contain a FROM instruction"

        if "WORKDIR " not in dockerfile_content:
            return False, "Dockerfile should contain a WORKDIR instruction"

        return True, "Dockerfile validation passed"

    def get_supported_stacks(self) -> Dict[str, List[str]]:
        """지원되는 스택 목록 조회"""
        return {
            "languages": list(self.base_images.keys()),
            "frameworks": {
                "node": ["react", "vue", "express", "nestjs", "next"],
                "python": ["django", "flask", "fastapi", "jupyter"],
                "java": ["spring", "maven", "gradle"],
                "go": ["gin", "echo", "fiber"]
            },
            "versions": self.base_images
        }

    async def cleanup_temp_files(self, environment_id: str):
        """임시 파일 정리 (목업)"""
        print(f"🧹 Mock: Cleaning up temp files for environment {environment_id}")
        pass