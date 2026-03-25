"""
实验追踪模块
支持实验管理、指标记录、参数追踪
"""

import os
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ExperimentStatus(str, Enum):
    """实验状态"""
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Experiment:
    """实验"""
    
    def __init__(
        self,
        experiment_id: str,
        name: str,
        description: str = "",
        tags: List[str] = None
    ):
        self.experiment_id = experiment_id
        self.name = name
        self.description = description
        self.tags = tags or []
        self.status = ExperimentStatus.CREATED
        self.parameters: Dict[str, Any] = {}
        self.metrics: Dict[str, List[Dict[str, Any]]] = {}
        self.artifacts: List[Dict[str, Any]] = []
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.ended_at: Optional[datetime] = None
        self.duration_seconds: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "status": self.status.value,
            "parameters": self.parameters,
            "metrics": self.metrics,
            "artifacts": self.artifacts,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration_seconds": self.duration_seconds
        }


class Run:
    """实验运行"""
    
    def __init__(
        self,
        run_id: str,
        experiment_id: str,
        name: str = ""
    ):
        self.run_id = run_id
        self.experiment_id = experiment_id
        self.name = name or f"run_{run_id[:8]}"
        self.status = ExperimentStatus.CREATED
        self.parameters: Dict[str, Any] = {}
        self.metrics: Dict[str, float] = {}
        self.metric_history: Dict[str, List[Dict[str, Any]]] = {}
        self.tags: Dict[str, str] = {}
        self.artifacts: List[Dict[str, Any]] = []
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.ended_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "experiment_id": self.experiment_id,
            "name": self.name,
            "status": self.status.value,
            "parameters": self.parameters,
            "metrics": self.metrics,
            "metric_history": self.metric_history,
            "tags": self.tags,
            "artifacts": self.artifacts,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None
        }


class ExperimentTracker:
    """实验追踪器"""
    
    def __init__(self, tracking_dir: str = "./mlruns"):
        self.tracking_dir = Path(tracking_dir)
        self.tracking_dir.mkdir(parents=True, exist_ok=True)
        self.experiments: Dict[str, Experiment] = {}
        self.runs: Dict[str, Run] = {}
        self._load_experiments()
    
    def _load_experiments(self):
        """加载已存在的实验"""
        experiments_file = self.tracking_dir / "experiments.json"
        if experiments_file.exists():
            try:
                with open(experiments_file, 'r') as f:
                    data = json.load(f)
                    for exp_data in data.get("experiments", []):
                        exp = Experiment(
                            experiment_id=exp_data["experiment_id"],
                            name=exp_data["name"],
                            description=exp_data.get("description", ""),
                            tags=exp_data.get("tags", [])
                        )
                        exp.status = ExperimentStatus(exp_data["status"])
                        exp.parameters = exp_data.get("parameters", {})
                        exp.metrics = exp_data.get("metrics", {})
                        exp.artifacts = exp_data.get("artifacts", [])
                        self.experiments[exp.experiment_id] = exp
            except Exception as e:
                logger.error(f"加载实验失败: {e}")
    
    def _save_experiments(self):
        """保存实验数据"""
        experiments_file = self.tracking_dir / "experiments.json"
        data = {
            "experiments": [exp.to_dict() for exp in self.experiments.values()],
            "updated_at": datetime.utcnow().isoformat()
        }
        with open(experiments_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def create_experiment(
        self,
        name: str,
        description: str = "",
        tags: List[str] = None
    ) -> Experiment:
        """创建实验"""
        experiment_id = str(uuid.uuid4())
        experiment = Experiment(
            experiment_id=experiment_id,
            name=name,
            description=description,
            tags=tags
        )
        self.experiments[experiment_id] = experiment
        self._save_experiments()
        logger.info(f"创建实验: {name} ({experiment_id})")
        return experiment
    
    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """获取实验"""
        return self.experiments.get(experiment_id)
    
    def list_experiments(
        self,
        status: ExperimentStatus = None,
        tags: List[str] = None
    ) -> List[Experiment]:
        """列出实验"""
        experiments = list(self.experiments.values())
        
        if status:
            experiments = [e for e in experiments if e.status == status]
        
        if tags:
            experiments = [e for e in experiments if any(t in e.tags for t in tags)]
        
        return sorted(experiments, key=lambda e: e.created_at, reverse=True)
    
    def delete_experiment(self, experiment_id: str) -> bool:
        """删除实验"""
        if experiment_id in self.experiments:
            del self.experiments[experiment_id]
            runs_to_delete = [r for r in self.runs.values() if r.experiment_id == experiment_id]
            for run in runs_to_delete:
                del self.runs[run.run_id]
            self._save_experiments()
            return True
        return False
    
    def start_run(
        self,
        experiment_id: str,
        name: str = "",
        parameters: Dict[str, Any] = None
    ) -> Run:
        """开始运行"""
        experiment = self.get_experiment(experiment_id)
        if not experiment:
            raise ValueError(f"实验不存在: {experiment_id}")
        
        run_id = str(uuid.uuid4())
        run = Run(
            run_id=run_id,
            experiment_id=experiment_id,
            name=name
        )
        
        if parameters:
            run.parameters = parameters
        
        run.status = ExperimentStatus.RUNNING
        run.started_at = datetime.utcnow()
        
        experiment.status = ExperimentStatus.RUNNING
        experiment.started_at = run.started_at
        
        self.runs[run_id] = run
        self._save_experiments()
        
        logger.info(f"开始运行: {run.name} ({run_id})")
        return run
    
    def get_run(self, run_id: str) -> Optional[Run]:
        """获取运行"""
        return self.runs.get(run_id)
    
    def list_runs(
        self,
        experiment_id: str = None,
        status: ExperimentStatus = None
    ) -> List[Run]:
        """列出运行"""
        runs = list(self.runs.values())
        
        if experiment_id:
            runs = [r for r in runs if r.experiment_id == experiment_id]
        
        if status:
            runs = [r for r in runs if r.status == status]
        
        return sorted(runs, key=lambda r: r.created_at, reverse=True)
    
    def log_parameter(self, run_id: str, key: str, value: Any):
        """记录参数"""
        run = self.get_run(run_id)
        if run:
            run.parameters[key] = value
            run.updated_at = datetime.utcnow()
    
    def log_parameters(self, run_id: str, parameters: Dict[str, Any]):
        """记录多个参数"""
        run = self.get_run(run_id)
        if run:
            run.parameters.update(parameters)
            run.updated_at = datetime.utcnow()
    
    def log_metric(
        self,
        run_id: str,
        key: str,
        value: float,
        step: int = None,
        timestamp: datetime = None
    ):
        """记录指标"""
        run = self.get_run(run_id)
        if run:
            run.metrics[key] = value
            
            if key not in run.metric_history:
                run.metric_history[key] = []
            
            run.metric_history[key].append({
                "value": value,
                "step": step,
                "timestamp": (timestamp or datetime.utcnow()).isoformat()
            })
            
            experiment = self.get_experiment(run.experiment_id)
            if experiment:
                if key not in experiment.metrics:
                    experiment.metrics[key] = []
                experiment.metrics[key].append({
                    "run_id": run_id,
                    "value": value,
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            run.updated_at = datetime.utcnow()
            self._save_experiments()
    
    def log_metrics(self, run_id: str, metrics: Dict[str, float], step: int = None):
        """记录多个指标"""
        for key, value in metrics.items():
            self.log_metric(run_id, key, value, step)
    
    def log_artifact(
        self,
        run_id: str,
        file_path: str,
        artifact_name: str = None
    ):
        """记录工件"""
        run = self.get_run(run_id)
        if run:
            artifact = {
                "name": artifact_name or os.path.basename(file_path),
                "path": file_path,
                "size": os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                "timestamp": datetime.utcnow().isoformat()
            }
            run.artifacts.append(artifact)
            run.updated_at = datetime.utcnow()
            self._save_experiments()
    
    def log_model(
        self,
        run_id: str,
        model_path: str,
        model_name: str,
        framework: str = "sklearn"
    ):
        """记录模型"""
        run = self.get_run(run_id)
        if run:
            artifact = {
                "name": model_name,
                "path": model_path,
                "type": "model",
                "framework": framework,
                "size": os.path.getsize(model_path) if os.path.exists(model_path) else 0,
                "timestamp": datetime.utcnow().isoformat()
            }
            run.artifacts.append(artifact)
            run.updated_at = datetime.utcnow()
            self._save_experiments()
    
    def end_run(
        self,
        run_id: str,
        status: ExperimentStatus = ExperimentStatus.COMPLETED,
        error_message: str = None
    ):
        """结束运行"""
        run = self.get_run(run_id)
        if run:
            run.status = status
            run.ended_at = datetime.utcnow()
            
            if run.started_at:
                run.duration_seconds = (run.ended_at - run.started_at).total_seconds()
            
            experiment = self.get_experiment(run.experiment_id)
            if experiment:
                running_runs = [r for r in self.runs.values() 
                               if r.experiment_id == run.experiment_id 
                               and r.status == ExperimentStatus.RUNNING 
                               and r.run_id != run_id]
                
                if not running_runs:
                    experiment.status = status
                    experiment.ended_at = run.ended_at
                    if experiment.started_at:
                        experiment.duration_seconds = (experiment.ended_at - experiment.started_at).total_seconds()
            
            self._save_experiments()
            logger.info(f"结束运行: {run.name} ({run_id}), 状态: {status.value}")
    
    def get_best_run(
        self,
        experiment_id: str,
        metric_key: str,
        mode: str = "max"
    ) -> Optional[Run]:
        """获取最佳运行"""
        runs = self.list_runs(experiment_id=experiment_id)
        runs = [r for r in runs if metric_key in r.metrics]
        
        if not runs:
            return None
        
        if mode == "max":
            return max(runs, key=lambda r: r.metrics[metric_key])
        else:
            return min(runs, key=lambda r: r.metrics[metric_key])
    
    def compare_runs(
        self,
        run_ids: List[str],
        metrics: List[str] = None
    ) -> Dict[str, Any]:
        """比较运行"""
        runs = [self.get_run(rid) for rid in run_ids]
        runs = [r for r in runs if r is not None]
        
        if not runs:
            return {"error": "没有找到有效的运行"}
        
        comparison = {
            "runs": [r.to_dict() for r in runs],
            "metrics_comparison": {},
            "parameters_comparison": {}
        }
        
        all_metrics = set()
        for run in runs:
            all_metrics.update(run.metrics.keys())
        
        if metrics:
            all_metrics = all_metrics.intersection(metrics)
        
        for metric in all_metrics:
            comparison["metrics_comparison"][metric] = {
                run.run_id: run.metrics.get(metric)
                for run in runs
            }
        
        all_params = set()
        for run in runs:
            all_params.update(run.parameters.keys())
        
        for param in all_params:
            comparison["parameters_comparison"][param] = {
                run.run_id: run.parameters.get(param)
                for run in runs
            }
        
        return comparison
    
    def search_runs(
        self,
        experiment_ids: List[str] = None,
        filter_string: str = None,
        max_results: int = 100
    ) -> List[Run]:
        """搜索运行"""
        runs = list(self.runs.values())
        
        if experiment_ids:
            runs = [r for r in runs if r.experiment_id in experiment_ids]
        
        if filter_string:
            pass
        
        return sorted(runs, key=lambda r: r.created_at, reverse=True)[:max_results]
