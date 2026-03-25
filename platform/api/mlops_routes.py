"""
MLOps API路由
提供实验追踪、模型注册、训练、部署等API
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import os

from auth.models import User
from auth.dependencies import get_current_active_user, require_developer

router = APIRouter(prefix="/mlops", tags=["mlops"])

_experiment_tracker = None
_model_registry = None


def get_experiment_tracker():
    global _experiment_tracker
    if _experiment_tracker is None:
        from mlops.tracking.experiment_tracker import ExperimentTracker
        _experiment_tracker = ExperimentTracker()
    return _experiment_tracker


def get_model_registry():
    global _model_registry
    if _model_registry is None:
        from mlops.tracking.model_registry import ModelRegistry
        _model_registry = ModelRegistry()
    return _model_registry


# ==================== 请求模型 ====================

class CreateExperimentRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    tags: Optional[List[str]] = None


class StartRunRequest(BaseModel):
    experiment_id: str
    name: Optional[str] = ""
    parameters: Optional[Dict[str, Any]] = None


class LogMetricRequest(BaseModel):
    run_id: str
    key: str
    value: float
    step: Optional[int] = None


class LogMetricsRequest(BaseModel):
    run_id: str
    metrics: Dict[str, float]
    step: Optional[int] = None


class CreateModelVersionRequest(BaseModel):
    name: str
    source_path: str
    run_id: Optional[str] = None
    experiment_id: Optional[str] = None
    metrics: Optional[Dict[str, float]] = None
    parameters: Optional[Dict[str, Any]] = None
    description: Optional[str] = ""
    tags: Optional[List[str]] = None
    framework: Optional[str] = "sklearn"


class TransitionStageRequest(BaseModel):
    name: str
    version: str
    stage: str
    archive_existing: Optional[bool] = True


# ==================== 实验追踪API ====================

@router.post("/experiments")
async def create_experiment(
    request: CreateExperimentRequest,
    current_user: User = Depends(require_developer)
):
    """创建实验"""
    tracker = get_experiment_tracker()
    experiment = tracker.create_experiment(
        name=request.name,
        description=request.description,
        tags=request.tags
    )
    return {"success": True, "experiment": experiment.to_dict()}


@router.get("/experiments")
async def list_experiments(
    status: Optional[str] = None,
    tags: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """列出实验"""
    tracker = get_experiment_tracker()
    from mlops.tracking.experiment_tracker import ExperimentStatus
    
    status_filter = ExperimentStatus(status) if status else None
    tag_filter = tags.split(",") if tags else None
    
    experiments = tracker.list_experiments(status=status_filter, tags=tag_filter)
    return {
        "success": True,
        "experiments": [e.to_dict() for e in experiments],
        "count": len(experiments)
    }


@router.get("/experiments/{experiment_id}")
async def get_experiment(
    experiment_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """获取实验详情"""
    tracker = get_experiment_tracker()
    experiment = tracker.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="实验不存在")
    return {"success": True, "experiment": experiment.to_dict()}


@router.delete("/experiments/{experiment_id}")
async def delete_experiment(
    experiment_id: str,
    current_user: User = Depends(require_developer)
):
    """删除实验"""
    tracker = get_experiment_tracker()
    success = tracker.delete_experiment(experiment_id)
    if not success:
        raise HTTPException(status_code=404, detail="实验不存在")
    return {"success": True, "message": "实验已删除"}


@router.post("/runs")
async def start_run(
    request: StartRunRequest,
    current_user: User = Depends(require_developer)
):
    """开始运行"""
    tracker = get_experiment_tracker()
    try:
        run = tracker.start_run(
            experiment_id=request.experiment_id,
            name=request.name,
            parameters=request.parameters
        )
        return {"success": True, "run": run.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/runs")
async def list_runs(
    experiment_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """列出运行"""
    tracker = get_experiment_tracker()
    from mlops.tracking.experiment_tracker import ExperimentStatus
    
    status_filter = ExperimentStatus(status) if status else None
    runs = tracker.list_runs(experiment_id=experiment_id, status=status_filter)
    return {
        "success": True,
        "runs": [r.to_dict() for r in runs],
        "count": len(runs)
    }


@router.get("/runs/{run_id}")
async def get_run(
    run_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """获取运行详情"""
    tracker = get_experiment_tracker()
    run = tracker.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="运行不存在")
    return {"success": True, "run": run.to_dict()}


@router.post("/runs/{run_id}/end")
async def end_run(
    run_id: str,
    status: str = "completed",
    current_user: User = Depends(require_developer)
):
    """结束运行"""
    tracker = get_experiment_tracker()
    from mlops.tracking.experiment_tracker import ExperimentStatus
    
    try:
        tracker.end_run(run_id, status=ExperimentStatus(status))
        return {"success": True, "message": "运行已结束"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/metrics")
async def log_metric(
    request: LogMetricRequest,
    current_user: User = Depends(require_developer)
):
    """记录指标"""
    tracker = get_experiment_tracker()
    tracker.log_metric(
        run_id=request.run_id,
        key=request.key,
        value=request.value,
        step=request.step
    )
    return {"success": True}


@router.post("/metrics/batch")
async def log_metrics(
    request: LogMetricsRequest,
    current_user: User = Depends(require_developer)
):
    """批量记录指标"""
    tracker = get_experiment_tracker()
    tracker.log_metrics(
        run_id=request.run_id,
        metrics=request.metrics,
        step=request.step
    )
    return {"success": True}


@router.get("/experiments/{experiment_id}/best-run")
async def get_best_run(
    experiment_id: str,
    metric_key: str,
    mode: str = "max",
    current_user: User = Depends(get_current_active_user)
):
    """获取最佳运行"""
    tracker = get_experiment_tracker()
    run = tracker.get_best_run(
        experiment_id=experiment_id,
        metric_key=metric_key,
        mode=mode
    )
    if not run:
        raise HTTPException(status_code=404, detail="没有找到运行")
    return {"success": True, "run": run.to_dict()}


@router.post("/runs/compare")
async def compare_runs(
    run_ids: List[str],
    metrics: Optional[List[str]] = None,
    current_user: User = Depends(get_current_active_user)
):
    """比较运行"""
    tracker = get_experiment_tracker()
    comparison = tracker.compare_runs(run_ids, metrics)
    return {"success": True, "comparison": comparison}


# ==================== 模型注册API ====================

@router.post("/models")
async def create_registered_model(
    name: str,
    description: Optional[str] = "",
    tags: Optional[str] = None,
    current_user: User = Depends(require_developer)
):
    """创建注册模型"""
    registry = get_model_registry()
    try:
        model = registry.create_registered_model(
            name=name,
            description=description,
            tags=tags.split(",") if tags else None
        )
        return {"success": True, "model": model.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/models")
async def list_registered_models(
    tags: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """列出注册模型"""
    registry = get_model_registry()
    tag_filter = tags.split(",") if tags else None
    models = registry.list_registered_models(tags=tag_filter)
    return {
        "success": True,
        "models": [m.to_dict() for m in models],
        "count": len(models)
    }


@router.get("/models/{name}")
async def get_registered_model(
    name: str,
    current_user: User = Depends(get_current_active_user)
):
    """获取注册模型"""
    registry = get_model_registry()
    model = registry.get_registered_model(name)
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")
    return {"success": True, "model": model.to_dict()}


@router.delete("/models/{name}")
async def delete_registered_model(
    name: str,
    current_user: User = Depends(require_developer)
):
    """删除注册模型"""
    registry = get_model_registry()
    success = registry.delete_registered_model(name)
    if not success:
        raise HTTPException(status_code=404, detail="模型不存在")
    return {"success": True, "message": "模型已删除"}


@router.post("/models/versions")
async def create_model_version(
    request: CreateModelVersionRequest,
    current_user: User = Depends(require_developer)
):
    """创建模型版本"""
    registry = get_model_registry()
    
    if not os.path.exists(request.source_path):
        raise HTTPException(status_code=400, detail="模型文件不存在")
    
    try:
        version = registry.create_model_version(
            name=request.name,
            source_path=request.source_path,
            run_id=request.run_id,
            experiment_id=request.experiment_id,
            metrics=request.metrics,
            parameters=request.parameters,
            description=request.description,
            tags=request.tags,
            framework=request.framework
        )
        return {"success": True, "version": version.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/models/{name}/versions/{version}")
async def get_model_version(
    name: str,
    version: str,
    current_user: User = Depends(get_current_active_user)
):
    """获取模型版本"""
    registry = get_model_registry()
    model_version = registry.get_model_version(name, version)
    if not model_version:
        raise HTTPException(status_code=404, detail="模型版本不存在")
    return {"success": True, "version": model_version.to_dict()}


@router.get("/models/{name}/versions/latest")
async def get_latest_version(
    name: str,
    current_user: User = Depends(get_current_active_user)
):
    """获取最新版本"""
    registry = get_model_registry()
    version = registry.get_latest_version(name)
    if not version:
        raise HTTPException(status_code=404, detail="没有找到版本")
    return {"success": True, "version": version.to_dict()}


@router.get("/models/{name}/versions/production")
async def get_production_version(
    name: str,
    current_user: User = Depends(get_current_active_user)
):
    """获取生产版本"""
    registry = get_model_registry()
    version = registry.get_production_version(name)
    if not version:
        raise HTTPException(status_code=404, detail="没有生产版本")
    return {"success": True, "version": version.to_dict()}


@router.post("/models/versions/transition")
async def transition_model_stage(
    request: TransitionStageRequest,
    current_user: User = Depends(require_developer)
):
    """转换模型阶段"""
    registry = get_model_registry()
    from mlops.tracking.model_registry import ModelStage
    
    try:
        version = registry.transition_model_version_stage(
            name=request.name,
            version=request.version,
            stage=ModelStage(request.stage),
            archive_existing=request.archive_existing
        )
        return {"success": True, "version": version.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/models/{name}/versions/{version}")
async def delete_model_version(
    name: str,
    version: str,
    current_user: User = Depends(require_developer)
):
    """删除模型版本"""
    registry = get_model_registry()
    success = registry.delete_model_version(name, version)
    if not success:
        raise HTTPException(status_code=404, detail="模型版本不存在")
    return {"success": True, "message": "模型版本已删除"}


@router.get("/models/versions/search")
async def search_model_versions(
    max_results: int = 100,
    current_user: User = Depends(get_current_active_user)
):
    """搜索模型版本"""
    registry = get_model_registry()
    versions = registry.search_model_versions(max_results=max_results)
    return {
        "success": True,
        "versions": [v.to_dict() for v in versions],
        "count": len(versions)
    }


# ==================== 模型上传API ====================

@router.post("/models/upload")
async def upload_model(
    file: UploadFile = File(...),
    name: str = "",
    current_user: User = Depends(require_developer)
):
    """上传模型文件"""
    upload_dir = "./uploads/models"
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, file.filename)
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    return {
        "success": True,
        "file_path": file_path,
        "file_name": file.filename,
        "file_size": len(content)
    }
