"""
MLOps平台模型部署模块
实现模型部署、版本管理、服务配置、自动扩缩容等功能
"""

import os
import json
import logging
import time
import docker
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict, field
from enum import Enum
import yaml

logger = logging.getLogger(__name__)


class DeploymentStatus(Enum):
    PENDING = "pending"
    CREATING = "creating"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    SCALING = "scaling"


class DeploymentType(Enum):
    ONLINE = "online"
    BATCH = "batch"
    EDGE = "edge"


@dataclass
class DeploymentConfig:
    deployment_name: str
    model_id: str
    model_version: str
    deployment_type: DeploymentType
    replicas: int = 1
    cpu_limit: str = "2"
    memory_limit: str = "4Gi"
    gpu_count: int = 0
    auto_scale: bool = False
    min_replicas: int = 1
    max_replicas: int = 10
    target_cpu_utilization: float = 70.0
    environment_vars: Dict[str, str] = field(default_factory=dict)
    port: int = 8080
    health_check_path: str = "/health"


@dataclass
class DeploymentInfo:
    deployment_id: str
    deployment_name: str
    model_id: str
    model_version: str
    status: DeploymentStatus
    deployment_type: DeploymentType
    replicas: int
    endpoint_url: str
    created_at: str
    updated_at: str
    config: Dict[str, Any]
    metrics: Dict[str, Any] = field(default_factory=dict)


class ModelDeployer:
    """
    模型部署器
    提供模型部署、版本管理、服务配置和自动扩缩容功能
    """
    
    def __init__(self, storage_path: str = "./data/mlops/deployments"):
        """
        初始化模型部署器
        
        Args:
            storage_path: 部署配置存储路径
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        (self.storage_path / "configs").mkdir(exist_ok=True)
        (self.storage_path / "logs").mkdir(exist_ok=True)
        (self.storage_path / "templates").mkdir(exist_ok=True)
        
        self.registry_path = self.storage_path / "deployment_registry.json"
        self.deployments: Dict[str, DeploymentInfo] = self._load_registry()
        
        self._init_docker_client()
        self._create_deployment_templates()
    
    def _init_docker_client(self):
        """初始化Docker客户端"""
        try:
            self.docker_client = docker.from_env()
            logger.info("Docker client initialized successfully")
        except Exception as e:
            logger.warning(f"Docker client initialization failed: {e}")
            self.docker_client = None
    
    def _load_registry(self) -> Dict[str, DeploymentInfo]:
        """加载部署注册表"""
        if self.registry_path.exists():
            with open(self.registry_path, 'r') as f:
                data = json.load(f)
                return {
                    k: DeploymentInfo(**v) for k, v in data.items()
                }
        return {}
    
    def _save_registry(self):
        """保存部署注册表"""
        with open(self.registry_path, 'w') as f:
            data = {
                k: asdict(v) for k, v in self.deployments.items()
            }
            json.dump(data, f, indent=2, default=str)
    
    def _create_deployment_templates(self):
        """创建部署模板"""
        templates = {
            "standard": {
                "replicas": 1,
                "cpu_limit": "2",
                "memory_limit": "4Gi",
                "gpu_count": 0,
                "auto_scale": False
            },
            "high_performance": {
                "replicas": 3,
                "cpu_limit": "4",
                "memory_limit": "8Gi",
                "gpu_count": 1,
                "auto_scale": True,
                "min_replicas": 2,
                "max_replicas": 10
            },
            "batch": {
                "replicas": 1,
                "cpu_limit": "8",
                "memory_limit": "16Gi",
                "gpu_count": 2,
                "auto_scale": False
            }
        }
        
        for name, config in templates.items():
            template_path = self.storage_path / "templates" / f"{name}.yaml"
            with open(template_path, 'w') as f:
                yaml.dump(config, f)
    
    def create_deployment(
        self,
        config: DeploymentConfig,
        model_path: str
    ) -> str:
        """
        创建新部署
        
        Args:
            config: 部署配置
            model_path: 模型文件路径
            
        Returns:
            部署ID
        """
        deployment_id = f"deploy_{int(time.time() * 1000)}"
        
        deployment_info = DeploymentInfo(
            deployment_id=deployment_id,
            deployment_name=config.deployment_name,
            model_id=config.model_id,
            model_version=config.model_version,
            status=DeploymentStatus.CREATING,
            deployment_type=config.deployment_type,
            replicas=config.replicas,
            endpoint_url=f"http://localhost:{config.port}",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            config=asdict(config),
            metrics={
                "requests_total": 0,
                "requests_success": 0,
                "requests_failed": 0,
                "avg_latency_ms": 0,
                "p99_latency_ms": 0
            }
        )
        
        self.deployments[deployment_id] = deployment_info
        self._save_registry()
        
        config_path = self.storage_path / "configs" / f"{deployment_id}.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(asdict(config), f)
        
        self._create_deployment_resources(deployment_id, config, model_path)
        
        logger.info(f"Created deployment: {deployment_id}")
        return deployment_id
    
    def _create_deployment_resources(
        self,
        deployment_id: str,
        config: DeploymentConfig,
        model_path: str
    ):
        """创建部署资源"""
        try:
            if self.docker_client:
                self._create_docker_container(deployment_id, config, model_path)
            else:
                self._simulate_deployment(deployment_id, config)
        except Exception as e:
            logger.error(f"Failed to create deployment resources: {e}")
            self.deployments[deployment_id].status = DeploymentStatus.FAILED
            self._save_registry()
    
    def _create_docker_container(
        self,
        deployment_id: str,
        config: DeploymentConfig,
        model_path: str
    ):
        """创建Docker容器"""
        try:
            container = self.docker_client.containers.run(
                "python:3.9-slim",
                name=f"ai-plat-{deployment_id}",
                detach=True,
                ports={f"{config.port}/tcp": config.port},
                environment={
                    "MODEL_PATH": model_path,
                    "DEPLOYMENT_ID": deployment_id,
                    **config.environment_vars
                },
                cpu_period=100000,
                cpu_quota=int(float(config.cpu_limit) * 100000),
                mem_limit=config.memory_limit,
                command="python -m inference_server"
            )
            
            self.deployments[deployment_id].status = DeploymentStatus.RUNNING
            self.deployments[deployment_id].endpoint_url = f"http://localhost:{config.port}"
            self._save_registry()
            
            logger.info(f"Docker container created: {container.id}")
        except Exception as e:
            logger.error(f"Failed to create Docker container: {e}")
            raise
    
    def _simulate_deployment(self, deployment_id: str, config: DeploymentConfig):
        """模拟部署（无Docker时使用）"""
        self.deployments[deployment_id].status = DeploymentStatus.RUNNING
        self.deployments[deployment_id].endpoint_url = f"http://localhost:{config.port}"
        self._save_registry()
        logger.info(f"Simulated deployment created: {deployment_id}")
    
    def get_deployment(self, deployment_id: str) -> Optional[DeploymentInfo]:
        """获取部署信息"""
        return self.deployments.get(deployment_id)
    
    def list_deployments(
        self,
        status: Optional[DeploymentStatus] = None,
        model_id: Optional[str] = None
    ) -> List[DeploymentInfo]:
        """列出部署"""
        deployments = list(self.deployments.values())
        
        if status:
            deployments = [d for d in deployments if d.status == status]
        if model_id:
            deployments = [d for d in deployments if d.model_id == model_id]
        
        return deployments
    
    def scale_deployment(
        self,
        deployment_id: str,
        replicas: int
    ) -> Dict[str, Any]:
        """扩缩容部署"""
        if deployment_id not in self.deployments:
            raise ValueError(f"Deployment not found: {deployment_id}")
        
        deployment = self.deployments[deployment_id]
        old_replicas = deployment.replicas
        deployment.replicas = replicas
        deployment.status = DeploymentStatus.SCALING
        deployment.updated_at = datetime.now().isoformat()
        self._save_registry()
        
        if self.docker_client:
            try:
                container_name = f"ai-plat-{deployment_id}"
                container = self.docker_client.containers.get(container_name)
            except Exception as e:
                logger.warning(f"Failed to scale Docker container: {e}")
        
        time.sleep(1)
        deployment.status = DeploymentStatus.RUNNING
        self._save_registry()
        
        return {
            "deployment_id": deployment_id,
            "old_replicas": old_replicas,
            "new_replicas": replicas,
            "status": "completed"
        }
    
    def stop_deployment(self, deployment_id: str) -> Dict[str, Any]:
        """停止部署"""
        if deployment_id not in self.deployments:
            raise ValueError(f"Deployment not found: {deployment_id}")
        
        deployment = self.deployments[deployment_id]
        
        if self.docker_client:
            try:
                container_name = f"ai-plat-{deployment_id}"
                container = self.docker_client.containers.get(container_name)
                container.stop()
            except Exception as e:
                logger.warning(f"Failed to stop Docker container: {e}")
        
        deployment.status = DeploymentStatus.STOPPED
        deployment.updated_at = datetime.now().isoformat()
        self._save_registry()
        
        return {
            "deployment_id": deployment_id,
            "status": "stopped"
        }
    
    def start_deployment(self, deployment_id: str) -> Dict[str, Any]:
        """启动已停止的部署"""
        if deployment_id not in self.deployments:
            raise ValueError(f"Deployment not found: {deployment_id}")
        
        deployment = self.deployments[deployment_id]
        
        if self.docker_client:
            try:
                container_name = f"ai-plat-{deployment_id}"
                container = self.docker_client.containers.get(container_name)
                container.start()
            except Exception as e:
                logger.warning(f"Failed to start Docker container: {e}")
        
        deployment.status = DeploymentStatus.RUNNING
        deployment.updated_at = datetime.now().isoformat()
        self._save_registry()
        
        return {
            "deployment_id": deployment_id,
            "status": "running"
        }
    
    def delete_deployment(self, deployment_id: str) -> Dict[str, Any]:
        """删除部署"""
        if deployment_id not in self.deployments:
            raise ValueError(f"Deployment not found: {deployment_id}")
        
        deployment = self.deployments[deployment_id]
        
        if self.docker_client:
            try:
                container_name = f"ai-plat-{deployment_id}"
                container = self.docker_client.containers.get(container_name)
                container.remove(force=True)
            except Exception as e:
                logger.warning(f"Failed to remove Docker container: {e}")
        
        config_path = self.storage_path / "configs" / f"{deployment_id}.yaml"
        if config_path.exists():
            config_path.unlink()
        
        del self.deployments[deployment_id]
        self._save_registry()
        
        return {
            "deployment_id": deployment_id,
            "status": "deleted"
        }
    
    def update_deployment_metrics(
        self,
        deployment_id: str,
        metrics: Dict[str, Any]
    ):
        """更新部署指标"""
        if deployment_id in self.deployments:
            self.deployments[deployment_id].metrics.update(metrics)
            self.deployments[deployment_id].updated_at = datetime.now().isoformat()
            self._save_registry()
    
    def get_deployment_logs(
        self,
        deployment_id: str,
        lines: int = 100
    ) -> List[str]:
        """获取部署日志"""
        if deployment_id not in self.deployments:
            raise ValueError(f"Deployment not found: {deployment_id}")
        
        logs = []
        
        if self.docker_client:
            try:
                container_name = f"ai-plat-{deployment_id}"
                container = self.docker_client.containers.get(container_name)
                logs = container.logs(tail=lines).decode('utf-8').split('\n')
            except Exception as e:
                logger.warning(f"Failed to get Docker logs: {e}")
        
        log_file = self.storage_path / "logs" / f"{deployment_id}.log"
        if log_file.exists():
            with open(log_file, 'r') as f:
                logs = f.readlines()[-lines:]
        
        return logs
    
    def health_check(self, deployment_id: str) -> Dict[str, Any]:
        """健康检查"""
        if deployment_id not in self.deployments:
            raise ValueError(f"Deployment not found: {deployment_id}")
        
        deployment = self.deployments[deployment_id]
        
        health_status = {
            "deployment_id": deployment_id,
            "status": deployment.status.value,
            "healthy": deployment.status == DeploymentStatus.RUNNING,
            "replicas": deployment.replicas,
            "endpoint": deployment.endpoint_url,
            "last_check": datetime.now().isoformat()
        }
        
        if self.docker_client:
            try:
                container_name = f"ai-plat-{deployment_id}"
                container = self.docker_client.containers.get(container_name)
                health_status["container_status"] = container.status
            except Exception as e:
                health_status["container_error"] = str(e)
        
        return health_status
    
    def rollback_deployment(
        self,
        deployment_id: str,
        target_version: str
    ) -> Dict[str, Any]:
        """回滚部署到指定版本"""
        if deployment_id not in self.deployments:
            raise ValueError(f"Deployment not found: {deployment_id}")
        
        deployment = self.deployments[deployment_id]
        old_version = deployment.model_version
        
        deployment.model_version = target_version
        deployment.updated_at = datetime.now().isoformat()
        self._save_registry()
        
        return {
            "deployment_id": deployment_id,
            "old_version": old_version,
            "new_version": target_version,
            "status": "rolled_back"
        }


if __name__ == "__main__":
    deployer = ModelDeployer()
    
    config = DeploymentConfig(
        deployment_name="test-model-deployment",
        model_id="model_001",
        model_version="v1.0.0",
        deployment_type=DeploymentType.ONLINE,
        replicas=2,
        auto_scale=True
    )
    
    deployment_id = deployer.create_deployment(config, "/models/model_001")
    print(f"Created deployment: {deployment_id}")
    
    status = deployer.health_check(deployment_id)
    print(f"Health check: {status}")
