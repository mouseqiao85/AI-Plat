"""
动态本体构建器
支持运行时动态调整本体结构，实现自适应建模和增量学习
"""

from .ontology_manager import OntologyManager
from .inference_engine import InferenceEngine
from rdflib import Graph, URIRef, RDF, RDFS, OWL
from typing import Dict, List, Tuple, Optional, Any
import logging
from collections import defaultdict
import json
import hashlib

logger = logging.getLogger(__name__)


class DynamicOntologyBuilder:
    """
    动态本体构建器
    支持：
    1. 自适应建模：根据数据模式自动调整本体结构
    2. 增量学习：支持本体结构的增量式更新
    3. 冲突解决：智能解决本体定义冲突
    4. 版本管理：完整的本体版本控制和回滚
    """
    
    def __init__(self, ontology_manager: OntologyManager):
        """
        初始化动态本体构建器
        
        Args:
            ontology_manager: 本体管理器实例
        """
        self.ontology_manager = ontology_manager
        self.graph = ontology_manager.graph
        self.base_ns = ontology_manager.base_ns
        
        # 模式检测缓存
        self.pattern_cache = {}
        self.change_history = []
        self.conflict_resolution_rules = self._initialize_conflict_rules()
        
        # 版本管理
        self.versions = {}
        self.current_version = "1.0.0"
        
    def _initialize_conflict_rules(self) -> Dict[str, Any]:
        """
        初始化冲突解决规则
        """
        return {
            'duplicate_entity': self._resolve_duplicate_entity,
            'inconsistent_property': self._resolve_inconsistent_property,
            'circular_hierarchy': self._resolve_circular_hierarchy,
            'semantic_conflict': self._resolve_semantic_conflict
        }
    
    def adapt_to_data_pattern(self, data_records: List[Dict], domain_name: str = "default") -> Dict[str, Any]:
        """
        自适应建模：根据数据模式自动调整本体结构
        
        Args:
            data_records: 数据记录列表
            domain_name: 领域名称
            
        Returns:
            调整结果统计
        """
        logger.info(f"Adapting ontology to data patterns in domain: {domain_name}")
        
        if not data_records:
            return {"status": "skipped", "reason": "no_data"}
        
        # 分析数据模式
        patterns = self._analyze_data_patterns(data_records)
        
        # 检测现有本体结构
        existing_ontology = self._analyze_existing_ontology(domain_name)
        
        # 计算差异并调整
        adjustments = self._calculate_adjustments(patterns, existing_ontology)
        
        # 应用调整
        results = self._apply_ontology_adjustments(adjustments)
        
        # 保存版本快照
        self._save_version_snapshot(f"after_adaptation_{domain_name}")
        
        return {
            "status": "completed",
            "domain": domain_name,
            "patterns_detected": len(patterns),
            "adjustments_made": results["adjustments_count"],
            "new_entities": results["new_entities"],
            "modified_relations": results["modified_relations"]
        }
    
    def _analyze_data_patterns(self, data_records: List[Dict]) -> Dict[str, Any]:
        """
        分析数据模式
        
        Args:
            data_records: 数据记录
            
        Returns:
            检测到的模式
        """
        patterns = {
            "entities": defaultdict(set),
            "properties": defaultdict(list),
            "relations": defaultdict(int),
            "value_patterns": defaultdict(dict)
        }
        
        for record in data_records:
            # 检测实体类型
            entity_types = self._detect_entity_types(record)
            for entity_type in entity_types:
                patterns["entities"][entity_type].add(record.get("id", str(hash(str(record)))))
            
            # 检测属性
            for key, value in record.items():
                if key == "id":
                    continue
                    
                prop_type = self._detect_property_type(key, value)
                patterns["properties"][prop_type].append(key)
                
                # 记录属性值模式
                if prop_type not in patterns["value_patterns"][key]:
                    patterns["value_patterns"][key] = {"type": prop_type, "examples": []}
                patterns["value_patterns"][key]["examples"].append(value)
            
            # 检测关系（如果有关系字段）
            if "relations" in record:
                for relation in record["relations"]:
                    rel_key = f"{relation['source']}_{relation['type']}_{relation['target']}"
                    patterns["relations"][rel_key] += 1
        
        # 清理和统计
        for prop_type in list(patterns["properties"].keys()):
            patterns["properties"][prop_type] = list(set(patterns["properties"][prop_type]))
        
        return patterns
    
    def _detect_entity_types(self, record: Dict) -> List[str]:
        """
        检测实体类型
        
        Args:
            record: 数据记录
            
        Returns:
            实体类型列表
        """
        entity_types = []
        
        # 基于字段名启发式检测
        type_hints = {
            "person": ["person", "user", "customer", "employee"],
            "product": ["product", "item", "good", "service"],
            "location": ["location", "place", "address", "city"],
            "organization": ["organization", "company", "business", "department"],
            "event": ["event", "meeting", "appointment", "transaction"]
        }
        
        record_str = json.dumps(record).lower()
        for entity_type, hints in type_hints.items():
            for hint in hints:
                if hint in record_str:
                    entity_types.append(entity_type)
                    break
        
        # 如果没有检测到类型，使用默认值
        if not entity_types:
            entity_types.append("Thing")
        
        return entity_types
    
    def _detect_property_type(self, key: str, value: Any) -> str:
        """
        检测属性类型
        
        Args:
            key: 属性名
            value: 属性值
            
        Returns:
            属性类型 (datatype_property, object_property, relation)
        """
        # 基于值类型检测
        if isinstance(value, (int, float)):
            return "datatype_property"
        elif isinstance(value, str):
            # 检查是否为ID引用
            if len(value) > 10 and value.startswith("ID_"):
                return "object_property"
            # 检查是否为URI
            if value.startswith("http://") or value.startswith("https://"):
                return "object_property"
            return "datatype_property"
        elif isinstance(value, dict):
            return "object_property"
        elif isinstance(value, list):
            if value and isinstance(value[0], dict):
                return "object_property"
            return "datatype_property"
        else:
            return "datatype_property"
    
    def _analyze_existing_ontology(self, domain_name: str) -> Dict[str, Any]:
        """
        分析现有本体结构
        
        Args:
            domain_name: 领域名称
            
        Returns:
            现有本体结构分析
        """
        existing = {
            "classes": set(),
            "properties": set(),
            "relations": defaultdict(set),
            "domain_coverage": 0.0
        }
        
        # 查询现有类
        classes_query = """
        SELECT ?class WHERE {
            ?class rdf:type owl:Class .
        }
        """
        for row in self.graph.query(classes_query):
            class_name = str(row[0]).split("#")[-1]
            existing["classes"].add(class_name)
        
        # 查询现有属性
        properties_query = """
        SELECT ?prop WHERE {
            ?prop rdf:type ?type .
            FILTER (?type IN (owl:ObjectProperty, owl:DatatypeProperty))
        }
        """
        for row in self.graph.query(properties_query):
            prop_name = str(row[0]).split("#")[-1]
            existing["properties"].add(prop_name)
        
        # 查询现有关系
        relations_query = """
        SELECT ?subject ?predicate ?object WHERE {
            ?subject ?predicate ?object .
            FILTER (isIRI(?subject) && isIRI(?object))
        }
        """
        for row in self.graph.query(relations_query):
            subj = str(row[0]).split("#")[-1]
            pred = str(row[1]).split("#")[-1]
            obj = str(row[2]).split("#")[-1]
            existing["relations"][pred].add((subj, obj))
        
        return existing
    
    def _calculate_adjustments(self, patterns: Dict, existing: Dict) -> Dict[str, Any]:
        """
        计算本体调整需求
        
        Args:
            patterns: 数据模式
            existing: 现有本体
            
        Returns:
            调整计划
        """
        adjustments = {
            "new_classes": [],
            "new_properties": [],
            "modified_classes": [],
            "modified_properties": [],
            "new_relations": []
        }
        
        # 检测新类
        for entity_type in patterns["entities"]:
            if entity_type not in existing["classes"]:
                adjustments["new_classes"].append({
                    "name": entity_type,
                    "description": f"Auto-detected entity type from data patterns",
                    "type": "Class",
                    "confidence": 0.8
                })
        
        # 检测新属性
        for prop_type, props in patterns["properties"].items():
            for prop in props:
                if prop not in existing["properties"]:
                    adjustments["new_properties"].append({
                        "name": prop,
                        "description": f"Data property for {prop}",
                        "type": prop_type,
                        "examples": patterns["value_patterns"].get(prop, {}).get("examples", [])[:3]
                    })
        
        # 检测新关系（简化版）
        for relation_pattern, count in patterns["relations"].items():
            if count > 2:  # 出现多次的关系才考虑添加
                source, rel_type, target = relation_pattern.split("_")
                if rel_type not in existing["properties"]:
                    adjustments["new_relations"].append({
                        "source": source,
                        "relation": rel_type,
                        "target": target,
                        "frequency": count
                    })
        
        return adjustments
    
    def _apply_ontology_adjustments(self, adjustments: Dict[str, Any]) -> Dict[str, int]:
        """
        应用本体调整
        
        Args:
            adjustments: 调整计划
            
        Returns:
            应用结果统计
        """
        results = {
            "adjustments_count": 0,
            "new_entities": 0,
            "modified_relations": 0,
            "conflicts_resolved": 0
        }
        
        # 添加新类
        for new_class in adjustments["new_classes"]:
            try:
                self.ontology_manager.create_entity(
                    entity_name=new_class["name"],
                    entity_type=new_class["type"],
                    description=new_class["description"]
                )
                results["new_entities"] += 1
                results["adjustments_count"] += 1
            except Exception as e:
                logger.warning(f"Failed to add class {new_class['name']}: {str(e)}")
        
        # 添加新属性
        for new_prop in adjustments["new_properties"]:
            try:
                self.ontology_manager.create_entity(
                    entity_name=new_prop["name"],
                    entity_type=new_prop["type"],
                    description=new_prop["description"]
                )
                results["new_entities"] += 1
                results["adjustments_count"] += 1
            except Exception as e:
                logger.warning(f"Failed to add property {new_prop['name']}: {str(e)}")
        
        # 添加新关系
        for new_rel in adjustments["new_relations"]:
            try:
                # 首先确保源和目标类存在
                self._ensure_class_exists(new_rel["source"])
                self._ensure_class_exists(new_rel["target"])
                
                # 创建关系
                self.ontology_manager.create_relationship(
                    subject=new_rel["source"],
                    predicate=new_rel["relation"],
                    obj=new_rel["target"]
                )
                results["modified_relations"] += 1
                results["adjustments_count"] += 1
            except Exception as e:
                logger.warning(f"Failed to add relation {new_rel}: {str(e)}")
        
        return results
    
    def _ensure_class_exists(self, class_name: str):
        """
        确保类存在，如果不存在则创建
        
        Args:
            class_name: 类名
        """
        # 检查类是否已存在
        existing_classes = self.ontology_manager.get_entities_by_type("Class")
        existing_class_names = [str(c).split("#")[-1] for c in existing_classes]
        
        if class_name not in existing_class_names:
            self.ontology_manager.create_entity(
                entity_name=class_name,
                entity_type="Class",
                description=f"Auto-created class for relation modeling"
            )
    
    def incremental_update(self, new_data: List[Dict], change_summary: Dict = None) -> Dict[str, Any]:
        """
        增量学习：支持本体结构的增量式更新
        
        Args:
            new_data: 新数据
            change_summary: 变更摘要
            
        Returns:
            更新结果
        """
        logger.info("Performing incremental ontology update")
        
        # 记录变更前状态
        before_hash = self._calculate_ontology_hash()
        
        # 应用增量更新
        adaptation_result = self.adapt_to_data_pattern(new_data, "incremental_update")
        
        # 记录变更后状态
        after_hash = self._calculate_ontology_hash()
        
        # 检测冲突
        conflicts = self._detect_conflicts()
        
        # 解决冲突
        if conflicts:
            resolved = self._resolve_conflicts(conflicts)
            adaptation_result["conflicts_resolved"] = resolved
        
        # 记录变更历史
        change_record = {
            "timestamp": self._get_timestamp(),
            "before_hash": before_hash,
            "after_hash": after_hash,
            "data_count": len(new_data),
            "adaptation_result": adaptation_result,
            "change_summary": change_summary
        }
        self.change_history.append(change_record)
        
        # 保存版本
        self._save_version_snapshot(f"incremental_update_{len(self.change_history)}")
        
        return {
            "status": "completed",
            "update_id": len(self.change_history),
            "ontology_changed": before_hash != after_hash,
            "conflicts_detected": len(conflicts) if conflicts else 0,
            "change_record": change_record
        }
    
    def _calculate_ontology_hash(self) -> str:
        """
        计算本体哈希值，用于检测变更
        
        Returns:
            哈希值
        """
        ontology_json = self.ontology_manager.export_to_json()
        ontology_str = json.dumps(ontology_json, sort_keys=True)
        return hashlib.md5(ontology_str.encode()).hexdigest()
    
    def _detect_conflicts(self) -> List[Dict]:
        """
        检测本体冲突
        
        Returns:
            冲突列表
        """
        conflicts = []
        
        # 使用推理引擎进行一致性检查
        inference_engine = InferenceEngine(self.ontology_manager)
        consistency = inference_engine.consistency_check()
        
        if not consistency['consistent']:
            for issue in consistency['issues_found']:
                conflicts.append({
                    "type": f"consistency_{issue['type']}",
                    "severity": "high",
                    "details": issue
                })
        
        # 检查重复实体
        duplicate_check = self._check_duplicate_entities()
        if duplicate_check:
            conflicts.extend(duplicate_check)
        
        # 检查循环层次结构
        circular_check = self._check_circular_hierarchy()
        if circular_check:
            conflicts.extend(circular_check)
        
        return conflicts
    
    def _check_duplicate_entities(self) -> List[Dict]:
        """
        检查重复实体
        
        Returns:
            重复实体冲突
        """
        conflicts = []
        
        # 检查同名不同URI的实体
        entity_names = defaultdict(list)
        
        # 查询所有实体
        all_entities_query = """
        SELECT ?entity WHERE {
            ?entity ?p ?o .
            FILTER (isIRI(?entity))
        }
        """
        
        for row in self.graph.query(all_entities_query):
            entity_uri = str(row[0])
            entity_name = entity_uri.split("#")[-1]
            entity_names[entity_name].append(entity_uri)
        
        # 检测重复
        for entity_name, uris in entity_names.items():
            if len(uris) > 1:
                conflicts.append({
                    "type": "duplicate_entity",
                    "severity": "medium",
                    "details": {
                        "entity_name": entity_name,
                        "uris": uris,
                        "count": len(uris)
                    }
                })
        
        return conflicts
    
    def _check_circular_hierarchy(self) -> List[Dict]:
        """
        检查循环层次结构
        
        Returns:
            循环结构冲突
        """
        conflicts = []
        
        # 检查循环子类关系
        circular_query = """
        SELECT ?class1 ?class2 WHERE {
            ?class1 rdfs:subClassOf ?class2 .
            ?class2 rdfs:subClassOf ?class1 .
            FILTER (?class1 != ?class2)
        }
        """
        
        for row in self.graph.query(circular_query):
            class1 = str(row[0])
            class2 = str(row[1])
            conflicts.append({
                "type": "circular_hierarchy",
                "severity": "high",
                "details": {
                    "class1": class1,
                    "class2": class2,
                    "relation": "mutual_subClassOf"
                }
            })
        
        return conflicts
    
    def _resolve_conflicts(self, conflicts: List[Dict]) -> int:
        """
        解决检测到的冲突
        
        Args:
            conflicts: 冲突列表
            
        Returns:
            解决的冲突数量
        """
        resolved_count = 0
        
        for conflict in conflicts:
            conflict_type = conflict["type"]
            resolver = self.conflict_resolution_rules.get(conflict_type)
            
            if resolver:
                try:
                    resolved = resolver(conflict)
                    if resolved:
                        resolved_count += 1
                        logger.info(f"Resolved conflict: {conflict_type}")
                except Exception as e:
                    logger.warning(f"Failed to resolve conflict {conflict_type}: {str(e)}")
        
        return resolved_count
    
    def _resolve_duplicate_entity(self, conflict: Dict) -> bool:
        """
        解决重复实体冲突
        
        Args:
            conflict: 冲突详情
            
        Returns:
            是否成功解决
        """
        # 简单的解决策略：保留第一个URI，将其他URI重定向
        entity_name = conflict["details"]["entity_name"]
        uris = conflict["details"]["uris"]
        
        if len(uris) <= 1:
            return True
        
        # 选择主URI（第一个）
        main_uri = URIRef(uris[0])
        other_uris = [URIRef(uri) for uri in uris[1:]]
        
        # 重定向其他URI到主URI
        for other_uri in other_uris:
            # 复制所有三元组
            triples_to_copy = list(self.graph.triples((other_uri, None, None)))
            for triple in triples_to_copy:
                _, pred, obj = triple
                self.graph.add((main_uri, pred, obj))
            
            # 添加owl:sameAs关系
            self.graph.add((other_uri, OWL.sameAs, main_uri))
        
        return True
    
    def _resolve_inconsistent_property(self, conflict: Dict) -> bool:
        """
        解决不一致属性冲突
        
        Args:
            conflict: 冲突详情
            
        Returns:
            是否成功解决
        """
        # 默认实现：记录冲突但不自动解决
        logger.warning(f"Inconsistent property conflict detected: {conflict}")
        return False
    
    def _resolve_circular_hierarchy(self, conflict: Dict) -> bool:
        """
        解决循环层次结构冲突
        
        Args:
            conflict: 冲突详情
            
        Returns:
            是否成功解决
        """
        details = conflict["details"]
        class1 = URIRef(details["class1"])
        class2 = URIRef(details["class2"])
        
        # 移除其中一个子类关系
        # 这里使用简单的启发式：移除后添加的关系
        # 在实际应用中可能需要更复杂的逻辑
        try:
            self.graph.remove((class1, RDFS.subClassOf, class2))
            logger.info(f"Removed circular subclass relation: {details['class1']} -> {details['class2']}")
            return True
        except Exception as e:
            logger.warning(f"Failed to remove circular relation: {str(e)}")
            return False
    
    def _resolve_semantic_conflict(self, conflict: Dict) -> bool:
        """
        解决语义冲突
        
        Args:
            conflict: 冲突详情
            
        Returns:
            是否成功解决
        """
        # 默认实现：需要人工干预
        logger.warning(f"Semantic conflict detected, requires manual review: {conflict}")
        return False
    
    def _save_version_snapshot(self, version_name: str):
        """
        保存版本快照
        
        Args:
            version_name: 版本名称
        """
        snapshot = {
            "version_name": version_name,
            "timestamp": self._get_timestamp(),
            "ontology_hash": self._calculate_ontology_hash(),
            "entity_count": len(self.ontology_manager.get_entities_by_type("Class")),
            "property_count": len(self.ontology_manager.get_entities_by_type("ObjectProperty")) + 
                           len(self.ontology_manager.get_entities_by_type("DatatypeProperty"))
        }
        
        self.versions[version_name] = snapshot
        logger.info(f"Saved version snapshot: {version_name}")
    
    def _get_timestamp(self) -> str:
        """
        获取当前时间戳
        
        Returns:
            时间戳字符串
        """
        from datetime import datetime
        return datetime.now().isoformat()
    
    def rollback_to_version(self, version_name: str) -> Dict[str, Any]:
        """
        回滚到指定版本
        
        Args:
            version_name: 版本名称
            
        Returns:
            回滚结果
        """
        if version_name not in self.versions:
            return {"status": "failed", "reason": f"Version {version_name} not found"}
        
        logger.info(f"Rolling back to version: {version_name}")
        
        # 当前实现：记录回滚请求
        # 在实际应用中，这里需要实现完整的版本恢复逻辑
        self.change_history.append({
            "timestamp": self._get_timestamp(),
            "action": "rollback_request",
            "target_version": version_name,
            "current_version": self.current_version
        })
        
        return {
            "status": "requested",
            "message": "Rollback requested (full implementation needed)",
            "target_version": version_name,
            "current_version": self.current_version
        }
    
    def get_version_history(self) -> List[Dict]:
        """
        获取版本历史
        
        Returns:
            版本历史列表
        """
        return [
            {
                "version": name,
                "timestamp": snapshot["timestamp"],
                "ontology_hash": snapshot["ontology_hash"][:8],  # 简短的哈希
                "entity_count": snapshot["entity_count"],
                "property_count": snapshot["property_count"]
            }
            for name, snapshot in self.versions.items()
        ]
    
    def get_change_summary(self, limit: int = 10) -> List[Dict]:
        """
        获取变更摘要
        
        Args:
            limit: 返回的最大记录数
            
        Returns:
            变更摘要列表
        """
        return self.change_history[-limit:] if self.change_history else []


# 示例使用
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # 创建本体管理器
    om = OntologyManager()
    
    # 创建动态本体构建器
    dob = DynamicOntologyBuilder(om)
    
    # 示例数据
    sample_data = [
        {
            "id": "person_001",
            "name": "张三",
            "age": 30,
            "department": "sales",
            "location": "beijing",
            "relations": [
                {"source": "person_001", "type": "works_in", "target": "dept_001"},
                {"source": "person_001", "type": "located_in", "target": "loc_001"}
            ]
        },
        {
            "id": "product_001", 
            "name": "Laptop",
            "price": 999.99,
            "category": "electronics",
            "relations": [
                {"source": "product_001", "type": "belongs_to", "target": "cat_001"}
            ]
        }
    ]
    
    # 自适应建模
    result = dob.adapt_to_data_pattern(sample_data, "test_domain")
    print("Adaptation Result:", json.dumps(result, indent=2, ensure_ascii=False))
    
    # 获取版本历史
    version_history = dob.get_version_history()
    print("\nVersion History:")
    for version in version_history:
        print(f"  {version['version']}: {version['entity_count']} entities")
    
    # 获取变更摘要
    changes = dob.get_change_summary()
    print(f"\nRecent Changes: {len(changes)} records")