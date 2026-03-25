"""
认知推理器
实现深度推理、不确定性推理、因果推理和反事实推理等高级认知能力
"""

from .ontology_manager import OntologyManager
from .inference_engine import InferenceEngine
from rdflib import Graph, URIRef, RDF, RDFS, OWL
from typing import Dict, List, Tuple, Optional, Any, Set
import logging
import random
from collections import defaultdict
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class CognitiveReasoner:
    """
    认知推理器
    提供高级认知推理能力：
    1. 深度推理：支持复杂的多步推理链
    2. 不确定性推理：处理不确定性和模糊信息
    3. 因果推理：识别和推理因果关系
    4. 反事实推理：支持假设性场景分析
    """
    
    def __init__(self, ontology_manager: OntologyManager, inference_engine: InferenceEngine):
        """
        初始化认知推理器
        
        Args:
            ontology_manager: 本体管理器实例
            inference_engine: 推理引擎实例
        """
        self.ontology_manager = ontology_manager
        self.inference_engine = inference_engine
        self.graph = ontology_manager.graph
        
        # 推理状态缓存
        self.reasoning_cache = {}
        self.causal_models = {}
        self.counterfactual_scenarios = {}
        
        # 配置参数
        self.max_reasoning_depth = 5
        self.confidence_threshold = 0.7
        self.similarity_threshold = 0.8
        
    def deep_reasoning(self, query: str, max_depth: int = None) -> Dict[str, Any]:
        """
        深度推理：执行复杂的多步推理链
        
        Args:
            query: 查询内容（可以是自然语言或结构化查询）
            max_depth: 最大推理深度
            
        Returns:
            深度推理结果
        """
        logger.info(f"Starting deep reasoning for query: {query}")
        
        if max_depth is None:
            max_depth = self.max_reasoning_depth
        
        # 解析查询
        parsed_query = self._parse_query(query)
        
        # 执行深度推理
        reasoning_result = self._execute_deep_reasoning(parsed_query, max_depth)
        
        # 生成解释
        explanation = self._generate_explanation(reasoning_result, parsed_query)
        
        return {
            "query": query,
            "parsed_query": parsed_query,
            "reasoning_result": reasoning_result,
            "explanation": explanation,
            "confidence": reasoning_result.get("confidence", 0.0),
            "depth_used": reasoning_result.get("depth", 0)
        }
    
    def _parse_query(self, query: str) -> Dict[str, Any]:
        """
        解析查询
        
        Args:
            query: 查询字符串
            
        Returns:
            解析后的查询结构
        """
        # 简化的查询解析
        # 在实际应用中，这里可以使用NLP模型进行更复杂的解析
        
        parsed = {
            "original": query,
            "type": "unknown",
            "entities": [],
            "relations": [],
            "intent": ""
        }
        
        # 基于关键词的简单分类
        query_lower = query.lower()
        
        if "why" in query_lower:
            parsed["type"] = "causal"
            parsed["intent"] = "explain_cause"
        elif "what if" in query_lower or "如果" in query_lower:
            parsed["type"] = "counterfactual"
            parsed["intent"] = "explore_scenario"
        elif "how" in query_lower:
            parsed["type"] = "procedural"
            parsed["intent"] = "explain_process"
        elif "relationship" in query_lower or "关系" in query_lower:
            parsed["type"] = "relational"
            parsed["intent"] = "find_relations"
        else:
            parsed["type"] = "factual"
            parsed["intent"] = "retrieve_information"
        
        # 提取实体（简化的正则匹配）
        import re
        entity_patterns = [
            r'[A-Z][a-z]+(?:\s[A-Z][a-z]+)*',  # 大写开头的词
            r'[A-Z]+(?:_[A-Z]+)*',            # 大写字母组成的标识符
            r'\b\d+\b'                         # 数字
        ]
        
        for pattern in entity_patterns:
            matches = re.findall(pattern, query)
            parsed["entities"].extend(matches)
        
        # 去重
        parsed["entities"] = list(set(parsed["entities"]))
        
        return parsed
    
    def _execute_deep_reasoning(self, parsed_query: Dict, max_depth: int) -> Dict[str, Any]:
        """
        执行深度推理
        
        Args:
            parsed_query: 解析后的查询
            max_depth: 最大推理深度
            
        Returns:
            推理结果
        """
        reasoning_steps = []
        visited_nodes = set()
        current_depth = 0
        
        # 初始化推理队列
        reasoning_queue = [{
            "node": parsed_query["entities"][0] if parsed_query["entities"] else "start",
            "path": [],
            "depth": 0,
            "confidence": 1.0
        }]
        
        while reasoning_queue and current_depth < max_depth:
            current_node = reasoning_queue.pop(0)
            node_id = current_node["node"]
            
            if node_id in visited_nodes:
                continue
                
            visited_nodes.add(node_id)
            current_depth = max(current_depth, current_node["depth"])
            
            # 扩展当前节点
            expansions = self._expand_node(node_id, current_node["path"], parsed_query["type"])
            
            for expansion in expansions:
                new_node = expansion["node"]
                new_path = current_node["path"] + [expansion]
                new_confidence = current_node["confidence"] * expansion.get("confidence", 0.8)
                
                # 检查是否达到目标
                if self._is_goal_reached(new_node, parsed_query):
                    reasoning_steps.append({
                        "step": len(reasoning_steps) + 1,
                        "node": new_node,
                        "path": new_path,
                        "confidence": new_confidence,
                        "depth": current_node["depth"] + 1,
                        "is_goal": True
                    })
                    continue
                
                # 如果置信度低于阈值，停止扩展
                if new_confidence < self.confidence_threshold:
                    continue
                
                reasoning_queue.append({
                    "node": new_node,
                    "path": new_path,
                    "depth": current_node["depth"] + 1,
                    "confidence": new_confidence
                })
                
                reasoning_steps.append({
                    "step": len(reasoning_steps) + 1,
                    "node": new_node,
                    "path": new_path,
                    "confidence": new_confidence,
                    "depth": current_node["depth"] + 1,
                    "is_goal": False
                })
        
        # 分析推理结果
        goal_steps = [step for step in reasoning_steps if step.get("is_goal", False)]
        
        if goal_steps:
            best_goal = max(goal_steps, key=lambda x: x["confidence"])
            return {
                "success": True,
                "result": best_goal["node"],
                "confidence": best_goal["confidence"],
                "path": best_goal["path"],
                "depth": best_goal["depth"],
                "total_steps": len(reasoning_steps),
                "reasoning_steps": reasoning_steps[:10]  # 只返回前10步
            }
        else:
            # 返回最佳的非目标节点
            if reasoning_steps:
                best_step = max(reasoning_steps, key=lambda x: x["confidence"])
                return {
                    "success": False,
                    "result": best_step["node"],
                    "confidence": best_step["confidence"],
                    "path": best_step["path"],
                    "depth": best_step["depth"],
                    "total_steps": len(reasoning_steps),
                    "reasoning_steps": reasoning_steps[:10],
                    "message": "No definitive answer found, returning best guess"
                }
            else:
                return {
                    "success": False,
                    "result": None,
                    "confidence": 0.0,
                    "depth": 0,
                    "total_steps": 0,
                    "reasoning_steps": [],
                    "message": "No reasoning paths found"
                }
    
    def _expand_node(self, node_id: str, current_path: List, reasoning_type: str) -> List[Dict]:
        """
        扩展节点
        
        Args:
            node_id: 节点标识符
            current_path: 当前路径
            reasoning_type: 推理类型
            
        Returns:
            扩展节点列表
        """
        expansions = []
        
        # 根据推理类型选择不同的扩展策略
        if reasoning_type == "causal":
            expansions.extend(self._expand_causal(node_id))
        elif reasoning_type == "counterfactual":
            expansions.extend(self._expand_counterfactual(node_id))
        else:
            expansions.extend(self._expand_general(node_id))
        
        # 去重（避免循环）
        path_nodes = [step["node"] for step in current_path]
        expansions = [exp for exp in expansions if exp["node"] not in path_nodes]
        
        return expansions
    
    def _expand_general(self, node_id: str) -> List[Dict]:
        """
        一般扩展：基于本体的关系扩展
        
        Args:
            node_id: 节点标识符
            
        Returns:
            扩展列表
        """
        expansions = []
        
        # 查询直接关系
        direct_query = f"""
        SELECT ?predicate ?object WHERE {{
            ?subject ?predicate ?object .
            FILTER (str(?subject) = "{node_id}" || str(?object) = "{node_id}")
        }}
        LIMIT 10
        """
        
        # 注意：这是一个简化的实现
        # 在实际应用中，需要将node_id映射到本体中的URI
        
        # 这里添加一些模拟的扩展
        if node_id == "start":
            expansions.append({"node": "concept_A", "relation": "related_to", "confidence": 0.9})
            expansions.append({"node": "concept_B", "relation": "related_to", "confidence": 0.8})
        elif "concept" in node_id.lower():
            expansions.append({"node": f"{node_id}_property", "relation": "has_property", "confidence": 0.85})
            expansions.append({"node": f"{node_id}_instance", "relation": "has_instance", "confidence": 0.75})
        
        return expansions
    
    def _expand_causal(self, node_id: str) -> List[Dict]:
        """
        因果扩展：基于因果关系的扩展
        
        Args:
            node_id: 节点标识符
            
        Returns:
            因果扩展列表
        """
        expansions = []
        
        # 查询可能的原因
        cause_expansions = self._find_possible_causes(node_id)
        expansions.extend(cause_expansions)
        
        # 查询可能的结果
        effect_expansions = self._find_possible_effects(node_id)
        expansions.extend(effect_expansions)
        
        return expansions
    
    def _expand_counterfactual(self, node_id: str) -> List[Dict]:
        """
        反事实扩展：基于假设场景的扩展
        
        Args:
            node_id: 节点标识符
            
        Returns:
            反事实扩展列表
        """
        expansions = []
        
        # 生成反事实假设
        counterfactuals = self._generate_counterfactuals(node_id)
        expansions.extend(counterfactuals)
        
        return expansions
    
    def _is_goal_reached(self, node: str, parsed_query: Dict) -> bool:
        """
        检查是否达到推理目标
        
        Args:
            node: 当前节点
            parsed_query: 解析后的查询
            
        Returns:
            是否达到目标
        """
        # 简化的目标检查
        query_text = parsed_query["original"].lower()
        
        # 如果查询中包含具体的目标词
        target_keywords = ["result", "answer", "conclusion", "solution"]
        for keyword in target_keywords:
            if keyword in query_text and keyword in node.lower():
                return True
        
        # 如果节点类型与查询意图匹配
        if parsed_query["intent"] == "explain_cause" and "cause" in node.lower():
            return True
        
        # 如果节点是已知的结论类型
        conclusion_indicators = ["therefore", "thus", "hence", "consequently"]
        for indicator in conclusion_indicators:
            if indicator in node.lower():
                return True
        
        return False
    
    def _generate_explanation(self, reasoning_result: Dict, parsed_query: Dict) -> str:
        """
        生成推理解释
        
        Args:
            reasoning_result: 推理结果
            parsed_query: 解析后的查询
            
        Returns:
            解释文本
        """
        if not reasoning_result.get("success", False):
            return "无法找到明确的答案。推理过程中未发现满足条件的结论。"
        
        steps = reasoning_result.get("reasoning_steps", [])
        result = reasoning_result.get("result", "")
        confidence = reasoning_result.get("confidence", 0.0)
        
        explanation_parts = []
        
        # 添加查询类型解释
        query_type = parsed_query.get("type", "factual")
        if query_type == "causal":
            explanation_parts.append("这是一个因果推理问题，旨在找出事件发生的原因。")
        elif query_type == "counterfactual":
            explanation_parts.append("这是一个反事实推理问题，探讨假设情景下的可能性。")
        
        # 添加推理过程摘要
        if steps:
            key_steps = [step for step in steps if step.get("confidence", 0) > 0.7][:3]
            if key_steps:
                explanation_parts.append("推理过程涉及以下关键步骤：")
                for i, step in enumerate(key_steps, 1):
                    node = step.get("node", "unknown")
                    confidence = step.get("confidence", 0.0)
                    explanation_parts.append(f"{i}. 考虑 {node} (置信度: {confidence:.2f})")
        
        # 添加结论
        explanation_parts.append(f"基于以上推理，结论是：{result}")
        explanation_parts.append(f"整体置信度为：{confidence:.2f}")
        
        return "\n".join(explanation_parts)
    
    def uncertain_reasoning(self, query: str, evidence: Dict[str, float] = None) -> Dict[str, Any]:
        """
        不确定性推理：处理不确定和模糊信息
        
        Args:
            query: 查询内容
            evidence: 证据及其置信度
            
        Returns:
            不确定性推理结果
        """
        logger.info(f"Starting uncertain reasoning for query: {query}")
        
        # 解析查询
        parsed_query = self._parse_query(query)
        
        # 收集证据
        if evidence is None:
            evidence = self._collect_evidence(parsed_query)
        
        # 执行不确定性推理
        reasoning_result = self._execute_uncertain_reasoning(parsed_query, evidence)
        
        return {
            "query": query,
            "parsed_query": parsed_query,
            "evidence": evidence,
            "reasoning_result": reasoning_result,
            "overall_confidence": reasoning_result.get("confidence", 0.0)
        }
    
    def _collect_evidence(self, parsed_query: Dict) -> Dict[str, float]:
        """
        收集证据
        
        Args:
            parsed_query: 解析后的查询
            
        Returns:
            证据字典
        """
        evidence = {}
        
        # 基于本体的证据收集
        for entity in parsed_query.get("entities", []):
            # 查询实体的相关事实
            related_facts = self._query_related_facts(entity)
            for fact in related_facts:
                fact_key = f"{entity}_{fact['property']}"
                evidence[fact_key] = fact.get("confidence", 0.7)
        
        # 添加默认证据
        if not evidence:
            evidence["default_knowledge"] = 0.6
            evidence["common_sense"] = 0.5
        
        return evidence
    
    def _query_related_facts(self, entity: str) -> List[Dict]:
        """
        查询实体的相关事实
        
        Args:
            entity: 实体名称
            
        Returns:
            相关事实列表
        """
        # 简化的实现
        # 在实际应用中，这里应该查询本体图
        
        facts = []
        
        # 模拟一些事实
        if "person" in entity.lower():
            facts.append({
                "property": "is_human",
                "value": True,
                "confidence": 0.95
            })
            facts.append({
                "property": "has_name",
                "value": entity,
                "confidence": 0.8
            })
        elif "product" in entity.lower():
            facts.append({
                "property": "is_tangible",
                "value": True,
                "confidence": 0.9
            })
        
        return facts
    
    def _execute_uncertain_reasoning(self, parsed_query: Dict, evidence: Dict[str, float]) -> Dict[str, Any]:
        """
        执行不确定性推理
        
        Args:
            parsed_query: 解析后的查询
            evidence: 证据字典
            
        Returns:
            推理结果
        """
        # 使用简化的概率模型
        # 在实际应用中，可以使用贝叶斯网络、模糊逻辑等
        
        # 计算总体置信度
        evidence_values = list(evidence.values())
        if evidence_values:
            avg_confidence = sum(evidence_values) / len(evidence_values)
        else:
            avg_confidence = 0.5
        
        # 根据查询类型调整置信度
        query_type = parsed_query.get("type", "factual")
        type_adjustment = {
            "factual": 1.0,
            "causal": 0.8,
            "counterfactual": 0.6,
            "procedural": 0.7,
            "relational": 0.9
        }
        
        adjusted_confidence = avg_confidence * type_adjustment.get(query_type, 0.7)
        
        # 生成推理结果
        result = f"基于{len(evidence)}条证据的分析结果"
        
        return {
            "result": result,
            "confidence": adjusted_confidence,
            "evidence_count": len(evidence),
            "evidence_summary": {k: f"{v:.2f}" for k, v in list(evidence.items())[:5]}
        }
    
    def causal_reasoning(self, event: str, depth: int = 3) -> Dict[str, Any]:
        """
        因果推理：识别和推理因果关系
        
        Args:
            event: 事件描述
            depth: 推理深度
            
        Returns:
            因果推理结果
        """
        logger.info(f"Starting causal reasoning for event: {event}")
        
        # 解析事件
        parsed_event = self._parse_event(event)
        
        # 构建因果模型
        causal_model = self._build_causal_model(parsed_event, depth)
        
        # 执行因果推理
        reasoning_result = self._execute_causal_reasoning(causal_model, parsed_event)
        
        # 缓存因果模型
        model_id = f"causal_{hash(event)}"
        self.causal_models[model_id] = {
            "model": causal_model,
            "timestamp": datetime.now().isoformat(),
            "event": event
        }
        
        return {
            "event": event,
            "parsed_event": parsed_event,
            "causal_model": causal_model,
            "reasoning_result": reasoning_result,
            "model_id": model_id
        }
    
    def _parse_event(self, event: str) -> Dict[str, Any]:
        """
        解析事件
        
        Args:
            event: 事件描述
            
        Returns:
            解析后的事件结构
        """
        # 简化的事件解析
        parsed = {
            "original": event,
            "main_subject": "",
            "main_action": "",
            "main_object": "",
            "time_reference": "",
            "location_reference": ""
        }
        
        # 提取关键词
        words = event.lower().split()
        action_verbs = ["caused", "led", "resulted", "affected", "influenced"]
        
        for word in words:
            if word in action_verbs:
                parsed["main_action"] = word
            elif word.isupper() or word[0].isupper():
                if not parsed["main_subject"]:
                    parsed["main_subject"] = word
        
        return parsed
    
    def _build_causal_model(self, parsed_event: Dict, depth: int) -> Dict[str, Any]:
        """
        构建因果模型
        
        Args:
            parsed_event: 解析后的事件
            depth: 模型深度
            
        Returns:
            因果模型
        """
        model = {
            "root_event": parsed_event,
            "depth": depth,
            "causes": [],
            "effects": [],
            "mediators": [],
            "confounders": []
        }
        
        # 识别可能的原因
        subject = parsed_event.get("main_subject", "")
        if subject:
            # 查询历史模式
            historical_patterns = self._query_historical_patterns(subject)
            model["causes"].extend(historical_patterns)
        
        # 识别可能的结果
        action = parsed_event.get("main_action", "")
        if action:
            potential_effects = self._infer_potential_effects(action, subject)
            model["effects"].extend(potential_effects)
        
        # 识别中介变量和混杂因素
        if subject and action:
            mediators = self._identify_mediators(subject, action)
            model["mediators"].extend(mediators)
            
            confounders = self._identify_confounders(subject, action)
            model["confounders"].extend(confounders)
        
        return model
    
    def _query_historical_patterns(self, subject: str) -> List[Dict]:
        """
        查询历史模式
        
        Args:
            subject: 主体
            
        Returns:
            历史模式列表
        """
        # 简化的实现
        patterns = []
        
        if "sales" in subject.lower():
            patterns.append({
                "cause": "marketing_campaign",
                "effect": "increased_sales",
                "confidence": 0.75,
                "frequency": 3
            })
        
        if "production" in subject.lower():
            patterns.append({
                "cause": "equipment_upgrade",
                "effect": "improved_efficiency",
                "confidence": 0.8,
                "frequency": 2
            })
        
        return patterns
    
    def _infer_potential_effects(self, action: str, subject: str) -> List[Dict]:
        """
        推断潜在结果
        
        Args:
            action: 行动
            subject: 主体
            
        Returns:
            潜在结果列表
        """
        effects = []
        
        if "increase" in action.lower():
            effects.append({
                "effect": f"higher_{subject}_levels",
                "confidence": 0.7,
                "timeframe": "short_term"
            })
        elif "decrease" in action.lower():
            effects.append({
                "effect": f"lower_{subject}_levels",
                "confidence": 0.7,
                "timeframe": "short_term"
            })
        
        return effects
    
    def _identify_mediators(self, subject: str, action: str) -> List[Dict]:
        """
        识别中介变量
        
        Args:
            subject: 主体
            action: 行动
            
        Returns:
            中介变量列表
        """
        mediators = []
        
        # 基于领域知识的简单识别
        if "sales" in subject.lower() and "increase" in action.lower():
            mediators.append({
                "mediator": "customer_awareness",
                "role": "transmits_effect",
                "confidence": 0.6
            })
        
        return mediators
    
    def _identify_confounders(self, subject: str, action: str) -> List[Dict]:
        """
        识别混杂因素
        
        Args:
            subject: 主体
            action: 行动
            
        Returns:
            混杂因素列表
        """
        confounders = []
        
        if "sales" in subject.lower():
            confounders.append({
                "confounder": "seasonal_demand",
                "effect": "may_appear_as_cause",
                "confidence": 0.65
            })
            confounders.append({
                "confounder": "economic_conditions",
                "effect": "simultaneously_affects",
                "confidence": 0.7
            })
        
        return confounders
    
    def _execute_causal_reasoning(self, causal_model: Dict, parsed_event: Dict) -> Dict[str, Any]:
        """
        执行因果推理
        
        Args:
            causal_model: 因果模型
            parsed_event: 解析后的事件
            
        Returns:
            推理结果
        """
        # 分析因果强度
        causes = causal_model.get("causes", [])
        effects = causal_model.get("effects", [])
        
        if not causes and not effects:
            return {
                "conclusion": "因果关系不明确",
                "confidence": 0.3,
                "reasoning": "缺乏足够的因果证据"
            }
        
        # 计算平均置信度
        all_items = causes + effects
        if all_items:
            avg_confidence = sum(item.get("confidence", 0) for item in all_items) / len(all_items)
        else:
            avg_confidence = 0.5
        
        # 生成结论
        if causes:
            strongest_cause = max(causes, key=lambda x: x.get("confidence", 0))
            conclusion = f"事件的主要原因可能是：{strongest_cause.get('cause', 'unknown')}"
        else:
            conclusion = "未发现明确的因果关系"
        
        return {
            "conclusion": conclusion,
            "confidence": avg_confidence,
            "causes_found": len(causes),
            "effects_found": len(effects),
            "strongest_cause": strongest_cause if causes else None
        }
    
    def counterfactual_reasoning(self, scenario: str, alternative: str = None) -> Dict[str, Any]:
        """
        反事实推理：分析假设性场景
        
        Args:
            scenario: 原始场景描述
            alternative: 替代场景描述
            
        Returns:
            反事实推理结果
        """
        logger.info(f"Starting counterfactual reasoning for scenario: {scenario}")
        
        # 解析场景
        parsed_scenario = self._parse_scenario(scenario)
        
        # 生成替代场景
        if alternative is None:
            alternative = self._generate_alternative_scenario(parsed_scenario)
        
        parsed_alternative = self._parse_scenario(alternative)
        
        # 执行反事实推理
        reasoning_result = self._execute_counterfactual_reasoning(parsed_scenario, parsed_alternative)
        
        # 缓存场景
        scenario_id = f"counterfactual_{hash(scenario)}"
        self.counterfactual_scenarios[scenario_id] = {
            "original": parsed_scenario,
            "alternative": parsed_alternative,
            "result": reasoning_result,
            "timestamp": datetime.now().isoformat()
        }
        
        return {
            "original_scenario": scenario,
            "alternative_scenario": alternative,
            "parsed_original": parsed_scenario,
            "parsed_alternative": parsed_alternative,
            "reasoning_result": reasoning_result,
            "scenario_id": scenario_id
        }
    
    def _parse_scenario(self, scenario: str) -> Dict[str, Any]:
        """
        解析场景
        
        Args:
            scenario: 场景描述
            
        Returns:
            解析后的场景
        """
        parsed = {
            "original": scenario,
            "agents": [],
            "actions": [],
            "states": [],
            "conditions": [],
            "outcomes": []
        }
        
        # 简化的解析
        words = scenario.lower().split()
        
        # 识别代理
        agent_keywords = ["company", "person", "team", "organization", "system"]
        parsed["agents"] = [word for word in words if word in agent_keywords]
        
        # 识别行动
        action_keywords = ["did", "made", "created", "built", "implemented"]
        parsed["actions"] = [word for word in words if word in action_keywords]
        
        # 识别状态
        state_keywords = ["successful", "failed", "efficient", "inefficient"]
        parsed["states"] = [word for word in words if word in state_keywords]
        
        # 识别条件
        condition_keywords = ["if", "when", "given", "assuming"]
        parsed["conditions"] = [word for word in words if word in condition_keywords]
        
        return parsed
    
    def _generate_alternative_scenario(self, parsed_scenario: Dict) -> str:
        """
        生成替代场景
        
        Args:
            parsed_scenario: 解析后的原始场景
            
        Returns:
            替代场景描述
        """
        # 基于原始场景生成替代场景
        original = parsed_scenario["original"]
        
        # 简单的替换规则
        replacements = {
            "successful": "unsuccessful",
            "failed": "succeeded",
            "increased": "decreased",
            "decreased": "increased",
            "efficient": "inefficient",
            "inefficient": "efficient"
        }
        
        alternative = original
        for old, new in replacements.items():
            if old in original.lower():
                alternative = alternative.lower().replace(old, new)
                break
        
        # 如果没有替换，添加否定词
        if alternative == original:
            alternative = f"What if {original} had not happened?"
        
        return alternative.capitalize()
    
    def _execute_counterfactual_reasoning(self, original: Dict, alternative: Dict) -> Dict[str, Any]:
        """
        执行反事实推理
        
        Args:
            original: 原始场景
            alternative: 替代场景
            
        Returns:
            推理结果
        """
        # 分析场景差异
        differences = self._analyze_scenario_differences(original, alternative)
        
        # 推断可能的结果
        consequences = self._infer_counterfactual_consequences(differences)
        
        # 评估可能性
        plausibility = self._assess_counterfactual_plausibility(original, alternative)
        
        return {
            "differences_identified": differences,
            "potential_consequences": consequences,
            "plausibility_assessment": plausibility,
            "conclusion": self._generate_counterfactual_conclusion(differences, consequences, plausibility)
        }
    
    def _analyze_scenario_differences(self, original: Dict, alternative: Dict) -> List[Dict]:
        """
        分析场景差异
        
        Args:
            original: 原始场景
            alternative: 替代场景
            
        Returns:
            差异列表
        """
        differences = []
        
        # 比较代理
        orig_agents = set(original.get("agents", []))
        alt_agents = set(alternative.get("agents", []))
        agent_diff = alt_agents - orig_agents
        if agent_diff:
            differences.append({
                "aspect": "agents",
                "change": f"added_agents: {list(agent_diff)}"
            })
        
        # 比较行动
        orig_actions = set(original.get("actions", []))
        alt_actions = set(alternative.get("actions", []))
        action_diff = alt_actions - orig_actions
        if action_diff:
            differences.append({
                "aspect": "actions",
                "change": f"different_actions: {list(action_diff)}"
            })
        
        # 比较状态
        orig_states = set(original.get("states", []))
        alt_states = set(alternative.get("states", []))
        state_diff = alt_states - orig_states
        if state_diff:
            differences.append({
                "aspect": "states",
                "change": f"changed_states: {list(state_diff)}"
            })
        
        return differences
    
    def _infer_counterfactual_consequences(self, differences: List[Dict]) -> List[Dict]:
        """
        推断反事实后果
        
        Args:
            differences: 场景差异
            
        Returns:
            潜在后果列表
        """
        consequences = []
        
        for diff in differences:
            aspect = diff.get("aspect", "")
            change = diff.get("change", "")
            
            if "agents" in aspect:
                consequences.append({
                    "consequence": "different_decision_makers",
                    "confidence": 0.7,
                    "impact": "medium"
                })
            elif "actions" in aspect:
                consequences.append({
                    "consequence": "alternative_outcomes",
                    "confidence": 0.8,
                    "impact": "high"
                })
            elif "states" in aspect:
                if "successful" in change or "unsuccessful" in change:
                    consequences.append({
                        "consequence": "reversed_success_outcome",
                        "confidence": 0.75,
                        "impact": "high"
                    })
        
        return consequences
    
    def _assess_counterfactual_plausibility(self, original: Dict, alternative: Dict) -> Dict[str, float]:
        """
        评估反事实可能性
        
        Args:
            original: 原始场景
            alternative: 替代场景
            
        Returns:
            可能性评估
        """
        plausibility = {
            "historical_precedence": 0.4,
            "causal_consistency": 0.6,
            "temporal_feasibility": 0.7,
            "resource_availability": 0.5
        }
        
        # 简单的评估规则
        orig_text = original.get("original", "").lower()
        alt_text = alternative.get("original", "").lower()
        
        if "not" in alt_text and "not" not in orig_text:
            plausibility["historical_precedence"] = 0.6
        
        if len(orig_text.split()) < 10 and len(alt_text.split()) < 10:
            plausibility["causal_consistency"] = 0.8
        
        # 计算总体可能性
        avg_plausibility = sum(plausibility.values()) / len(plausibility)
        
        return {
            "aspect_scores": plausibility,
            "overall_plausibility": avg_plausibility,
            "interpretation": self._interpret_plausibility(avg_plausibility)
        }
    
    def _interpret_plausibility(self, score: float) -> str:
        """
        解释可能性分数
        
        Args:
            score: 可能性分数
            
        Returns:
            解释文本
        """
        if score >= 0.8:
            return "高度可能"
        elif score >= 0.6:
            return "中等可能"
        elif score >= 0.4:
            return "较低可能"
        else:
            return "不太可能"
    
    def _generate_counterfactual_conclusion(self, differences: List[Dict], 
                                           consequences: List[Dict], 
                                           plausibility: Dict) -> str:
        """
        生成反事实结论
        
        Args:
            differences: 差异
            consequences: 后果
            plausibility: 可能性评估
            
        Returns:
            结论文本
        """
        conclusion_parts = []
        
        if differences:
            diff_desc = "、".join([d["aspect"] for d in differences])
            conclusion_parts.append(f"场景在{diff_desc}方面存在差异。")
        
        if consequences:
            cons_desc = "、".join([c["consequence"] for c in consequences])
            conclusion_parts.append(f"这些差异可能导致{cons_desc}。")
        
        plausibility_score = plausibility.get("overall_plausibility", 0.5)
        interpretation = plausibility.get("interpretation", "不确定")
        conclusion_parts.append(f"这个反事实场景的总体可能性为{plausibility_score:.2f}，属于{interpretation}的情况。")
        
        return " ".join(conclusion_parts)
    
    def _find_possible_causes(self, event: str) -> List[Dict]:
        """
        查找可能的原因
        
        Args:
            event: 事件
            
        Returns:
            可能的原因列表
        """
        causes = []
        
        # 基于常见因果模式
        if "sales_decrease" in event.lower():
            causes.append({
                "node": "economic_downturn",
                "relation": "may_cause",
                "confidence": 0.7
            })
            causes.append({
                "node": "competitor_action",
                "relation": "could_cause",
                "confidence": 0.6
            })
        
        return causes
    
    def _find_possible_effects(self, event: str) -> List[Dict]:
        """
        查找可能的结果
        
        Args:
            event: 事件
            
        Returns:
            可能的结果列表
        """
        effects = []
        
        if "investment" in event.lower():
            effects.append({
                "node": "future_growth",
                "relation": "leads_to",
                "confidence": 0.65
            })
        
        return effects
    
    def _generate_counterfactuals(self, event: str) -> List[Dict]:
        """
        生成反事实假设
        
        Args:
            event: 事件
            
        Returns:
            反事实假设列表
        """
        counterfactuals = []
        
        if "success" in event.lower():
            counterfactuals.append({
                "node": "failure_scenario",
                "relation": "counterfactual_of",
                "confidence": 0.5
            })
        elif "failure" in event.lower():
            counterfactuals.append({
                "node": "success_scenario",
                "relation": "counterfactual_of",
                "confidence": 0.5
            })
        
        return counterfactuals


# 示例使用
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # 创建本体管理器和推理引擎
    om = OntologyManager()
    ie = InferenceEngine(om)
    
    # 创建认知推理器
    cr = CognitiveReasoner(om, ie)
    
    # 深度推理示例
    print("=== 深度推理示例 ===")
    deep_result = cr.deep_reasoning("Why did sales increase last quarter?")
    print(f"查询: {deep_result['query']}")
    print(f"结果: {deep_result['reasoning_result']['result']}")
    print(f"置信度: {deep_result['confidence']:.2f}")
    print(f"解释: {deep_result['explanation']}")
    print()
    
    # 不确定性推理示例
    print("=== 不确定性推理示例 ===")
    uncertain_result = cr.uncertain_reasoning(
        "Will the new product be successful?",
        evidence={"market_research": 0.8, "team_experience": 0.7, "competitive_landscape": 0.5}
    )
    print(f"查询: {uncertain_result['query']}")
    print(f"结果: {uncertain_result['reasoning_result']['result']}")
    print(f"总体置信度: {uncertain_result['overall_confidence']:.2f}")
    print()
    
    # 因果推理示例
    print("=== 因果推理示例 ===")
    causal_result = cr.causal_reasoning("Sales increased after marketing campaign", depth=2)
    print(f"事件: {causal_result['event']}")
    print(f"结论: {causal_result['reasoning_result']['conclusion']}")
    print(f"置信度: {causal_result['reasoning_result']['confidence']:.2f}")
    print()
    
    # 反事实推理示例
    print("=== 反事实推理示例 ===")
    counterfactual_result = cr.counterfactual_reasoning(
        "The company invested in new technology and became more efficient"
    )
    print(f"原始场景: {counterfactual_result['original_scenario']}")
    print(f"替代场景: {counterfactual_result['alternative_scenario']}")
    print(f"结论: {counterfactual_result['reasoning_result']['conclusion']}")