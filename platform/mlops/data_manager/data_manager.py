"""
MLOps平台数据管理模块
实现数据集版本控制、数据质量检测、数据标注工具集成、数据预处理管道
"""

import os
import json
import hashlib
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class DatasetStatus(Enum):
    """数据集状态"""
    DRAFT = "draft"
    VALIDATING = "validating"
    READY = "ready"
    ARCHIVED = "archived"


class DataType(Enum):
    """数据类型"""
    TABULAR = "tabular"
    IMAGE = "image"
    TEXT = "text"
    AUDIO = "audio"
    VIDEO = "video"
    TIME_SERIES = "time_series"


@dataclass
class DatasetVersion:
    """数据集版本"""
    version_id: str
    version_number: str
    created_at: str
    created_by: str
    description: str
    file_hash: str
    file_size: int
    record_count: int
    feature_count: int
    tags: List[str]
    parent_version: Optional[str] = None


@dataclass
class DataQualityReport:
    """数据质量报告"""
    dataset_id: str
    version: str
    checked_at: str
    total_records: int
    valid_records: int
    invalid_records: int
    missing_rate: float
    duplicate_rate: float
    quality_score: float
    issues: List[Dict[str, Any]]
    recommendations: List[str]


class DataManager:
    """
    数据管理器
    提供数据集版本控制、质量检测、标注管理和预处理功能
    """
    
    def __init__(self, storage_path: str = "./data/mlops"):
        """
        初始化数据管理器
        
        Args:
            storage_path: 数据存储路径
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 创建子目录
        (self.storage_path / "datasets").mkdir(exist_ok=True)
        (self.storage_path / "versions").mkdir(exist_ok=True)
        (self.storage_path / "annotations").mkdir(exist_ok=True)
        (self.storage_path / "pipelines").mkdir(exist_ok=True)
        (self.storage_path / "reports").mkdir(exist_ok=True)
        
        # 数据集注册表
        self.registry_path = self.storage_path / "registry.json"
        self.registry = self._load_registry()
        
        # 质量规则
        self.quality_rules = self._initialize_quality_rules()
        
    def _load_registry(self) -> Dict:
        """加载数据集注册表"""
        if self.registry_path.exists():
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"datasets": {}, "version_history": []}
    
    def _save_registry(self):
        """保存数据集注册表"""
        with open(self.registry_path, 'w', encoding='utf-8') as f:
            json.dump(self.registry, f, ensure_ascii=False, indent=2)
    
    def _initialize_quality_rules(self) -> Dict:
        """初始化质量检测规则"""
        return {
            "missing_threshold": 0.1,  # 缺失值阈值
            "duplicate_threshold": 0.05,  # 重复值阈值
            "outlier_method": "iqr",  # 异常值检测方法
            "quality_weights": {
                "completeness": 0.3,
                "uniqueness": 0.2,
                "consistency": 0.3,
                "validity": 0.2
            }
        }
    
    def register_dataset(
        self,
        name: str,
        description: str,
        data_type: DataType,
        file_path: str,
        owner: str = "system",
        tags: List[str] = None,
        metadata: Dict = None
    ) -> Dict[str, Any]:
        """
        注册数据集
        
        Args:
            name: 数据集名称
            description: 描述
            data_type: 数据类型
            file_path: 数据文件路径
            owner: 所有者
            tags: 标签
            metadata: 元数据
            
        Returns:
            注册结果
        """
        logger.info(f"Registering dataset: {name}")
        
        # 生成唯一ID
        dataset_id = self._generate_id(name)
        
        # 计算文件哈希
        file_hash = self._calculate_file_hash(file_path)
        file_size = os.path.getsize(file_path)
        
        # 分析数据
        data_info = self._analyze_data(file_path, data_type)
        
        # 创建数据集记录
        dataset_record = {
            "dataset_id": dataset_id,
            "name": name,
            "description": description,
            "data_type": data_type.value,
            "owner": owner,
            "status": DatasetStatus.DRAFT.value,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "current_version": "v1.0.0",
            "versions": {},
            "tags": tags or [],
            "metadata": metadata or {},
            "file_info": {
                "original_path": file_path,
                "hash": file_hash,
                "size": file_size
            },
            "statistics": data_info
        }
        
        # 注册到注册表
        self.registry["datasets"][dataset_id] = dataset_record
        self._save_registry()
        
        # 创建初始版本
        version_result = self.create_version(
            dataset_id=dataset_id,
            version_number="v1.0.0",
            description="Initial version",
            created_by=owner,
            file_path=file_path
        )
        
        # 复制数据文件到存储
        self._copy_dataset_file(dataset_id, "v1.0.0", file_path)
        
        logger.info(f"Dataset registered: {dataset_id}")
        
        return {
            "status": "success",
            "dataset_id": dataset_id,
            "dataset_record": dataset_record,
            "initial_version": version_result
        }
    
    def create_version(
        self,
        dataset_id: str,
        version_number: str,
        description: str,
        created_by: str,
        file_path: str = None,
        parent_version: str = None,
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """
        创建数据集版本
        
        Args:
            dataset_id: 数据集ID
            version_number: 版本号
            description: 描述
            created_by: 创建者
            file_path: 数据文件路径（可选，如果不提供则基于父版本）
            parent_version: 父版本
            tags: 标签
            
        Returns:
            版本创建结果
        """
        if dataset_id not in self.registry["datasets"]:
            return {"status": "error", "message": f"Dataset {dataset_id} not found"}
        
        logger.info(f"Creating version {version_number} for dataset {dataset_id}")
        
        # 生成版本ID
        version_id = self._generate_id(f"{dataset_id}_{version_number}")
        
        # 计算文件信息
        if file_path:
            file_hash = self._calculate_file_hash(file_path)
            file_size = os.path.getsize(file_path)
            data_info = self._analyze_data(file_path, DataType(
                self.registry["datasets"][dataset_id]["data_type"]
            ))
            record_count = data_info.get("record_count", 0)
            feature_count = data_info.get("feature_count", 0)
        else:
            # 使用父版本信息
            parent_info = self._get_version_info(dataset_id, parent_version)
            file_hash = parent_info.file_hash if parent_info else ""
            file_size = parent_info.file_size if parent_info else 0
            record_count = parent_info.record_count if parent_info else 0
            feature_count = parent_info.feature_count if parent_info else 0
        
        # 创建版本记录
        version = DatasetVersion(
            version_id=version_id,
            version_number=version_number,
            created_at=datetime.now().isoformat(),
            created_by=created_by,
            description=description,
            file_hash=file_hash,
            file_size=file_size,
            record_count=record_count,
            feature_count=feature_count,
            tags=tags or [],
            parent_version=parent_version
        )
        
        # 更新注册表
        self.registry["datasets"][dataset_id]["versions"][version_number] = asdict(version)
        self.registry["datasets"][dataset_id]["current_version"] = version_number
        self.registry["datasets"][dataset_id]["updated_at"] = datetime.now().isoformat()
        
        # 添加到版本历史
        self.registry["version_history"].append({
            "dataset_id": dataset_id,
            "version_number": version_number,
            "created_at": version.created_at,
            "created_by": created_by
        })
        
        self._save_registry()
        
        logger.info(f"Version created: {version_number}")
        
        return {
            "status": "success",
            "version_id": version_id,
            "version_number": version_number,
            "version_record": asdict(version)
        }
    
    def check_data_quality(
        self,
        dataset_id: str,
        version: str = None,
        custom_rules: Dict = None
    ) -> DataQualityReport:
        """
        检测数据质量
        
        Args:
            dataset_id: 数据集ID
            version: 版本号（默认当前版本）
            custom_rules: 自定义规则
            
        Returns:
            数据质量报告
        """
        if dataset_id not in self.registry["datasets"]:
            raise ValueError(f"Dataset {dataset_id} not found")
        
        logger.info(f"Checking data quality for {dataset_id}")
        
        dataset = self.registry["datasets"][dataset_id]
        version = version or dataset["current_version"]
        
        # 加载数据
        file_path = self._get_version_file_path(dataset_id, version)
        data = self._load_data(file_path)
        
        # 合并规则
        rules = {**self.quality_rules, **(custom_rules or {})}
        
        # 执行质量检测
        issues = []
        
        # 1. 完整性检测
        missing_info = self._check_missing_values(data)
        issues.extend(missing_info["issues"])
        
        # 2. 唯一性检测
        duplicate_info = self._check_duplicates(data)
        issues.extend(duplicate_info["issues"])
        
        # 3. 一致性检测
        consistency_info = self._check_consistency(data)
        issues.extend(consistency_info["issues"])
        
        # 4. 有效性检测
        validity_info = self._check_validity(data)
        issues.extend(validity_info["issues"])
        
        # 计算总体质量分数
        total_records = len(data)
        valid_records = total_records - missing_info["invalid_count"]
        missing_rate = missing_info["missing_rate"]
        duplicate_rate = duplicate_info["duplicate_rate"]
        
        quality_score = self._calculate_quality_score(
            completeness=1 - missing_rate,
            uniqueness=1 - duplicate_rate,
            consistency=consistency_info["consistency_score"],
            validity=validity_info["validity_score"],
            weights=rules["quality_weights"]
        )
        
        # 生成建议
        recommendations = self._generate_recommendations(issues, quality_score)
        
        # 创建报告
        report = DataQualityReport(
            dataset_id=dataset_id,
            version=version,
            checked_at=datetime.now().isoformat(),
            total_records=total_records,
            valid_records=valid_records,
            invalid_records=total_records - valid_records,
            missing_rate=missing_rate,
            duplicate_rate=duplicate_rate,
            quality_score=quality_score,
            issues=issues,
            recommendations=recommendations
        )
        
        # 保存报告
        self._save_quality_report(report)
        
        logger.info(f"Quality check completed. Score: {quality_score:.2f}")
        
        return report
    
    def _check_missing_values(self, data: pd.DataFrame) -> Dict:
        """检测缺失值"""
        issues = []
        missing_counts = data.isnull().sum()
        total_cells = data.size
        missing_cells = missing_counts.sum()
        missing_rate = missing_cells / total_cells if total_cells > 0 else 0
        
        for column, count in missing_counts.items():
            if count > 0:
                col_missing_rate = count / len(data)
                severity = "high" if col_missing_rate > 0.1 else "medium" if col_missing_rate > 0.05 else "low"
                issues.append({
                    "type": "missing_values",
                    "column": column,
                    "count": int(count),
                    "rate": col_missing_rate,
                    "severity": severity
                })
        
        return {
            "missing_rate": missing_rate,
            "invalid_count": int(missing_counts.any().sum()),
            "issues": issues
        }
    
    def _check_duplicates(self, data: pd.DataFrame) -> Dict:
        """检测重复值"""
        issues = []
        duplicate_rows = data.duplicated()
        duplicate_count = duplicate_rows.sum()
        duplicate_rate = duplicate_count / len(data) if len(data) > 0 else 0
        
        if duplicate_count > 0:
            issues.append({
                "type": "duplicate_records",
                "count": int(duplicate_count),
                "rate": duplicate_rate,
                "severity": "medium" if duplicate_rate > 0.05 else "low"
            })
        
        return {
            "duplicate_rate": duplicate_rate,
            "issues": issues
        }
    
    def _check_consistency(self, data: pd.DataFrame) -> Dict:
        """检测一致性"""
        issues = []
        
        # 检查数据类型一致性
        for column in data.columns:
            if data[column].dtype == 'object':
                # 检查混合类型
                types = data[column].apply(type).unique()
                if len(types) > 1:
                    issues.append({
                        "type": "inconsistent_types",
                        "column": column,
                        "types": [str(t) for t in types],
                        "severity": "medium"
                    })
        
        consistency_score = 1.0 - (len(issues) * 0.1)
        consistency_score = max(0.0, consistency_score)
        
        return {
            "consistency_score": consistency_score,
            "issues": issues
        }
    
    def _check_validity(self, data: pd.DataFrame) -> Dict:
        """检测有效性"""
        issues = []
        
        # 检查数值范围
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        for column in numeric_columns:
            # 检查异常值（使用IQR方法）
            Q1 = data[column].quantile(0.25)
            Q3 = data[column].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outliers = data[(data[column] < lower_bound) | (data[column] > upper_bound)]
            if len(outliers) > 0:
                issues.append({
                    "type": "outliers",
                    "column": column,
                    "count": len(outliers),
                    "rate": len(outliers) / len(data),
                    "severity": "low"
                })
        
        validity_score = 1.0 - (len(issues) * 0.05)
        validity_score = max(0.0, validity_score)
        
        return {
            "validity_score": validity_score,
            "issues": issues
        }
    
    def _calculate_quality_score(
        self,
        completeness: float,
        uniqueness: float,
        consistency: float,
        validity: float,
        weights: Dict[str, float]
    ) -> float:
        """计算总体质量分数"""
        score = (
            completeness * weights["completeness"] +
            uniqueness * weights["uniqueness"] +
            consistency * weights["consistency"] +
            validity * weights["validity"]
        )
        return round(score, 4)
    
    def _generate_recommendations(self, issues: List[Dict], quality_score: float) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        if quality_score < 0.6:
            recommendations.append("数据质量较差，建议进行全面的数据清洗")
        
        missing_issues = [i for i in issues if i["type"] == "missing_values"]
        if missing_issues:
            high_missing = [i for i in missing_issues if i["severity"] == "high"]
            if high_missing:
                recommendations.append(f"发现{len(high_missing)}个字段缺失值严重，建议进行缺失值填充或删除")
        
        duplicate_issues = [i for i in issues if i["type"] == "duplicate_records"]
        if duplicate_issues:
            recommendations.append("发现重复记录，建议进行去重处理")
        
        outlier_issues = [i for i in issues if i["type"] == "outliers"]
        if outlier_issues:
            recommendations.append(f"发现{len(outlier_issues)}个字段存在异常值，建议检查数据采集过程")
        
        if not recommendations:
            recommendations.append("数据质量良好，可以直接使用")
        
        return recommendations
    
    def create_preprocessing_pipeline(
        self,
        name: str,
        steps: List[Dict[str, Any]],
        description: str = ""
    ) -> Dict[str, Any]:
        """
        创建数据预处理管道
        
        Args:
            name: 管道名称
            steps: 处理步骤列表
            description: 描述
            
        Returns:
            管道创建结果
        """
        logger.info(f"Creating preprocessing pipeline: {name}")
        
        pipeline_id = self._generate_id(name)
        
        pipeline = {
            "pipeline_id": pipeline_id,
            "name": name,
            "description": description,
            "steps": steps,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "version": "1.0.0"
        }
        
        # 保存管道配置
        pipeline_file = self.storage_path / "pipelines" / f"{pipeline_id}.json"
        with open(pipeline_file, 'w', encoding='utf-8') as f:
            json.dump(pipeline, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Pipeline created: {pipeline_id}")
        
        return {
            "status": "success",
            "pipeline_id": pipeline_id,
            "pipeline": pipeline
        }
    
    def execute_preprocessing_pipeline(
        self,
        pipeline_id: str,
        dataset_id: str,
        version: str = None,
        output_name: str = None
    ) -> Dict[str, Any]:
        """
        执行数据预处理管道
        
        Args:
            pipeline_id: 管道ID
            dataset_id: 数据集ID
            version: 版本号
            output_name: 输出数据集名称
            
        Returns:
            执行结果
        """
        logger.info(f"Executing pipeline {pipeline_id} on dataset {dataset_id}")
        
        # 加载管道配置
        pipeline_file = self.storage_path / "pipelines" / f"{pipeline_id}.json"
        if not pipeline_file.exists():
            return {"status": "error", "message": f"Pipeline {pipeline_id} not found"}
        
        with open(pipeline_file, 'r', encoding='utf-8') as f:
            pipeline = json.load(f)
        
        # 加载数据
        file_path = self._get_version_file_path(dataset_id, version)
        data = self._load_data(file_path)
        
        # 执行处理步骤
        processed_data = data.copy()
        execution_log = []
        
        for i, step in enumerate(pipeline["steps"]):
            step_name = step.get("name", f"step_{i}")
            step_type = step.get("type")
            step_params = step.get("params", {})
            
            try:
                processed_data = self._execute_preprocessing_step(
                    processed_data, step_type, step_params
                )
                execution_log.append({
                    "step": step_name,
                    "type": step_type,
                    "status": "success",
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                execution_log.append({
                    "step": step_name,
                    "type": step_type,
                    "status": "failed",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                return {
                    "status": "error",
                    "message": f"Pipeline execution failed at step {step_name}",
                    "execution_log": execution_log
                }
        
        # 保存处理后的数据
        output_name = output_name or f"{dataset_id}_processed"
        output_path = self.storage_path / "datasets" / f"{output_name}.csv"
        processed_data.to_csv(output_path, index=False)
        
        # 创建新版本
        version_result = self.create_version(
            dataset_id=dataset_id,
            version_number=self._increment_version(version or "v1.0.0"),
            description=f"Processed with pipeline {pipeline_id}",
            created_by="pipeline",
            file_path=str(output_path)
        )
        
        logger.info(f"Pipeline execution completed")
        
        return {
            "status": "success",
            "output_path": str(output_path),
            "records_processed": len(processed_data),
            "execution_log": execution_log,
            "new_version": version_result
        }
    
    def _execute_preprocessing_step(
        self,
        data: pd.DataFrame,
        step_type: str,
        params: Dict
    ) -> pd.DataFrame:
        """执行单个预处理步骤"""
        if step_type == "drop_missing":
            threshold = params.get("threshold", 0.5)
            return data.dropna(thresh=int(threshold * len(data.columns)))
        
        elif step_type == "fill_missing":
            strategy = params.get("strategy", "mean")
            columns = params.get("columns", data.columns)
            
            for col in columns:
                if col in data.columns:
                    if strategy == "mean":
                        data[col].fillna(data[col].mean(), inplace=True)
                    elif strategy == "median":
                        data[col].fillna(data[col].median(), inplace=True)
                    elif strategy == "mode":
                        data[col].fillna(data[col].mode()[0], inplace=True)
                    elif strategy == "constant":
                        data[col].fillna(params.get("value", 0), inplace=True)
            return data
        
        elif step_type == "drop_duplicates":
            return data.drop_duplicates()
        
        elif step_type == "normalize":
            columns = params.get("columns", data.select_dtypes(include=[np.number]).columns)
            method = params.get("method", "minmax")
            
            for col in columns:
                if col in data.columns and data[col].dtype in [np.float64, np.int64]:
                    if method == "minmax":
                        data[col] = (data[col] - data[col].min()) / (data[col].max() - data[col].min())
                    elif method == "zscore":
                        data[col] = (data[col] - data[col].mean()) / data[col].std()
            return data
        
        elif step_type == "encode_categorical":
            columns = params.get("columns")
            method = params.get("method", "onehot")
            
            if columns is None:
                columns = data.select_dtypes(include=['object']).columns
            
            if method == "onehot":
                data = pd.get_dummies(data, columns=columns)
            elif method == "label":
                from sklearn.preprocessing import LabelEncoder
                for col in columns:
                    if col in data.columns:
                        le = LabelEncoder()
                        data[col] = le.fit_transform(data[col].astype(str))
            
            return data
        
        else:
            logger.warning(f"Unknown step type: {step_type}")
            return data
    
    def list_datasets(self, status: DatasetStatus = None) -> List[Dict]:
        """列出数据集"""
        datasets = list(self.registry["datasets"].values())
        
        if status:
            datasets = [d for d in datasets if d["status"] == status.value]
        
        return datasets
    
    def get_dataset_info(self, dataset_id: str) -> Optional[Dict]:
        """获取数据集信息"""
        return self.registry["datasets"].get(dataset_id)
    
    def _generate_id(self, name: str) -> str:
        """生成唯一ID"""
        import uuid
        return f"{name}_{uuid.uuid4().hex[:8]}"
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件哈希"""
        if not os.path.exists(file_path):
            return ""
        
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _analyze_data(self, file_path: str, data_type: DataType) -> Dict:
        """分析数据"""
        if not os.path.exists(file_path):
            return {}
        
        try:
            if data_type == DataType.TABULAR:
                if file_path.endswith('.csv'):
                    df = pd.read_csv(file_path)
                elif file_path.endswith('.json'):
                    df = pd.read_json(file_path)
                else:
                    return {}
                
                return {
                    "record_count": len(df),
                    "feature_count": len(df.columns),
                    "columns": list(df.columns),
                    "dtypes": df.dtypes.astype(str).to_dict(),
                    "memory_usage": df.memory_usage(deep=True).sum()
                }
        except Exception as e:
            logger.error(f"Error analyzing data: {str(e)}")
            return {}
        
        return {}
    
    def _copy_dataset_file(self, dataset_id: str, version: str, source_path: str):
        """复制数据文件到存储"""
        import shutil
        
        dest_dir = self.storage_path / "datasets" / dataset_id / "versions" / version
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        dest_path = dest_dir / os.path.basename(source_path)
        shutil.copy2(source_path, dest_path)
    
    def _get_version_file_path(self, dataset_id: str, version: str = None) -> str:
        """获取版本文件路径"""
        dataset = self.registry["datasets"].get(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")
        
        version = version or dataset["current_version"]
        
        # 查找版本目录
        version_dir = self.storage_path / "datasets" / dataset_id / "versions" / version
        if version_dir.exists():
            files = list(version_dir.glob("*"))
            if files:
                return str(files[0])
        
        # 如果没有版本目录，使用原始路径
        return dataset["file_info"]["original_path"]
    
    def _load_data(self, file_path: str) -> pd.DataFrame:
        """加载数据"""
        if file_path.endswith('.csv'):
            return pd.read_csv(file_path)
        elif file_path.endswith('.json'):
            return pd.read_json(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path}")
    
    def _get_version_info(self, dataset_id: str, version: str) -> Optional[DatasetVersion]:
        """获取版本信息"""
        dataset = self.registry["datasets"].get(dataset_id)
        if not dataset or version not in dataset["versions"]:
            return None
        
        version_dict = dataset["versions"][version]
        return DatasetVersion(**version_dict)
    
    def _increment_version(self, version: str) -> str:
        """递增版本号"""
        parts = version.replace('v', '').split('.')
        if len(parts) == 3:
            parts[2] = str(int(parts[2]) + 1)
            return f"v{'.'.join(parts)}"
        return f"{version}.1"
    
    def _save_quality_report(self, report: DataQualityReport):
        """保存质量报告"""
        report_file = self.storage_path / "reports" / f"quality_{report.dataset_id}_{report.version}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(report), f, ensure_ascii=False, indent=2)


# 示例使用
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # 创建数据管理器
    dm = DataManager()
    
    # 示例数据
    sample_data = pd.DataFrame({
        'id': range(1, 101),
        'name': [f'user_{i}' for i in range(1, 101)],
        'age': np.random.randint(18, 70, 100),
        'income': np.random.normal(50000, 15000, 100),
        'category': np.random.choice(['A', 'B', 'C', 'D'], 100)
    })
    
    # 添加一些缺失值和重复值
    sample_data.loc[0:5, 'age'] = None
    sample_data.loc[10:15, 'income'] = None
    sample_data = pd.concat([sample_data, sample_data.iloc[0:5]], ignore_index=True)
    
    # 保存示例数据
    sample_file = "./sample_data.csv"
    sample_data.to_csv(sample_file, index=False)
    
    # 注册数据集
    result = dm.register_dataset(
        name="user_demographics",
        description="用户人口统计数据集",
        data_type=DataType.TABULAR,
        file_path=sample_file,
        owner="data_team",
        tags=["user", "demographics", "sample"]
    )
    
    print(f"Dataset registered: {result['dataset_id']}")
    
    # 检测数据质量
    quality_report = dm.check_data_quality(result['dataset_id'])
    print(f"Quality score: {quality_report.quality_score}")
    print(f"Issues found: {len(quality_report.issues)}")
    
    # 创建预处理管道
    pipeline = dm.create_preprocessing_pipeline(
        name="basic_cleaning",
        description="基本数据清洗管道",
        steps=[
            {"name": "drop_missing", "type": "drop_missing", "params": {"threshold": 0.5}},
            {"name": "fill_missing", "type": "fill_missing", "params": {"strategy": "mean"}},
            {"name": "drop_duplicates", "type": "drop_duplicates", "params": {}},
            {"name": "normalize_income", "type": "normalize", "params": {"columns": ["income", "age"], "method": "minmax"}}
        ]
    )
    
    print(f"Pipeline created: {pipeline['pipeline_id']}")