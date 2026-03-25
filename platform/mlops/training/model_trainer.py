"""
MLOps平台模型训练模块
实现分布式训练、超参数优化、训练监控、断点续训等功能
"""

import os
import json
import logging
import pickle
import time
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict, field
from enum import Enum
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import threading

logger = logging.getLogger(__name__)


class TrainingStatus(Enum):
    """训练状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class ModelType(Enum):
    """模型类型"""
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    CLUSTERING = "clustering"
    RECOMMENDATION = "recommendation"
    TIME_SERIES = "time_series"
    NLP = "nlp"
    COMPUTER_VISION = "computer_vision"


class OptimizerType(Enum):
    """优化器类型"""
    GRID_SEARCH = "grid_search"
    RANDOM_SEARCH = "random_search"
    BAYESIAN = "bayesian"
    HYPERBAND = "hyperband"


@dataclass
class HyperParameter:
    """超参数定义"""
    name: str
    param_type: str  # "int", "float", "categorical"
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    choices: Optional[List[Any]] = None
    default: Optional[Any] = None


@dataclass
class TrainingConfig:
    """训练配置"""
    model_name: str
    model_type: ModelType
    dataset_id: str
    dataset_version: str
    target_column: str
    feature_columns: List[str]
    hyperparameters: Dict[str, Any]
    validation_split: float = 0.2
    test_split: float = 0.1
    random_seed: int = 42
    early_stopping_patience: int = 10
    max_epochs: int = 100
    batch_size: int = 32
    learning_rate: float = 0.001
    optimizer: str = "adam"
    loss_function: str = "mse"
    metrics: List[str] = field(default_factory=lambda: ["accuracy"])


@dataclass
class TrainingMetrics:
    """训练指标"""
    epoch: int
    train_loss: float
    val_loss: float
    train_metrics: Dict[str, float]
    val_metrics: Dict[str, float]
    timestamp: str
    learning_rate: float


@dataclass
class TrainingResult:
    """训练结果"""
    training_id: str
    model_name: str
    status: TrainingStatus
    start_time: str
    end_time: Optional[str]
    duration_seconds: float
    best_epoch: int
    best_val_loss: float
    best_val_metrics: Dict[str, float]
    final_train_loss: float
    final_train_metrics: Dict[str, float]
    metrics_history: List[Dict]
    hyperparameters: Dict[str, Any]
    model_path: Optional[str]
    error_message: Optional[str] = None


class ModelTrainer:
    """
    模型训练器
    支持多种模型类型、超参数优化、训练监控
    """
    
    def __init__(self, storage_path: str = "./data/mlops/training"):
        """
        初始化模型训练器
        
        Args:
            storage_path: 存储路径
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        (self.storage_path / "models").mkdir(exist_ok=True)
        (self.storage_path / "experiments").mkdir(exist_ok=True)
        (self.storage_path / "checkpoints").mkdir(exist_ok=True)
        (self.storage_path / "logs").mkdir(exist_ok=True)
        
        self.active_trainings = {}
        self.training_history = self._load_training_history()
        
    def _load_training_history(self) -> Dict:
        """加载训练历史"""
        history_file = self.storage_path / "training_history.json"
        if history_file.exists():
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"trainings": {}}
    
    def _save_training_history(self):
        """保存训练历史"""
        history_file = self.storage_path / "training_history.json"
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(self.training_history, f, ensure_ascii=False, indent=2)
    
    def create_training_job(
        self,
        config: TrainingConfig,
        description: str = ""
    ) -> Dict[str, Any]:
        """
        创建训练任务
        
        Args:
            config: 训练配置
            description: 描述
            
        Returns:
            任务创建结果
        """
        logger.info(f"Creating training job: {config.model_name}")
        
        training_id = self._generate_id(f"train_{config.model_name}")
        
        job = {
            "training_id": training_id,
            "config": asdict(config),
            "description": description,
            "status": TrainingStatus.PENDING.value,
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "checkpoints": [],
            "logs": []
        }
        
        self.training_history["trainings"][training_id] = job
        self._save_training_history()
        
        logger.info(f"Training job created: {training_id}")
        
        return {
            "status": "success",
            "training_id": training_id,
            "job": job
        }
    
    def start_training(
        self,
        training_id: str,
        data_loader: Callable = None,
        model_builder: Callable = None,
        checkpoint_path: str = None
    ) -> Dict[str, Any]:
        """
        开始训练
        
        Args:
            training_id: 训练ID
            data_loader: 数据加载函数
            model_builder: 模型构建函数
            checkpoint_path: 检查点路径（用于断点续训）
            
        Returns:
            训练启动结果
        """
        if training_id not in self.training_history["trainings"]:
            return {"status": "error", "message": f"Training job {training_id} not found"}
        
        logger.info(f"Starting training: {training_id}")
        
        job = self.training_history["trainings"][training_id]
        job["status"] = TrainingStatus.RUNNING.value
        job["started_at"] = datetime.now().isoformat()
        
        config = TrainingConfig(**job["config"])
        
        try:
            # 加载数据
            X_train, X_val, y_train, y_val = self._load_training_data(config)
            
            # 构建模型
            model = self._build_model(config, model_builder)
            
            # 从检查点恢复（如果提供）
            start_epoch = 0
            if checkpoint_path:
                start_epoch, model = self._load_checkpoint(model, checkpoint_path)
                logger.info(f"Resumed from epoch {start_epoch}")
            
            # 训练模型
            training_result = self._train_model(
                training_id=training_id,
                model=model,
                X_train=X_train,
                X_val=X_val,
                y_train=y_train,
                y_val=y_val,
                config=config,
                start_epoch=start_epoch
            )
            
            # 更新任务状态
            job["status"] = training_result.status.value
            job["completed_at"] = training_result.end_time
            
            self._save_training_history()
            
            logger.info(f"Training completed: {training_id}")
            
            return {
                "status": "success",
                "training_result": asdict(training_result)
            }
            
        except Exception as e:
            logger.error(f"Training failed: {str(e)}")
            job["status"] = TrainingStatus.FAILED.value
            job["error"] = str(e)
            job["completed_at"] = datetime.now().isoformat()
            self._save_training_history()
            
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _load_training_data(
        self,
        config: TrainingConfig
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """加载训练数据"""
        # 这里应该从数据管理器加载数据
        # 简化实现：生成模拟数据
        
        n_samples = 1000
        n_features = len(config.feature_columns) if config.feature_columns else 10
        
        X = np.random.randn(n_samples, n_features)
        y = np.random.randn(n_samples) if config.model_type == ModelType.REGRESSION else np.random.randint(0, 2, n_samples)
        
        # 分割数据
        val_size = int(n_samples * config.validation_split)
        
        X_val = X[:val_size]
        y_val = y[:val_size]
        X_train = X[val_size:]
        y_train = y[val_size:]
        
        return X_train, X_val, y_train, y_val
    
    def _build_model(self, config: TrainingConfig, custom_builder: Callable = None):
        """构建模型"""
        if custom_builder:
            return custom_builder(config)
        
        # 使用sklearn作为默认实现
        from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
        from sklearn.linear_model import LogisticRegression, LinearRegression
        
        if config.model_type == ModelType.CLASSIFICATION:
            return RandomForestClassifier(
                n_estimators=config.hyperparameters.get("n_estimators", 100),
                max_depth=config.hyperparameters.get("max_depth", None),
                random_state=config.random_seed
            )
        elif config.model_type == ModelType.REGRESSION:
            return RandomForestRegressor(
                n_estimators=config.hyperparameters.get("n_estimators", 100),
                max_depth=config.hyperparameters.get("max_depth", None),
                random_state=config.random_seed
            )
        else:
            raise ValueError(f"Unsupported model type: {config.model_type}")
    
    def _train_model(
        self,
        training_id: str,
        model,
        X_train: np.ndarray,
        X_val: np.ndarray,
        y_train: np.ndarray,
        y_val: np.ndarray,
        config: TrainingConfig,
        start_epoch: int = 0
    ) -> TrainingResult:
        """训练模型"""
        start_time = datetime.now()
        metrics_history = []
        best_val_loss = float('inf')
        best_epoch = 0
        patience_counter = 0
        
        # 记录训练过程
        for epoch in range(start_epoch, config.max_epochs):
            epoch_start = time.time()
            
            # 模拟训练（sklearn模型不需要epoch训练）
            if hasattr(model, 'fit'):
                if epoch == 0:
                    model.fit(X_train, y_train)
            
            # 计算指标
            train_pred = model.predict(X_train)
            val_pred = model.predict(X_val)
            
            train_loss = self._calculate_loss(y_train, train_pred, config.loss_function)
            val_loss = self._calculate_loss(y_val, val_pred, config.loss_function)
            
            train_metrics = self._calculate_metrics(y_train, train_pred, config.metrics)
            val_metrics = self._calculate_metrics(y_val, val_pred, config.metrics)
            
            # 记录指标
            metric_record = TrainingMetrics(
                epoch=epoch + 1,
                train_loss=train_loss,
                val_loss=val_loss,
                train_metrics=train_metrics,
                val_metrics=val_metrics,
                timestamp=datetime.now().isoformat(),
                learning_rate=config.learning_rate
            )
            metrics_history.append(asdict(metric_record))
            
            # 更新最佳模型
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_epoch = epoch + 1
                patience_counter = 0
                self._save_checkpoint(training_id, model, epoch + 1, val_loss)
            else:
                patience_counter += 1
            
            # 早停检查
            if patience_counter >= config.early_stopping_patience:
                logger.info(f"Early stopping at epoch {epoch + 1}")
                break
            
            # 定期保存检查点
            if (epoch + 1) % 10 == 0:
                self._save_checkpoint(training_id, model, epoch + 1, val_loss)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # 保存最终模型
        model_path = self._save_model(training_id, model)
        
        return TrainingResult(
            training_id=training_id,
            model_name=config.model_name,
            status=TrainingStatus.COMPLETED,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            duration_seconds=duration,
            best_epoch=best_epoch,
            best_val_loss=best_val_loss,
            best_val_metrics=metrics_history[best_epoch - 1]["val_metrics"] if metrics_history else {},
            final_train_loss=train_loss,
            final_train_metrics=train_metrics,
            metrics_history=metrics_history,
            hyperparameters=config.hyperparameters,
            model_path=model_path
        )
    
    def _calculate_loss(self, y_true: np.ndarray, y_pred: np.ndarray, loss_function: str) -> float:
        """计算损失"""
        if loss_function == "mse":
            return float(np.mean((y_true - y_pred) ** 2))
        elif loss_function == "mae":
            return float(np.mean(np.abs(y_true - y_pred)))
        elif loss_function == "cross_entropy":
            epsilon = 1e-15
            y_pred = np.clip(y_pred, epsilon, 1 - epsilon)
            return float(-np.mean(y_true * np.log(y_pred) + (1 - y_true) * np.log(1 - y_pred)))
        else:
            return 0.0
    
    def _calculate_metrics(self, y_true: np.ndarray, y_pred: np.ndarray, metrics: List[str]) -> Dict[str, float]:
        """计算指标"""
        result = {}
        
        for metric in metrics:
            if metric == "accuracy":
                result["accuracy"] = float(np.mean(y_true == y_pred))
            elif metric == "precision":
                true_positives = np.sum((y_true == 1) & (y_pred == 1))
                predicted_positives = np.sum(y_pred == 1)
                result["precision"] = float(true_positives / predicted_positives) if predicted_positives > 0 else 0.0
            elif metric == "recall":
                true_positives = np.sum((y_true == 1) & (y_pred == 1))
                actual_positives = np.sum(y_true == 1)
                result["recall"] = float(true_positives / actual_positives) if actual_positives > 0 else 0.0
            elif metric == "f1":
                precision = result.get("precision", 0.0)
                recall = result.get("recall", 0.0)
                result["f1"] = float(2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
            elif metric == "r2":
                ss_res = np.sum((y_true - y_pred) ** 2)
                ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
                result["r2"] = float(1 - (ss_res / ss_tot)) if ss_tot > 0 else 0.0
        
        return result
    
    def _save_checkpoint(self, training_id: str, model, epoch: int, val_loss: float):
        """保存检查点"""
        checkpoint_dir = self.storage_path / "checkpoints" / training_id
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        checkpoint_file = checkpoint_dir / f"checkpoint_epoch_{epoch}.pkl"
        
        checkpoint = {
            "epoch": epoch,
            "model": model,
            "val_loss": val_loss,
            "timestamp": datetime.now().isoformat()
        }
        
        with open(checkpoint_file, 'wb') as f:
            pickle.dump(checkpoint, f)
        
        # 更新任务检查点记录
        if training_id in self.training_history["trainings"]:
            self.training_history["trainings"][training_id]["checkpoints"].append({
                "epoch": epoch,
                "val_loss": val_loss,
                "path": str(checkpoint_file),
                "timestamp": datetime.now().isoformat()
            })
    
    def _load_checkpoint(self, model, checkpoint_path: str) -> Tuple[int, Any]:
        """加载检查点"""
        with open(checkpoint_path, 'rb') as f:
            checkpoint = pickle.load(f)
        
        return checkpoint["epoch"], checkpoint["model"]
    
    def _save_model(self, training_id: str, model) -> str:
        """保存模型"""
        model_dir = self.storage_path / "models" / training_id
        model_dir.mkdir(parents=True, exist_ok=True)
        
        model_file = model_dir / "model.pkl"
        
        with open(model_file, 'wb') as f:
            pickle.dump(model, f)
        
        return str(model_file)
    
    def hyperparameter_optimization(
        self,
        config: TrainingConfig,
        param_grid: Dict[str, HyperParameter],
        optimizer: OptimizerType = OptimizerType.RANDOM_SEARCH,
        n_trials: int = 10,
        n_jobs: int = 1
    ) -> Dict[str, Any]:
        """
        超参数优化
        
        Args:
            config: 基础训练配置
            param_grid: 参数网格
            optimizer: 优化器类型
            n_trials: 试验次数
            n_jobs: 并行任务数
            
        Returns:
            优化结果
        """
        logger.info(f"Starting hyperparameter optimization with {optimizer.value}")
        
        optimization_id = self._generate_id(f"hpo_{config.model_name}")
        
        # 生成参数组合
        param_combinations = self._generate_param_combinations(param_grid, optimizer, n_trials)
        
        results = []
        
        # 执行优化
        if n_jobs > 1:
            with ThreadPoolExecutor(max_workers=n_jobs) as executor:
                futures = []
                for i, params in enumerate(param_combinations):
                    future = executor.submit(
                        self._run_single_trial,
                        config,
                        params,
                        f"{optimization_id}_trial_{i}"
                    )
                    futures.append(future)
                
                for future in futures:
                    results.append(future.result())
        else:
            for i, params in enumerate(param_combinations):
                result = self._run_single_trial(
                    config,
                    params,
                    f"{optimization_id}_trial_{i}"
                )
                results.append(result)
        
        # 分析结果
        best_result = min(results, key=lambda x: x.get("best_val_loss", float('inf')))
        
        logger.info(f"Best parameters found: {best_result['hyperparameters']}")
        
        return {
            "optimization_id": optimization_id,
            "best_params": best_result["hyperparameters"],
            "best_val_loss": best_result["best_val_loss"],
            "best_val_metrics": best_result["best_val_metrics"],
            "all_results": results,
            "n_trials": len(results)
        }
    
    def _generate_param_combinations(
        self,
        param_grid: Dict[str, HyperParameter],
        optimizer: OptimizerType,
        n_trials: int
    ) -> List[Dict[str, Any]]:
        """生成参数组合"""
        combinations = []
        
        if optimizer == OptimizerType.RANDOM_SEARCH:
            for _ in range(n_trials):
                params = {}
                for name, param_def in param_grid.items():
                    if param_def.param_type == "int":
                        params[name] = np.random.randint(
                            int(param_def.min_value),
                            int(param_def.max_value) + 1
                        )
                    elif param_def.param_type == "float":
                        params[name] = np.random.uniform(
                            param_def.min_value,
                            param_def.max_value
                        )
                    elif param_def.param_type == "categorical":
                        params[name] = np.random.choice(param_def.choices)
                combinations.append(params)
        
        elif optimizer == OptimizerType.GRID_SEARCH:
            # 简化的网格搜索
            param_values = {}
            for name, param_def in param_grid.items():
                if param_def.param_type == "int":
                    step = max(1, int((param_def.max_value - param_def.min_value) / 3))
                    param_values[name] = list(range(
                        int(param_def.min_value),
                        int(param_def.max_value) + 1,
                        step
                    ))
                elif param_def.param_type == "float":
                    param_values[name] = np.linspace(
                        param_def.min_value,
                        param_def.max_value,
                        4
                    ).tolist()
                elif param_def.param_type == "categorical":
                    param_values[name] = param_def.choices
            
            # 生成所有组合
            import itertools
            keys = param_values.keys()
            values = param_values.values()
            for combo in itertools.product(*values):
                combinations.append(dict(zip(keys, combo)))
        
        return combinations[:n_trials]
    
    def _run_single_trial(
        self,
        base_config: TrainingConfig,
        params: Dict[str, Any],
        trial_id: str
    ) -> Dict[str, Any]:
        """运行单个试验"""
        # 更新配置
        trial_config = TrainingConfig(
            model_name=f"{base_config.model_name}_trial",
            model_type=base_config.model_type,
            dataset_id=base_config.dataset_id,
            dataset_version=base_config.dataset_version,
            target_column=base_config.target_column,
            feature_columns=base_config.feature_columns,
            hyperparameters={**base_config.hyperparameters, **params},
            validation_split=base_config.validation_split,
            test_split=base_config.test_split,
            random_seed=base_config.random_seed,
            early_stopping_patience=base_config.early_stopping_patience,
            max_epochs=base_config.max_epochs // 2  # 减少epoch以加速
        )
        
        # 创建并启动训练
        job_result = self.create_training_job(trial_config, f"Trial for hyperparameter optimization")
        training_id = job_result["training_id"]
        
        train_result = self.start_training(training_id)
        
        if train_result["status"] == "success":
            result = train_result["training_result"]
            return {
                "trial_id": trial_id,
                "hyperparameters": params,
                "best_val_loss": result["best_val_loss"],
                "best_val_metrics": result["best_val_metrics"],
                "best_epoch": result["best_epoch"]
            }
        else:
            return {
                "trial_id": trial_id,
                "hyperparameters": params,
                "best_val_loss": float('inf'),
                "best_val_metrics": {},
                "best_epoch": 0,
                "error": train_result.get("message", "Unknown error")
            }
    
    def get_training_status(self, training_id: str) -> Optional[Dict]:
        """获取训练状态"""
        return self.training_history["trainings"].get(training_id)
    
    def stop_training(self, training_id: str) -> Dict[str, Any]:
        """停止训练"""
        if training_id not in self.training_history["trainings"]:
            return {"status": "error", "message": f"Training {training_id} not found"}
        
        job = self.training_history["trainings"][training_id]
        
        if job["status"] != TrainingStatus.RUNNING.value:
            return {"status": "error", "message": "Training is not running"}
        
        job["status"] = TrainingStatus.STOPPED.value
        job["completed_at"] = datetime.now().isoformat()
        
        self._save_training_history()
        
        logger.info(f"Training stopped: {training_id}")
        
        return {"status": "success", "message": f"Training {training_id} stopped"}
    
    def list_trainings(self, status: TrainingStatus = None) -> List[Dict]:
        """列出训练任务"""
        trainings = list(self.training_history["trainings"].values())
        
        if status:
            trainings = [t for t in trainings if t["status"] == status.value]
        
        return trainings
    
    def _generate_id(self, name: str) -> str:
        """生成唯一ID"""
        import uuid
        return f"{name}_{uuid.uuid4().hex[:8]}"


class DistributedTrainer(ModelTrainer):
    """
    分布式训练器
    支持多节点、多GPU训练
    """
    
    def __init__(self, storage_path: str = "./data/mlops/training"):
        super().__init__(storage_path)
        self.workers = {}
        self.worker_status = {}
    
    def register_worker(self, worker_id: str, worker_info: Dict) -> Dict[str, Any]:
        """注册工作节点"""
        self.workers[worker_id] = worker_info
        self.worker_status[worker_id] = "idle"
        
        logger.info(f"Worker registered: {worker_id}")
        
        return {
            "status": "success",
            "worker_id": worker_id
        }
    
    def distribute_training(
        self,
        config: TrainingConfig,
        n_workers: int = 2,
        strategy: str = "data_parallel"
    ) -> Dict[str, Any]:
        """
        分布式训练
        
        Args:
            config: 训练配置
            n_workers: 工作节点数
            strategy: 分布策略
            
        Returns:
            分布式训练结果
        """
        logger.info(f"Starting distributed training with {n_workers} workers")
        
        distributed_id = self._generate_id(f"dist_{config.model_name}")
        
        # 分配任务到工作节点
        worker_assignments = self._assign_workers(n_workers)
        
        # 启动分布式训练
        results = []
        for worker_id in worker_assignments:
            result = self._start_worker_training(
                worker_id,
                config,
                distributed_id
            )
            results.append(result)
        
        # 汇总结果
        aggregated_result = self._aggregate_results(results)
        
        return {
            "distributed_id": distributed_id,
            "strategy": strategy,
            "n_workers": n_workers,
            "worker_results": results,
            "aggregated_result": aggregated_result
        }
    
    def _assign_workers(self, n_workers: int) -> List[str]:
        """分配工作节点"""
        available_workers = [
            wid for wid, status in self.worker_status.items()
            if status == "idle"
        ]
        
        if len(available_workers) < n_workers:
            logger.warning(f"Only {len(available_workers)} workers available, requested {n_workers}")
            return available_workers
        
        return available_workers[:n_workers]
    
    def _start_worker_training(
        self,
        worker_id: str,
        config: TrainingConfig,
        distributed_id: str
    ) -> Dict[str, Any]:
        """在工作节点启动训练"""
        self.worker_status[worker_id] = "busy"
        
        # 创建子训练任务
        worker_config = TrainingConfig(
            model_name=f"{config.model_name}_worker_{worker_id}",
            model_type=config.model_type,
            dataset_id=config.dataset_id,
            dataset_version=config.dataset_version,
            target_column=config.target_column,
            feature_columns=config.feature_columns,
            hyperparameters=config.hyperparameters,
            validation_split=config.validation_split,
            test_split=config.test_split,
            random_seed=config.random_seed + hash(worker_id) % 1000,  # 不同的随机种子
            early_stopping_patience=config.early_stopping_patience,
            max_epochs=config.max_epochs,
            batch_size=config.batch_size,
            learning_rate=config.learning_rate
        )
        
        job_result = self.create_training_job(worker_config, f"Worker {worker_id} training")
        train_result = self.start_training(job_result["training_id"])
        
        self.worker_status[worker_id] = "idle"
        
        return {
            "worker_id": worker_id,
            "training_result": train_result
        }
    
    def _aggregate_results(self, results: List[Dict]) -> Dict[str, Any]:
        """汇总结果"""
        successful_results = [
            r for r in results
            if r.get("training_result", {}).get("status") == "success"
        ]
        
        if not successful_results:
            return {"status": "failed", "message": "All workers failed"}
        
        # 聚合指标
        val_losses = [
            r["training_result"]["training_result"]["best_val_loss"]
            for r in successful_results
        ]
        
        return {
            "status": "success",
            "avg_val_loss": np.mean(val_losses),
            "std_val_loss": np.std(val_losses),
            "min_val_loss": np.min(val_losses),
            "max_val_loss": np.max(val_losses),
            "successful_workers": len(successful_results)
        }


# 示例使用
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # 创建训练器
    trainer = ModelTrainer()
    
    # 创建训练配置
    config = TrainingConfig(
        model_name="customer_churn_model",
        model_type=ModelType.CLASSIFICATION,
        dataset_id="customer_data",
        dataset_version="v1.0.0",
        target_column="churn",
        feature_columns=["age", "income", "usage", "tenure"],
        hyperparameters={
            "n_estimators": 100,
            "max_depth": 10
        },
        validation_split=0.2,
        max_epochs=50,
        early_stopping_patience=5
    )
    
    # 创建训练任务
    job_result = trainer.create_training_job(config, "Customer churn prediction model")
    training_id = job_result["training_id"]
    print(f"Training job created: {training_id}")
    
    # 启动训练
    train_result = trainer.start_training(training_id)
    
    if train_result["status"] == "success":
        result = train_result["training_result"]
        print(f"Training completed:")
        print(f"  Best epoch: {result['best_epoch']}")
        print(f"  Best val loss: {result['best_val_loss']:.4f}")
        print(f"  Duration: {result['duration_seconds']:.2f}s")
    
    # 超参数优化示例
    print("\n=== Hyperparameter Optimization ===")
    param_grid = {
        "n_estimators": HyperParameter(
            name="n_estimators",
            param_type="int",
            min_value=50,
            max_value=200,
            default=100
        ),
        "max_depth": HyperParameter(
            name="max_depth",
            param_type="int",
            min_value=5,
            max_value=20,
            default=10
        )
    }
    
    hpo_result = trainer.hyperparameter_optimization(
        config=config,
        param_grid=param_grid,
        optimizer=OptimizerType.RANDOM_SEARCH,
        n_trials=5
    )
    
    print(f"Best params: {hpo_result['best_params']}")
    print(f"Best val loss: {hpo_result['best_val_loss']:.4f}")