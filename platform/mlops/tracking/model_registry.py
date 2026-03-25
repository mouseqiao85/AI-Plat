"""
模型版本管理模块
支持模型版本控制、注册、存储
"""

import os
import json
import uuid
import hashlib
import shutil
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ModelStage(str, Enum):
    """模型阶段"""
    NONE = "none"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"


class ModelStatus(str, Enum):
    """模型状态"""
    DRAFT = "draft"
    REGISTERED = "registered"
    DEPLOYED = "deployed"
    DEPRECATED = "deprecated"


class ModelVersion:
    """模型版本"""
    
    def __init__(
        self,
        model_id: str,
        version: str,
        name: str,
        framework: str = "sklearn"
    ):
        self.model_id = model_id
        self.version = version
        self.name = name
        self.framework = framework
        self.stage = ModelStage.NONE
        self.status = ModelStatus.DRAFT
        self.description = ""
        self.tags: List[str] = []
        self.source_path: Optional[str] = None
        self.run_id: Optional[str] = None
        self.experiment_id: Optional[str] = None
        self.metrics: Dict[str, float] = {}
        self.parameters: Dict[str, Any] = {}
        self.dependencies: List[str] = []
        self.signature: Optional[Dict[str, Any]] = None
        self.file_size: int = 0
        self.checksum: Optional[str] = None
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.created_by: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "version": self.version,
            "name": self.name,
            "framework": self.framework,
            "stage": self.stage.value,
            "status": self.status.value,
            "description": self.description,
            "tags": self.tags,
            "source_path": self.source_path,
            "run_id": self.run_id,
            "experiment_id": self.experiment_id,
            "metrics": self.metrics,
            "parameters": self.parameters,
            "dependencies": self.dependencies,
            "signature": self.signature,
            "file_size": self.file_size,
            "checksum": self.checksum,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by
        }


class RegisteredModel:
    """注册模型"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.tags: List[str] = []
        self.versions: Dict[str, ModelVersion] = {}
        self.latest_version: Optional[str] = None
        self.production_version: Optional[str] = None
        self.staging_version: Optional[str] = None
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "versions": {v: ver.to_dict() for v, ver in self.versions.items()},
            "latest_version": self.latest_version,
            "production_version": self.production_version,
            "staging_version": self.staging_version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class ModelRegistry:
    """模型注册表"""
    
    def __init__(self, registry_dir: str = "./model_registry"):
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.models: Dict[str, RegisteredModel] = {}
        self._load_registry()
    
    def _load_registry(self):
        """加载注册表"""
        registry_file = self.registry_dir / "registry.json"
        if registry_file.exists():
            try:
                with open(registry_file, 'r') as f:
                    data = json.load(f)
                    for model_data in data.get("models", []):
                        model = RegisteredModel(
                            name=model_data["name"],
                            description=model_data.get("description", "")
                        )
                        model.tags = model_data.get("tags", [])
                        model.latest_version = model_data.get("latest_version")
                        model.production_version = model_data.get("production_version")
                        model.staging_version = model_data.get("staging_version")
                        
                        for ver_str, ver_data in model_data.get("versions", {}).items():
                            version = ModelVersion(
                                model_id=ver_data["model_id"],
                                version=ver_data["version"],
                                name=ver_data["name"],
                                framework=ver_data.get("framework", "sklearn")
                            )
                            version.stage = ModelStage(ver_data.get("stage", "none"))
                            version.status = ModelStatus(ver_data.get("status", "draft"))
                            version.description = ver_data.get("description", "")
                            version.tags = ver_data.get("tags", [])
                            version.source_path = ver_data.get("source_path")
                            version.run_id = ver_data.get("run_id")
                            version.metrics = ver_data.get("metrics", {})
                            version.parameters = ver_data.get("parameters", {})
                            version.file_size = ver_data.get("file_size", 0)
                            version.checksum = ver_data.get("checksum")
                            model.versions[ver_str] = version
                        
                        self.models[model.name] = model
            except Exception as e:
                logger.error(f"加载模型注册表失败: {e}")
    
    def _save_registry(self):
        """保存注册表"""
        registry_file = self.registry_dir / "registry.json"
        data = {
            "models": [model.to_dict() for model in self.models.values()],
            "updated_at": datetime.utcnow().isoformat()
        }
        with open(registry_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def _calculate_checksum(self, file_path: str) -> str:
        """计算文件校验和"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for block in iter(lambda: f.read(65536), b''):
                sha256.update(block)
        return sha256.hexdigest()
    
    def _copy_model_file(self, source_path: str, model_name: str, version: str) -> str:
        """复制模型文件到注册表目录"""
        model_dir = self.registry_dir / "models" / model_name / version
        model_dir.mkdir(parents=True, exist_ok=True)
        
        dest_path = model_dir / os.path.basename(source_path)
        shutil.copy2(source_path, dest_path)
        
        return str(dest_path)
    
    def create_registered_model(
        self,
        name: str,
        description: str = "",
        tags: List[str] = None
    ) -> RegisteredModel:
        """创建注册模型"""
        if name in self.models:
            raise ValueError(f"模型已存在: {name}")
        
        model = RegisteredModel(name=name, description=description)
        if tags:
            model.tags = tags
        
        self.models[name] = model
        self._save_registry()
        
        logger.info(f"创建注册模型: {name}")
        return model
    
    def get_registered_model(self, name: str) -> Optional[RegisteredModel]:
        """获取注册模型"""
        return self.models.get(name)
    
    def list_registered_models(
        self,
        tags: List[str] = None
    ) -> List[RegisteredModel]:
        """列出注册模型"""
        models = list(self.models.values())
        
        if tags:
            models = [m for m in models if any(t in m.tags for t in tags)]
        
        return sorted(models, key=lambda m: m.updated_at, reverse=True)
    
    def delete_registered_model(self, name: str) -> bool:
        """删除注册模型"""
        if name in self.models:
            model_dir = self.registry_dir / "models" / name
            if model_dir.exists():
                shutil.rmtree(model_dir)
            del self.models[name]
            self._save_registry()
            return True
        return False
    
    def create_model_version(
        self,
        name: str,
        source_path: str,
        run_id: str = None,
        experiment_id: str = None,
        metrics: Dict[str, float] = None,
        parameters: Dict[str, Any] = None,
        description: str = "",
        tags: List[str] = None,
        framework: str = "sklearn"
    ) -> ModelVersion:
        """创建模型版本"""
        model = self.get_registered_model(name)
        if not model:
            model = self.create_registered_model(name)
        
        version_num = len(model.versions) + 1
        version_str = f"v{version_num}"
        
        model_id = str(uuid.uuid4())
        dest_path = self._copy_model_file(source_path, name, version_str)
        
        version = ModelVersion(
            model_id=model_id,
            version=version_str,
            name=name,
            framework=framework
        )
        version.description = description
        version.tags = tags or []
        version.source_path = dest_path
        version.run_id = run_id
        version.experiment_id = experiment_id
        version.metrics = metrics or {}
        version.parameters = parameters or {}
        version.file_size = os.path.getsize(dest_path)
        version.checksum = self._calculate_checksum(dest_path)
        version.status = ModelStatus.REGISTERED
        
        model.versions[version_str] = version
        model.latest_version = version_str
        model.updated_at = datetime.utcnow()
        
        self._save_registry()
        
        logger.info(f"创建模型版本: {name}@{version_str}")
        return version
    
    def get_model_version(
        self,
        name: str,
        version: str
    ) -> Optional[ModelVersion]:
        """获取模型版本"""
        model = self.get_registered_model(name)
        if model:
            return model.versions.get(version)
        return None
    
    def get_latest_version(self, name: str) -> Optional[ModelVersion]:
        """获取最新版本"""
        model = self.get_registered_model(name)
        if model and model.latest_version:
            return model.versions.get(model.latest_version)
        return None
    
    def get_production_version(self, name: str) -> Optional[ModelVersion]:
        """获取生产版本"""
        model = self.get_registered_model(name)
        if model and model.production_version:
            return model.versions.get(model.production_version)
        return None
    
    def transition_model_version_stage(
        self,
        name: str,
        version: str,
        stage: ModelStage,
        archive_existing: bool = True
    ) -> ModelVersion:
        """转换模型阶段"""
        model_version = self.get_model_version(name, version)
        if not model_version:
            raise ValueError(f"模型版本不存在: {name}@{version}")
        
        model = self.get_registered_model(name)
        
        if stage == ModelStage.PRODUCTION:
            if archive_existing and model.production_version:
                old_prod = model.versions.get(model.production_version)
                if old_prod:
                    old_prod.stage = ModelStage.ARCHIVED
            model.production_version = version
        
        elif stage == ModelStage.STAGING:
            if archive_existing and model.staging_version:
                old_staging = model.versions.get(model.staging_version)
                if old_staging:
                    old_staging.stage = ModelStage.ARCHIVED
            model.staging_version = version
        
        model_version.stage = stage
        model.updated_at = datetime.utcnow()
        model_version.updated_at = datetime.utcnow()
        
        self._save_registry()
        
        logger.info(f"转换模型阶段: {name}@{version} -> {stage.value}")
        return model_version
    
    def update_model_version(
        self,
        name: str,
        version: str,
        description: str = None,
        tags: List[str] = None
    ) -> ModelVersion:
        """更新模型版本"""
        model_version = self.get_model_version(name, version)
        if not model_version:
            raise ValueError(f"模型版本不存在: {name}@{version}")
        
        if description is not None:
            model_version.description = description
        
        if tags is not None:
            model_version.tags = tags
        
        model_version.updated_at = datetime.utcnow()
        
        model = self.get_registered_model(name)
        if model:
            model.updated_at = datetime.utcnow()
        
        self._save_registry()
        return model_version
    
    def delete_model_version(self, name: str, version: str) -> bool:
        """删除模型版本"""
        model = self.get_registered_model(name)
        if not model or version not in model.versions:
            return False
        
        if model.latest_version == version:
            versions = sorted(model.versions.keys(), reverse=True)
            if len(versions) > 1:
                model.latest_version = versions[1]
            else:
                model.latest_version = None
        
        if model.production_version == version:
            model.production_version = None
        
        if model.staging_version == version:
            model.staging_version = None
        
        version_dir = self.registry_dir / "models" / name / version
        if version_dir.exists():
            shutil.rmtree(version_dir)
        
        del model.versions[version]
        model.updated_at = datetime.utcnow()
        
        self._save_registry()
        return True
    
    def search_model_versions(
        self,
        filter_string: str = None,
        max_results: int = 100
    ) -> List[ModelVersion]:
        """搜索模型版本"""
        versions = []
        for model in self.models.values():
            versions.extend(model.versions.values())
        
        return sorted(versions, key=lambda v: v.created_at, reverse=True)[:max_results]
    
    def get_model_uri(self, name: str, version: str = None) -> str:
        """获取模型URI"""
        model_version = self.get_model_version(name, version) if version else self.get_latest_version(name)
        if not model_version:
            raise ValueError(f"模型版本不存在: {name}@{version}")
        return model_version.source_path
