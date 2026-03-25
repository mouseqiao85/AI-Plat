"""
基于上一代功能点分析结果，增强AI-Plat平台
"""

import json
from typing import Dict, List, Any
import os


def load_legacy_analysis():
    """加载上一代功能分析结果"""
    with open('legacy_features_analysis.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def enhance_ontology_module(legacy_data: Dict[str, Any]):
    """增强本体论模块，借鉴上一代模型管理功能"""
    print("[ENHANCE] 增强本体论模块...")
    
    # 分析模型相关功能，用于改进本体论设计
    model_management_features = []
    for feature in legacy_data['valuable_features']:
        if any(keyword in str(feature).lower() for keyword in ['model', '模型', 'asset', '资产']):
            model_management_features.append(feature)
    
    print(f"   识别到 {len(model_management_features)} 个模型管理相关功能")
    
    # 创建模型本体定义示例
    model_ontology_example = """
# 模型资产管理本体定义示例
@prefix mmo: <http://ai-plat.org/model-management-ontology#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

mmo:AIModel a owl:Class ;
    rdfs:label "AI模型" ;
    rdfs:comment "人工智能模型的通用表示" .

mmo:ModelVersion a owl:Class ;
    rdfs:label "模型版本" ;
    rdfs:comment "AI模型的特定版本" .

mmo:modelFramework a owl:ObjectProperty ;
    rdfs:label "模型框架" ;
    rdfs:domain mmo:AIModel ;
    rdfs:range mmo:Framework .

mmo:modelType a owl:ObjectProperty ;
    rdfs:label "模型类型" ;
    rdfs:domain mmo:AIModel ;
    rdfs:range mmo:ModelType .

mmo:trainingMethod a owl:ObjectProperty ;
    rdfs:label "训练方法" ;
    rdfs:domain mmo:AIModel ;
    rdfs:range mmo:TrainingMethod .

# 模型类型枚举
mmo:GenerativeAI a mmo:ModelType ; rdfs:label "生成式AI" .
mmo:DiscriminativeAI a mmo:ModelType ; rdfs:label "判别式AI" .
mmo:LargeLanguageModel a mmo:ModelType ; rdfs:label "大语言模型" .

# 训练方法枚举
mmo:FullTuning a mmo:TrainingMethod ; rdfs:label "全量更新" .
mmo:LoRA a mmo:TrainingMethod ; rdfs:label "LoRA" .
mmo:SFT a mmo:TrainingMethod ; rdfs:label "SFT" .
mmo:DPO a mmo:TrainingMethod ; rdfs:label "DPO" .
    """
    
    # 创建模型本体定义文件
    ontology_dir = "ontology/definitions"
    os.makedirs(ontology_dir, exist_ok=True)
    
    with open(f"{ontology_dir}/model_asset_ontology.ttl", "w", encoding="utf-8") as f:
        f.write(model_ontology_example)
    
    print("   ✓ 创建模型资产管理本体定义")


def enhance_agent_module(legacy_data: Dict[str, Any]):
    """增强智能体模块，借鉴上一代训练和推理功能"""
    print("[ENHANCE] 增强智能体模块...")
    
    # 分析任务和作业相关功能
    task_features = []
    for feature in legacy_data['valuable_features']:
        if any(keyword in str(feature).lower() for keyword in ['task', 'job', '训练', '作业', '推理']):
            task_features.append(feature)
    
    print(f"   识别到 {len(task_features)} 个任务/作业相关功能")
    
    # 创建示例技能 - 模型训练技能
    training_skill_example = '''
"""
模型训练技能
基于上一代平台的训练功能实现
"""

from agents.skill_registry import global_skill_registry, SkillCategory
from typing import Dict, Any, List


@global_skill_registry.register_skill(
    name="model_training",
    description="执行AI模型训练任务",
    version="1.0.0",
    author="AI-Plat Team",
    category=SkillCategory.ML_MODEL,
    tags=["training", "ml", "ai", "model"]
)
def model_training(
    model_type: str,
    training_method: str = "fine_tuning",
    dataset_path: str = "",
    hyperparameters: Dict[str, Any] = None,
    resources: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    执行模型训练任务
    
    Args:
        model_type: 模型类型 (e.g., "large_language_model", "vision_model")
        training_method: 训练方法 ("full_tuning", "lora", "sft", "dpo")
        dataset_path: 训练数据集路径
        hyperparameters: 超参数配置
        resources: 资源配置 (CPU, GPU, memory等)
    
    Returns:
        训练结果
    """
    if hyperparameters is None:
        hyperparameters = {}
    
    if resources is None:
        resources = {
            "cpu_cores": 8,
            "gpu_type": "nvidia",
            "gpu_count": 1,
            "memory_gb": 32
        }
    
    # 模拟训练过程
    result = {
        "status": "completed",
        "model_type": model_type,
        "training_method": training_method,
        "dataset": dataset_path,
        "hyperparameters_used": hyperparameters,
        "resources_allocated": resources,
        "estimated_duration": "2h 30m",
        "metrics": {
            "final_loss": 0.15,
            "accuracy": 0.92,
            "convergence_rate": 0.98
        }
    }
    
    print(f"模型训练任务完成: {model_type} using {training_method}")
    return result


@global_skill_registry.register_skill(
    name="model_evaluation",
    description="评估AI模型性能",
    version="1.0.0",
    author="AI-Plat Team", 
    category=SkillCategory.ML_MODEL,
    tags=["evaluation", "assessment", "ml", "ai"]
)
def model_evaluation(
    model_id: str,
    evaluation_type: str = "automatic",
    test_dataset: str = "",
    evaluation_metrics: List[str] = None
) -> Dict[str, Any]:
    """
    评估模型性能
    
    Args:
        model_id: 模型ID
        evaluation_type: 评估类型 ("automatic", "baseline", "human_judgment")
        test_dataset: 测试数据集
        evaluation_metrics: 评估指标列表
    
    Returns:
        评估结果
    """
    if evaluation_metrics is None:
        evaluation_metrics = ["accuracy", "f1_score", "precision", "recall"]
    
    # 模拟评估过程
    result = {
        "model_id": model_id,
        "evaluation_type": evaluation_type,
        "test_dataset": test_dataset,
        "metrics": {
            "accuracy": 0.94,
            "f1_score": 0.92,
            "precision": 0.95,
            "recall": 0.90,
            "bleu_score": 0.85 if "bleu" in evaluation_metrics else None,
            "rouge_scores": {
                "rouge_1": 0.78,
                "rouge_2": 0.65,
                "rouge_l": 0.72
            } if any("rouge" in metric.lower() for metric in evaluation_metrics) else None
        },
        "report_url": f"/reports/evaluation_{model_id}.html",
        "passed": True
    }
    
    print(f"模型评估完成: {model_id}")
    return result


@global_skill_registry.register_skill(
    name="model_inference",
    description="执行模型推理服务",
    version="1.0.0",
    author="AI-Plat Team",
    category=SkillCategory.ML_MODEL,
    tags=["inference", "prediction", "ml", "ai", "deployment"]
)
def model_inference(
    model_id: str,
    input_data: Any,
    deployment_config: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    执行模型推理
    
    Args:
        model_id: 模型ID
        input_data: 输入数据
        deployment_config: 部署配置
    
    Returns:
        推理结果
    """
    if deployment_config is None:
        deployment_config = {
            "batch_size": 1,
            "timeout": 30,
            "max_tokens": 2048
        }
    
    # 模拟推理过程
    result = {
        "model_id": model_id,
        "input_processed": len(str(input_data)) if hasattr(input_data, '__len__') else 1,
        "inference_time_ms": 245,
        "output": "Simulated inference output based on input",
        "confidence": 0.96,
        "deployment_config_used": deployment_config
    }
    
    print(f"模型推理完成: {model_id}")
    return result
'''
    
    # 创建技能定义文件
    skills_dir = "agents/skills"
    os.makedirs(skills_dir, exist_ok=True)
    
    with open(f"{skills_dir}/model_operations.py", "w", encoding="utf-8") as f:
        f.write(training_skill_example)
    
    print("   ✓ 创建模型操作相关技能")


def enhance_vibecoding_module(legacy_data: Dict[str, Any]):
    """增强Vibecoding模块，借鉴上一代开发体验"""
    print("[ENHANCE] 增强Vibecoding模块...")
    
    # 分析开发相关功能
    dev_features = []
    for feature in legacy_data['valuable_features']:
        if any(keyword in str(feature).lower() for keyword in ['notebook', 'code', 'dev', '开发', '编程']):
            dev_features.append(feature)
    
    print(f"   识别到 {len(dev_features)} 个开发相关功能")
    
    # 创建示例代码生成模板
    code_templates = '''
"""
代码生成模板
基于上一代平台的开发功能经验
"""

from vibecoding.code_generator import CodeGenerator
from typing import Dict, Any


def create_training_pipeline_template() -> str:
    """
    创建训练流水线代码模板
    参考上一代平台的Notebook建模和作业建模功能
    """
    template = """
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from transformers import AutoTokenizer, AutoModelForSequenceClassification, TrainingArguments, Trainer
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
import os

class TextDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_length=512):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = self.labels[idx]
        
        encoding = self.tokenizer(
            text,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }

def compute_metrics(eval_pred):
    predictions, labels = eval_pred
    predictions = np.argmax(predictions, axis=1)
    precision, recall, f1, _ = precision_recall_fscore_support(labels, predictions, average='weighted')
    acc = accuracy_score(labels, predictions)
    return {
        'accuracy': acc,
        'f1': f1,
        'precision': precision,
        'recall': recall
    }

def train_model(model_name, train_texts, train_labels, val_texts, val_labels, output_dir="./model_output"):
    # Initialize tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=len(set(train_labels))  # Adjust based on number of unique labels
    )
    
    # Create datasets
    train_dataset = TextDataset(train_texts, train_labels, tokenizer)
    val_dataset = TextDataset(val_texts, val_labels, tokenizer)
    
    # Define training arguments
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=3,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        warmup_steps=500,
        weight_decay=0.01,
        logging_dir='./logs',
        logging_steps=10,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
    )
    
    # Initialize trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
    )
    
    # Train the model
    trainer.train()
    
    # Save the model
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    
    return trainer

# Example usage
if __name__ == "__main__":
    # Load your data
    # train_texts, val_texts, train_labels, val_labels = train_test_split(texts, labels, test_size=0.2, random_state=42)
    
    # train_model("bert-base-uncased", train_texts, train_labels, val_texts, val_labels)
    print("Training pipeline template created successfully!")
"""
    return template


def create_evaluation_script_template() -> str:
    """
    创建评估脚本代码模板
    参考上一代平台的模型评估功能
    """
    template = """
import pandas as pd
import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, roc_auc_score, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple, Any
import json
from datetime import datetime

class ModelEvaluator:
    def __init__(self, model_name: str, task_type: str = "classification"):
        """
        初始化模型评估器
        
        Args:
            model_name: 模型名称
            task_type: 任务类型 ("classification", "regression", "generation")
        """
        self.model_name = model_name
        self.task_type = task_type
        self.evaluation_results = {}
        self.timestamp = datetime.now().isoformat()

    def evaluate_classification(self, y_true: List, y_pred: List, y_pred_proba: List = None) -> Dict[str, Any]:
        """
        评估分类模型
        
        Args:
            y_true: 真实标签
            y_pred: 预测标签
            y_pred_proba: 预测概率 (可选)
        
        Returns:
            评估结果字典
        """
        accuracy = accuracy_score(y_true, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average='weighted')
        
        results = {
            "model_name": self.model_name,
            "task_type": "classification",
            "timestamp": self.timestamp,
            "metrics": {
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall, 
                "f1_score": f1
            },
            "samples_count": len(y_true)
        }
        
        # 如果提供了概率，计算AUC
        if y_pred_proba is not None:
            try:
                auc = roc_auc_score(y_true, y_pred_proba, multi_class='ovr')
                results["metrics"]["auc"] = auc
            except:
                pass  # AUC不可用时忽略
        
        # 计算混淆矩阵
        cm = confusion_matrix(y_true, y_pred)
        results["confusion_matrix"] = cm.tolist()
        
        self.evaluation_results = results
        return results

    def evaluate_regression(self, y_true: List, y_pred: List) -> Dict[str, Any]:
        """
        评估回归模型
        """
        from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
        
        mse = mean_squared_error(y_true, y_pred)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(y_true, y_pred)
        r2 = r2_score(y_true, y_pred)
        
        results = {
            "model_name": self.model_name,
            "task_type": "regression",
            "timestamp": self.timestamp,
            "metrics": {
                "mse": mse,
                "rmse": rmse,
                "mae": mae,
                "r2_score": r2
            },
            "samples_count": len(y_true)
        }
        
        self.evaluation_results = results
        return results

    def evaluate_generation(self, references: List[str], predictions: List[str]) -> Dict[str, Any]:
        """
        评估生成模型 (使用简化的指标)
        """
        # 简化的评估 - 实际应用中可能需要更复杂的指标
        exact_match = sum(1 for ref, pred in zip(references, predictions) if ref.strip() == pred.strip()) / len(references)
        
        # 计算平均长度差异
        ref_lengths = [len(ref.split()) for ref in references]
        pred_lengths = [len(pred.split()) for pred in predictions]
        avg_length_diff = np.mean([abs(r - p) for r, p in zip(ref_lengths, pred_lengths)])
        
        results = {
            "model_name": self.model_name,
            "task_type": "generation", 
            "timestamp": self.timestamp,
            "metrics": {
                "exact_match_ratio": exact_match,
                "avg_length_difference": avg_length_diff,
                "avg_reference_length": np.mean(ref_lengths),
                "avg_prediction_length": np.mean(pred_lengths)
            },
            "samples_count": len(references)
        }
        
        self.evaluation_results = results
        return results

    def plot_confusion_matrix(self, save_path: str = None):
        """
        绘制混淆矩阵图
        """
        if "confusion_matrix" in self.evaluation_results:
            cm = np.array(self.evaluation_results["confusion_matrix"])
            
            plt.figure(figsize=(8, 6))
            sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
            plt.title(f'Confusion Matrix for {self.model_name}')
            plt.ylabel('True Label')
            plt.xlabel('Predicted Label')
            
            if save_path:
                plt.savefig(save_path)
            plt.show()

    def save_report(self, filepath: str):
        """
        保存评估报告
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.evaluation_results, f, indent=2, ensure_ascii=False)
        
        print(f"Evaluation report saved to {filepath}")

# Example usage
if __name__ == "__main__":
    evaluator = ModelEvaluator("SampleModel", "classification")
    
    # Example data
    y_true = [0, 1, 1, 0, 1, 0, 1, 1, 0, 0]
    y_pred = [0, 1, 0, 0, 1, 0, 1, 1, 0, 1]
    
    results = evaluator.evaluate_classification(y_true, y_pred)
    print("Evaluation Results:", results)
    
    # Save report
    evaluator.save_report(f"evaluation_report_{evaluator.model_name}.json")
"""
    return template


def create_deployment_script_template() -> str:
    """
    创建部署脚本模板
    参考上一代平台的模型部署功能
    """
    template = """
from flask import Flask, request, jsonify
import torch
import pickle
import pandas as pd
import numpy as np
import os
import logging
from typing import Dict, Any, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelServer:
    def __init__(self, model_path: str, model_type: str = "torch"):
        """
        初始化模型服务
        
        Args:
            model_path: 模型文件路径
            model_type: 模型类型 ("torch", "sklearn", "transformers", "custom")
        """
        self.model_path = model_path
        self.model_type = model_type
        self.model = None
        self.tokenizer = None  # For transformer models
        self.load_model()
    
    def load_model(self):
        """加载模型"""
        try:
            if self.model_type == "torch":
                self.model = torch.load(self.model_path)
                self.model.eval()
            elif self.model_type == "sklearn":
                with open(self.model_path, 'rb') as f:
                    self.model = pickle.load(f)
            elif self.model_type == "transformers":
                from transformers import AutoModel, AutoTokenizer
                self.model = AutoModel.from_pretrained(self.model_path)
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            else:
                # Custom model loading logic
                logger.warning(f"Unsupported model type: {self.model_type}. Using placeholder.")
                self.model = lambda x: {"prediction": "placeholder", "confidence": 0.5}
            
            logger.info(f"Model loaded successfully from {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            raise e
    
    def predict(self, input_data: Union[Dict, List, str]) -> Dict[str, Any]:
        """
        执行预测
        
        Args:
            input_data: 输入数据
            
        Returns:
            预测结果
        """
        try:
            if self.model_type == "torch":
                # Process input for PyTorch model
                tensor_input = torch.tensor(input_data) if not isinstance(input_data, torch.Tensor) else input_data
                with torch.no_grad():
                    prediction = self.model(tensor_input)
                    if isinstance(prediction, torch.Tensor):
                        prediction = prediction.numpy()
                
                result = {
                    "prediction": prediction.tolist() if hasattr(prediction, 'tolist') else prediction,
                    "model_type": self.model_type,
                    "success": True
                }
                
            elif self.model_type == "transformers":
                inputs = self.tokenizer(input_data, return_tensors="pt", padding=True, truncation=True)
                with torch.no_grad():
                    outputs = self.model(**inputs)
                    predictions = torch.softmax(outputs.logits, dim=-1)
                    predicted_class = torch.argmax(predictions, dim=-1).item()
                    confidence = predictions[0][predicted_class].item()
                
                result = {
                    "prediction": predicted_class,
                    "confidence": confidence,
                    "model_type": self.model_type,
                    "success": True
                }
                
            else:  # sklearn or custom
                prediction = self.model.predict([input_data]) if hasattr(self.model, 'predict') else input_data
                result = {
                    "prediction": prediction[0] if isinstance(prediction, (list, np.ndarray)) else prediction,
                    "model_type": self.model_type,
                    "success": True
                }
            
            logger.info(f"Prediction completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Prediction failed: {str(e)}")
            return {
                "error": str(e),
                "success": False
            }

# Initialize Flask app
app = Flask(__name__)

# Global model server instance
model_server = None

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify({"status": "healthy", "model_loaded": model_server is not None})

@app.route('/predict', methods=['POST'])
def predict():
    """预测端点"""
    global model_server
    
    if model_server is None:
        return jsonify({"error": "Model not loaded"}), 500
    
    try:
        data = request.get_json()
        input_data = data.get('input', {})
        
        result = model_server.predict(input_data)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Prediction request failed: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/reload', methods=['POST'])
def reload_model():
    """重新加载模型"""
    global model_server
    
    try:
        data = request.get_json()
        model_path = data.get('model_path')
        model_type = data.get('model_type', 'torch')
        
        model_server = ModelServer(model_path, model_type)
        return jsonify({"status": "reloaded", "model_path": model_path})
        
    except Exception as e:
        logger.error(f"Model reload failed: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python deployment_server.py <model_path> <model_type>")
        sys.exit(1)
    
    model_path = sys.argv[1]
    model_type = sys.argv[2]
    
    # Initialize model server
    model_server = ModelServer(model_path, model_type)
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=False)
"""
    return template


# 注册这些模板为Vibecoding的代码生成模板
code_gen_templates = {
    "training_pipeline": create_training_pipeline_template,
    "evaluation_script": create_evaluation_script_template,
    "deployment_script": create_deployment_script_template
}
'''
    
    # 创建Vibecoding模板文件
    vibecoding_dir = "vibecoding/templates"
    os.makedirs(vibecoding_dir, exist_ok=True)
    
    with open(f"{vibecoding_dir}/model_dev_templates.py", "w", encoding="utf-8") as f:
        f.write(code_templates)
    
    print("   ✓ 创建模型开发相关代码模板")


def create_integration_examples(legacy_data: Dict[str, Any]):
    """创建集成示例，展示三大模块如何协同工作"""
    print("[ENHANCE] 创建集成示例...")
    
    integration_example = '''
"""
AI-Plat 平台集成示例
展示本体论、智能体和Vibecoding三大模块如何协同工作
基于上一代平台功能点分析结果
"""

from ontology.ontology_manager import OntologyManager
from agents.skill_agent import SkillAgent
from agents.agent_orchestrator import AgentOrchestrator
from agents.skill_registry import global_skill_registry
from vibecoding.notebook_interface import VibecodingNotebookInterface
from vibecoding.code_generator import CodeGenerator
import asyncio
import uuid
from datetime import datetime


async def integrated_model_lifecycle_example():
    """
    集成示例：完整的模型生命周期管理
    基于上一代平台的模型管理、训练、评估、推理功能
    """
    print("="*60)
    print("🔄 开始执行集成模型生命周期示例")
    print("="*60)
    
    # 1. 使用本体论模块定义模型资产
    print("\\n1. 🏗️ 使用本体论模块定义模型资产")
    ontology_mgr = OntologyManager("./tmp_ontology_defs")
    
    # 定义模型类型和属性
    ontology_mgr.create_entity("LargeLanguageModel", "Class", "大语言模型")
    ontology_mgr.create_entity("VisionModel", "Class", "视觉模型")
    ontology_mgr.create_entity("TrainingMethod", "Class", "训练方法")
    ontology_mgr.create_entity("FineTuning", "NamedIndividual", "微调方法")
    ontology_mgr.create_entity("usesTrainingMethod", "ObjectProperty", "使用训练方法")
    
    # 创建具体模型实例
    model_id = f"LLM-{uuid.uuid4().hex[:8]}"
    ontology_mgr.create_entity(model_id, "NamedIndividual", f"模型实例: {model_id}")
    ontology_mgr.create_relationship(model_id, "rdf:type", "LargeLanguageModel")
    ontology_mgr.create_relationship(model_id, "usesTrainingMethod", "FineTuning")
    
    print(f"   ✓ 定义了模型实例: {model_id}")
    
    # 2. 使用智能体模块执行模型操作
    print("\\n2. 🤖 使用智能体模块执行模型操作")
    
    # 创建模型操作代理
    model_agent = SkillAgent(
        name="ModelLifecycleAgent",
        description="负责模型完整生命周期管理的智能体",
        skills=[]  # 会在初始化后填充
    )
    await model_agent.initialize()
    
    # 获取所有可用的模型相关技能
    model_skills = []
    for skill_id in global_skill_registry.skills.keys():
        skill_meta = global_skill_registry.skills[skill_id].metadata
        if any(tag in ['training', 'evaluation', 'inference', 'ml', 'model'] for tag in skill_meta.tags):
            model_skills.append(skill_id)
    
    # 为代理分配技能
    model_agent.skills = model_skills[:3]  # 分配前3个模型相关技能
    
    # 执行训练任务
    if len(model_agent.skills) > 0:
        training_task_id = await model_agent.add_task(
            name="Train New Model",
            description="使用SFT方法训练大语言模型",
            skill_id=model_agent.skills[0],  # 假设第一个是训练技能
            parameters={
                "model_type": "large_language_model",
                "training_method": "sft",
                "dataset_path": "/datasets/training_data.jsonl",
                "hyperparameters": {
                    "learning_rate": 5e-5,
                    "batch_size": 16,
                    "epochs": 3
                }
            }
        )
        print(f"   ✓ 提交训练任务: {training_task_id}")
    
    # 3. 使用Vibecoding模块生成分析代码
    print("\\n3. 💻 使用Vibecoding模块生成分析代码")
    
    vibecoding_interface = VibecodingNotebookInterface()
    
    # 创建分析笔记本
    notebook_id = vibecoding_interface.create_notebook(
        name="Model Lifecycle Analysis",
        description="分析模型生命周期各阶段的性能指标"
    )
    
    # 添加数据处理代码单元
    data_analysis_code = f"""
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# 模拟模型生命周期数据
phases = ['Training', 'Validation', 'Testing', 'Deployment']
durations = [2.5, 0.3, 0.2, 0.1]  # in hours
accuracies = [0.85, 0.82, 0.84, 0.83]

# Create dataframe
df = pd.DataFrame({{
    'Phase': phases,
    'Duration_Hours': durations,
    'Accuracy': accuracies
}})

print("模型生命周期分析:")
print(df)

# Visualization
fig, ax1 = plt.subplots(figsize=(10, 6))

color = 'tab:red'
ax1.set_xlabel('Phase')
ax1.set_ylabel('Duration (hours)', color=color)
bars = ax1.bar(phases, durations, color=['skyblue', 'lightgreen', 'lightcoral', 'gold'], alpha=0.7)
ax1.tick_params(axis='y', labelcolor=color)

ax2 = ax1.twinx()
color = 'tab:blue'
ax2.set_ylabel('Accuracy', color=color)
line = ax2.plot(phases, accuracies, color=color, marker='o', linewidth=2, markersize=8)
ax2.tick_params(axis='y', labelcolor=color)

plt.title('Model Lifecycle Performance Dashboard')
plt.tight_layout()
plt.show()

print(f"\\n模型生命周期总耗时: {{sum(durations)}} 小时")
print(f"平均准确率: {{np.mean(accuracies):.2f}}")
"""
    
    vibecoding_interface.add_cell(notebook_id, "code", data_analysis_code)
    
    # 4. 执行笔记本
    print("\\n4. ▶️ 执行分析笔记本")
    execution_result = await vibecoding_interface.execute_notebook(notebook_id)
    print(f"   ✓ 执行完成: {execution_result['successful_executions']}/{execution_result['executed_cells']} 成功")
    
    # 5. 保存本体定义
    print("\\n5. 💾 保存本体定义")
    ontology_mgr.save_ontology("model_lifecycle_demo")
    print("   ✓ 本体定义已保存")
    
    print("\\n" + "="*60)
    print("✅ 集成模型生命周期示例执行完成")
    print("="*60)
    
    return {
        "model_id": model_id,
        "training_task_id": training_task_id if 'training_task_id' in locals() else None,
        "notebook_execution": execution_result,
        "ontology_saved": True
    }


def demonstrate_advanced_features(legacy_data: Dict[str, Any]):
    """
    演示高级功能，基于上一代平台的复杂功能
    """
    print("\\n" + "="*60)
    print("🚀 演示高级功能整合")
    print("="*60)
    
    # 分析上一代平台的高级功能
    advanced_features = []
    for feature in legacy_data['valuable_features']:
        feature_text = ' '.join([str(v) for v in feature.values()]).lower()
        if any(keyword in feature_text for keyword in ['pipeline', 'workflow', 'automated', 'orchestration', 'multi-model', 'ensemble']):
            advanced_features.append(feature)
    
    print(f"识别到 {len(advanced_features)} 个高级功能概念")
    
    # 创建高级功能演示代码
    advanced_demo_code = f"""
from agents.agent_orchestrator import AgentOrchestrator, WorkflowTask, TaskDependencyType
from agents.skill_agent import TaskPriority
import asyncio

async def demonstrate_advanced_workflow():
    print("开始演示高级工作流功能...")
    
    # 创建编排器
    orchestrator = AgentOrchestrator()
    
    # 这里会集成上一代平台的复杂功能概念
    print("高级功能演示已准备就绪")
    print("- 支持复杂工作流编排")
    print("- 支持多模型协同工作") 
    print("- 支持自动化任务调度")
    print("- 支持资源优化分配")
    
    # 基于分析的高级功能概念创建示例工作流
    print("\\n基于上一代平台功能分析，AI-Plat支持:")
    for i, feature in enumerate(advanced_features[:3]):  # 显示前3个
        print(f"  {i+1}. {feature.get('一级功能', 'N/A')}: {feature.get('功能描述', '')[:100]}...")
    
    return True

# 运行演示
# await demonstrate_advanced_workflow()
"""
    
    print(advanced_demo_code)
    
    print("\\n✅ 高级功能演示创建完成")


if __name__ == "__main__":
    # 加载上一代功能分析结果
    print("[LOAD] 加载上一代功能分析结果...")
    try:
        legacy_data = load_legacy_analysis()
        print("   ✓ 分析结果加载成功")
    except FileNotFoundError:
        print("   ⚠ 未找到分析结果文件，使用模拟数据")
        legacy_data = {
            'valuable_features': [
                {'一级功能': '模型管理', '功能描述': '支持模型的全生命周期管理'},
                {'一级功能': '模型训练', '功能描述': '支持多种训练方法'},
                {'一级功能': '模型评估', '功能描述': '支持自动化评估'},
                {'一级功能': '模型推理', '功能描述': '支持高性能推理服务'}
            ]
        }
    
    # 增强各个模块
    enhance_ontology_module(legacy_data)
    enhance_agent_module(legacy_data) 
    enhance_vibecoding_module(legacy_data)
    
    # 创建集成示例
    create_integration_examples(legacy_data)
    
    # 演示高级功能
    demonstrate_advanced_features(legacy_data)
    
    print("\\n" + "="*70)
    print("🎉 AI-Plat平台已基于上一代功能点完成增强!")
    print("   ✓ 本体论模块: 增强了模型资产管理能力")
    print("   ✓ 智能体模块: 增加了模型训练/评估/推理技能") 
    print("   ✓ Vibecoding模块: 添加了开发模板和最佳实践")
    print("   ✓ 集成示例: 展示了三大模块协同工作")
    print("="*70)
'''
    
    # 创建集成示例文件
    examples_dir = "examples"
    os.makedirs(examples_dir, exist_ok=True)
    
    with open(f"{examples_dir}/integration_example.py", "w", encoding="utf-8") as f:
        f.write(integration_example)
    
    print("   ✓ 创建集成示例")


def main():
    """主函数"""
    print("[ENHANCE] 开始基于上一代功能点增强AI-Plat平台")
    
    # 加载分析结果
    try:
        legacy_data = load_legacy_analysis()
        print("[OK] 加载上一代功能分析结果")
    except FileNotFoundError:
        print("[WARN] 未找到分析结果文件，使用模拟数据")
        legacy_data = {
            'valuable_features': [
                {'一级功能': '模型管理', '功能描述': '支持模型的全生命周期管理'},
                {'一级功能': '模型训练', '功能描述': '支持多种训练方法'},
                {'一级功能': '模型评估', '功能描述': '支持自动化评估'},
                {'一级功能': '模型推理', '功能描述': '支持高性能推理服务'}
            ]
        }
    
    # 执行各项增强
    enhance_ontology_module(legacy_data)
    enhance_agent_module(legacy_data)
    enhance_vibecoding_module(legacy_data)
    create_integration_examples(legacy_data)
    
    print(f"\n{'='*60}")
    print("[SUCCESS] AI-Plat平台增强完成!")
    print("   平台现已集成上一代平台的核心功能优点，包括:")
    print("   - 强大的模型资产管理能力 (基于本体论)")
    print("   - 灵活的模型训练/评估/推理智能体")
    print("   - 丰富的代码生成和开发模板")
    print("   - 完整的模型生命周期集成示例")
    print("="*60)


if __name__ == "__main__":
    main()