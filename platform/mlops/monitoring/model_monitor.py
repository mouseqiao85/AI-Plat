"""
MLOps平台模型监控模块
实现模型性能监控、数据漂移检测、告警系统和仪表盘功能
"""

import os
import json
import logging
import time
import threading
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict, field
from enum import Enum
from collections import deque
import statistics

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class DriftType(Enum):
    DATA_DRIFT = "data_drift"
    CONCEPT_DRIFT = "concept_drift"
    PREDICTION_DRIFT = "prediction_drift"


@dataclass
class MetricDataPoint:
    timestamp: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class Alert:
    alert_id: str
    deployment_id: str
    severity: AlertSeverity
    title: str
    message: str
    metric_name: str
    current_value: float
    threshold: float
    triggered_at: str
    acknowledged: bool = False
    acknowledged_at: Optional[str] = None
    resolved: bool = False
    resolved_at: Optional[str] = None


@dataclass
class DriftReport:
    report_id: str
    deployment_id: str
    drift_type: DriftType
    detected: bool
    drift_score: float
    threshold: float
    affected_features: List[str]
    details: Dict[str, Any]
    generated_at: str


class ModelMonitor:
    """
    模型监控器
    提供模型性能监控、数据漂移检测、告警系统和仪表盘功能
    """
    
    def __init__(self, storage_path: str = "./data/mlops/monitoring"):
        """
        初始化模型监控器
        
        Args:
            storage_path: 监控数据存储路径
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        (self.storage_path / "metrics").mkdir(exist_ok=True)
        (self.storage_path / "alerts").mkdir(exist_ok=True)
        (self.storage_path / "drifts").mkdir(exist_ok=True)
        (self.storage_path / "dashboards").mkdir(exist_ok=True)
        
        self.metrics_store: Dict[str, deque] = {}
        self.max_metrics_points = 10000
        
        self.alerts: Dict[str, Alert] = {}
        self.alert_rules: Dict[str, Dict] = self._init_alert_rules()
        
        self.baselines: Dict[str, Dict[str, Any]] = {}
        
        self.drift_detectors: Dict[str, Dict] = {}
        
        self._monitoring_active = False
        self._monitor_thread: Optional[threading.Thread] = None
    
    def _init_alert_rules(self) -> Dict[str, Dict]:
        """初始化告警规则"""
        return {
            "latency_p99_high": {
                "metric": "latency_p99_ms",
                "condition": "greater_than",
                "threshold": 500,
                "severity": AlertSeverity.WARNING,
                "message": "P99延迟超过阈值"
            },
            "latency_p99_critical": {
                "metric": "latency_p99_ms",
                "condition": "greater_than",
                "threshold": 1000,
                "severity": AlertSeverity.CRITICAL,
                "message": "P99延迟严重超标"
            },
            "error_rate_high": {
                "metric": "error_rate",
                "condition": "greater_than",
                "threshold": 0.05,
                "severity": AlertSeverity.ERROR,
                "message": "错误率超过阈值"
            },
            "accuracy_drop": {
                "metric": "accuracy",
                "condition": "less_than",
                "threshold": 0.80,
                "severity": AlertSeverity.WARNING,
                "message": "模型准确率下降"
            },
            "throughput_low": {
                "metric": "throughput_rps",
                "condition": "less_than",
                "threshold": 50,
                "severity": AlertSeverity.WARNING,
                "message": "吞吐量低于阈值"
            }
        }
    
    def record_metric(
        self,
        deployment_id: str,
        metric_name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ):
        """记录指标数据点"""
        key = f"{deployment_id}:{metric_name}"
        
        if key not in self.metrics_store:
            self.metrics_store[key] = deque(maxlen=self.max_metrics_points)
        
        data_point = MetricDataPoint(
            timestamp=datetime.now().isoformat(),
            value=value,
            labels=labels or {}
        )
        
        self.metrics_store[key].append(data_point)
        
        self._check_alert_rules(deployment_id, metric_name, value)
        
        self._persist_metric(deployment_id, metric_name, data_point)
    
    def _persist_metric(
        self,
        deployment_id: str,
        metric_name: str,
        data_point: MetricDataPoint
    ):
        """持久化指标数据"""
        date_str = datetime.now().strftime("%Y%m%d")
        metrics_file = self.storage_path / "metrics" / f"{deployment_id}_{date_str}.jsonl"
        
        with open(metrics_file, 'a') as f:
            f.write(json.dumps(asdict(data_point)) + '\n')
    
    def _check_alert_rules(
        self,
        deployment_id: str,
        metric_name: str,
        value: float
    ):
        """检查告警规则"""
        for rule_name, rule in self.alert_rules.items():
            if rule["metric"] != metric_name:
                continue
            
            triggered = False
            if rule["condition"] == "greater_than" and value > rule["threshold"]:
                triggered = True
            elif rule["condition"] == "less_than" and value < rule["threshold"]:
                triggered = True
            elif rule["condition"] == "equals" and value == rule["threshold"]:
                triggered = True
            
            if triggered:
                self._create_alert(
                    deployment_id=deployment_id,
                    rule_name=rule_name,
                    severity=rule["severity"],
                    message=rule["message"],
                    metric_name=metric_name,
                    current_value=value,
                    threshold=rule["threshold"]
                )
    
    def _create_alert(
        self,
        deployment_id: str,
        rule_name: str,
        severity: AlertSeverity,
        message: str,
        metric_name: str,
        current_value: float,
        threshold: float
    ):
        """创建告警"""
        alert_id = f"alert_{int(time.time() * 1000)}"
        
        alert = Alert(
            alert_id=alert_id,
            deployment_id=deployment_id,
            severity=severity,
            title=f"[{severity.value.upper()}] {metric_name}",
            message=message,
            metric_name=metric_name,
            current_value=current_value,
            threshold=threshold,
            triggered_at=datetime.now().isoformat()
        )
        
        self.alerts[alert_id] = alert
        self._persist_alert(alert)
        
        logger.warning(f"Alert created: {alert.title} - {alert.message}")
    
    def _persist_alert(self, alert: Alert):
        """持久化告警"""
        alerts_file = self.storage_path / "alerts" / "alerts.jsonl"
        with open(alerts_file, 'a') as f:
            alert_dict = asdict(alert)
            alert_dict['severity'] = alert.severity.value
            f.write(json.dumps(alert_dict) + '\n')
    
    def get_metrics(
        self,
        deployment_id: str,
        metric_name: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 1000
    ) -> List[MetricDataPoint]:
        """获取指标数据"""
        key = f"{deployment_id}:{metric_name}"
        
        if key not in self.metrics_store:
            return []
        
        data_points = list(self.metrics_store[key])
        
        if start_time:
            data_points = [dp for dp in data_points if dp.timestamp >= start_time]
        if end_time:
            data_points = [dp for dp in data_points if dp.timestamp <= end_time]
        
        return data_points[-limit:]
    
    def get_metric_statistics(
        self,
        deployment_id: str,
        metric_name: str,
        window_minutes: int = 60
    ) -> Dict[str, float]:
        """获取指标统计信息"""
        data_points = self.get_metrics(
            deployment_id,
            metric_name,
            limit=window_minutes * 60
        )
        
        if not data_points:
            return {"count": 0}
        
        values = [dp.value for dp in data_points]
        
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "std": statistics.stdev(values) if len(values) > 1 else 0,
            "p99": sorted(values)[int(len(values) * 0.99)] if values else 0
        }
    
    def set_baseline(
        self,
        deployment_id: str,
        metrics: Dict[str, float]
    ):
        """设置基线指标"""
        self.baselines[deployment_id] = {
            "metrics": metrics,
            "set_at": datetime.now().isoformat()
        }
        
        baseline_file = self.storage_path / "metrics" / f"{deployment_id}_baseline.json"
        with open(baseline_file, 'w') as f:
            json.dump(self.baselines[deployment_id], f, indent=2)
    
    def detect_drift(
        self,
        deployment_id: str,
        current_data: Dict[str, List[float]],
        drift_type: DriftType = DriftType.DATA_DRIFT
    ) -> DriftReport:
        """检测数据漂移"""
        report_id = f"drift_{int(time.time() * 1000)}"
        
        if deployment_id not in self.baselines:
            return DriftReport(
                report_id=report_id,
                deployment_id=deployment_id,
                drift_type=drift_type,
                detected=False,
                drift_score=0.0,
                threshold=0.1,
                affected_features=[],
                details={"error": "No baseline set"},
                generated_at=datetime.now().isoformat()
            )
        
        baseline_metrics = self.baselines[deployment_id]["metrics"]
        drift_scores = {}
        affected_features = []
        
        for feature, current_values in current_data.items():
            if feature not in baseline_metrics:
                continue
            
            baseline_value = baseline_metrics[feature]
            if baseline_value == 0:
                continue
            
            current_mean = statistics.mean(current_values) if current_values else 0
            drift_score = abs(current_mean - baseline_value) / abs(baseline_value)
            drift_scores[feature] = drift_score
            
            if drift_score > 0.1:
                affected_features.append(feature)
        
        overall_drift_score = max(drift_scores.values()) if drift_scores else 0
        
        report = DriftReport(
            report_id=report_id,
            deployment_id=deployment_id,
            drift_type=drift_type,
            detected=overall_drift_score > 0.1,
            drift_score=overall_drift_score,
            threshold=0.1,
            affected_features=affected_features,
            details={
                "feature_drift_scores": drift_scores,
                "baseline_set_at": self.baselines[deployment_id]["set_at"]
            },
            generated_at=datetime.now().isoformat()
        )
        
        drift_file = self.storage_path / "drifts" / f"{report_id}.json"
        with open(drift_file, 'w') as f:
            report_dict = asdict(report)
            report_dict['drift_type'] = drift_type.value
            json.dump(report_dict, f, indent=2, default=str)
        
        if report.detected:
            self._create_alert(
                deployment_id=deployment_id,
                rule_name="drift_detected",
                severity=AlertSeverity.WARNING,
                message=f"检测到{drift_type.value}，受影响特征: {', '.join(affected_features)}",
                metric_name="drift_score",
                current_value=overall_drift_score,
                threshold=0.1
            )
        
        return report
    
    def get_alerts(
        self,
        deployment_id: Optional[str] = None,
        severity: Optional[AlertSeverity] = None,
        acknowledged: Optional[bool] = None,
        resolved: Optional[bool] = None,
        limit: int = 100
    ) -> List[Alert]:
        """获取告警列表"""
        alerts = list(self.alerts.values())
        
        if deployment_id:
            alerts = [a for a in alerts if a.deployment_id == deployment_id]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]
        if resolved is not None:
            alerts = [a for a in alerts if a.resolved == resolved]
        
        return sorted(alerts, key=lambda x: x.triggered_at, reverse=True)[:limit]
    
    def acknowledge_alert(self, alert_id: str) -> Alert:
        """确认告警"""
        if alert_id not in self.alerts:
            raise ValueError(f"Alert not found: {alert_id}")
        
        alert = self.alerts[alert_id]
        alert.acknowledged = True
        alert.acknowledged_at = datetime.now().isoformat()
        
        return alert
    
    def resolve_alert(self, alert_id: str) -> Alert:
        """解决告警"""
        if alert_id not in self.alerts:
            raise ValueError(f"Alert not found: {alert_id}")
        
        alert = self.alerts[alert_id]
        alert.resolved = True
        alert.resolved_at = datetime.now().isoformat()
        
        return alert
    
    def get_dashboard_data(
        self,
        deployment_id: str
    ) -> Dict[str, Any]:
        """获取仪表盘数据"""
        latency_stats = self.get_metric_statistics(deployment_id, "latency_ms")
        throughput_stats = self.get_metric_statistics(deployment_id, "throughput_rps")
        error_rate_stats = self.get_metric_statistics(deployment_id, "error_rate")
        
        recent_alerts = self.get_alerts(deployment_id, limit=10)
        unresolved_alerts = [a for a in recent_alerts if not a.resolved]
        
        return {
            "deployment_id": deployment_id,
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "latency": latency_stats,
                "throughput": throughput_stats,
                "error_rate": error_rate_stats
            },
            "alerts": {
                "total": len(recent_alerts),
                "unresolved": len(unresolved_alerts),
                "recent": [asdict(a) for a in recent_alerts[:5]]
            },
            "health_status": self._calculate_health_status(
                latency_stats,
                throughput_stats,
                error_rate_stats,
                unresolved_alerts
            )
        }
    
    def _calculate_health_status(
        self,
        latency_stats: Dict,
        throughput_stats: Dict,
        error_rate_stats: Dict,
        unresolved_alerts: List[Alert]
    ) -> Dict[str, Any]:
        """计算健康状态"""
        score = 100
        
        if latency_stats.get("p99", 0) > 500:
            score -= 10
        if latency_stats.get("p99", 0) > 1000:
            score -= 20
        
        if error_rate_stats.get("mean", 0) > 0.01:
            score -= 15
        if error_rate_stats.get("mean", 0) > 0.05:
            score -= 25
        
        score -= len(unresolved_alerts) * 5
        
        score = max(0, min(100, score))
        
        if score >= 90:
            status = "healthy"
        elif score >= 70:
            status = "warning"
        elif score >= 50:
            status = "degraded"
        else:
            status = "critical"
        
        return {
            "score": score,
            "status": status
        }
    
    def add_alert_rule(
        self,
        rule_name: str,
        metric: str,
        condition: str,
        threshold: float,
        severity: AlertSeverity,
        message: str
    ):
        """添加告警规则"""
        self.alert_rules[rule_name] = {
            "metric": metric,
            "condition": condition,
            "threshold": threshold,
            "severity": severity,
            "message": message
        }
    
    def remove_alert_rule(self, rule_name: str):
        """移除告警规则"""
        if rule_name in self.alert_rules:
            del self.alert_rules[rule_name]
    
    def start_monitoring(self, interval_seconds: int = 60):
        """启动监控"""
        if self._monitoring_active:
            return
        
        self._monitoring_active = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval_seconds,),
            daemon=True
        )
        self._monitor_thread.start()
        logger.info("Monitoring started")
    
    def stop_monitoring(self):
        """停止监控"""
        self._monitoring_active = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("Monitoring stopped")
    
    def _monitor_loop(self, interval_seconds: int):
        """监控循环"""
        while self._monitoring_active:
            try:
                for deployment_id in self.baselines:
                    self._collect_deployment_metrics(deployment_id)
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
            
            time.sleep(interval_seconds)
    
    def _collect_deployment_metrics(self, deployment_id: str):
        """收集部署指标"""
        pass


if __name__ == "__main__":
    monitor = ModelMonitor()
    
    monitor.set_baseline("deploy_001", {
        "accuracy": 0.92,
        "latency_ms": 100,
        "throughput_rps": 200
    })
    
    monitor.record_metric("deploy_001", "latency_ms", 120)
    monitor.record_metric("deploy_001", "latency_ms", 550)
    
    dashboard = monitor.get_dashboard_data("deploy_001")
    print(f"Dashboard data: {json.dumps(dashboard, indent=2, default=str)}")
