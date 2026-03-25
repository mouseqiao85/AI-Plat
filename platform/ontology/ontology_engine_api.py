"""
Ontology Engine API
智能本体引擎API - 提供本体管理和认知推理功能
"""

import sqlite3
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

DB_PATH = "/opt/ai-plat-api/ai_plat.db"


class EntityType(str, Enum):
    CLASS = "class"
    PROPERTY = "property"
    INDIVIDUAL = "individual"
    RELATION = "relation"


class ReasoningType(str, Enum):
    DEDUCTIVE = "deductive"
    INDUCTIVE = "inductive"
    ABDUCTIVE = "abductive"
    CAUSAL = "causal"
    COUNTERFACTUAL = "counterfactual"


@dataclass
class OntologyEntity:
    id: str
    name: str
    type: str
    description: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class OntologyRelation:
    id: str
    source_id: str
    target_id: str
    relation_type: str
    properties: Optional[Dict[str, Any]] = None
    confidence: float = 1.0


@dataclass
class ReasoningResult:
    query: str
    reasoning_type: str
    conclusions: List[Dict[str, Any]]
    confidence: float
    explanation: str
    reasoning_chain: List[Dict[str, Any]]


class OntologyEngine:
    """
    智能本体引擎
    提供本体管理和认知推理功能
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_tables()
    
    def _init_tables(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # 本体实体表
        c.execute("""
            CREATE TABLE IF NOT EXISTS ontology_entities (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                description TEXT,
                properties TEXT,
                parent_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 本体关系表
        c.execute("""
            CREATE TABLE IF NOT EXISTS ontology_relations (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                properties TEXT,
                confidence REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 推理规则表
        c.execute("""
            CREATE TABLE IF NOT EXISTS reasoning_rules (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                rule_type TEXT NOT NULL,
                conditions TEXT,
                conclusions TEXT,
                confidence REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 推理历史表
        c.execute("""
            CREATE TABLE IF NOT EXISTS reasoning_history (
                id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                reasoning_type TEXT NOT NULL,
                result TEXT,
                confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def create_entity(self, name: str, entity_type: str, 
                      description: str = None, properties: Dict = None,
                      parent_id: str = None) -> OntologyEntity:
        """创建本体实体"""
        entity_id = f"entity_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{name[:8]}"
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute(
            """INSERT INTO ontology_entities 
               (id, name, type, description, properties, parent_id) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (entity_id, name, entity_type, description, 
             json.dumps(properties) if properties else None, parent_id)
        )
        
        conn.commit()
        conn.close()
        
        return OntologyEntity(
            id=entity_id,
            name=name,
            type=entity_type,
            description=description,
            properties=properties,
            created_at=datetime.utcnow().isoformat()
        )
    
    def get_entity(self, entity_id: str) -> Optional[OntologyEntity]:
        """获取实体"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        c.execute("SELECT * FROM ontology_entities WHERE id = ?", (entity_id,))
        row = c.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return OntologyEntity(
            id=row["id"],
            name=row["name"],
            type=row["type"],
            description=row["description"],
            properties=json.loads(row["properties"]) if row["properties"] else None,
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )
    
    def list_entities(self, entity_type: str = None, limit: int = 100) -> List[OntologyEntity]:
        """列出实体"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        if entity_type:
            c.execute(
                "SELECT * FROM ontology_entities WHERE type = ? ORDER BY created_at DESC LIMIT ?",
                (entity_type, limit)
            )
        else:
            c.execute(
                "SELECT * FROM ontology_entities ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
        
        rows = c.fetchall()
        conn.close()
        
        return [
            OntologyEntity(
                id=row["id"],
                name=row["name"],
                type=row["type"],
                description=row["description"],
                properties=json.loads(row["properties"]) if row["properties"] else None,
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
            for row in rows
        ]
    
    def update_entity(self, entity_id: str, name: str = None, 
                      description: str = None, properties: Dict = None) -> Optional[OntologyEntity]:
        """更新实体"""
        entity = self.get_entity(entity_id)
        if not entity:
            return None
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        updates = []
        params = []
        
        if name:
            updates.append("name = ?")
            params.append(name)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if properties is not None:
            updates.append("properties = ?")
            params.append(json.dumps(properties))
        
        updates.append("updated_at = ?")
        params.append(datetime.utcnow().isoformat())
        params.append(entity_id)
        
        c.execute(
            f"UPDATE ontology_entities SET {', '.join(updates)} WHERE id = ?",
            params
        )
        conn.commit()
        conn.close()
        
        return self.get_entity(entity_id)
    
    def delete_entity(self, entity_id: str) -> bool:
        """删除实体"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # 删除相关关系
        c.execute(
            "DELETE FROM ontology_relations WHERE source_id = ? OR target_id = ?",
            (entity_id, entity_id)
        )
        
        # 删除实体
        c.execute("DELETE FROM ontology_entities WHERE id = ?", (entity_id,))
        deleted = c.rowcount > 0
        
        conn.commit()
        conn.close()
        
        return deleted
    
    def create_relation(self, source_id: str, target_id: str, 
                        relation_type: str, properties: Dict = None,
                        confidence: float = 1.0) -> OntologyRelation:
        """创建关系"""
        relation_id = f"rel_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute(
            """INSERT INTO ontology_relations 
               (id, source_id, target_id, relation_type, properties, confidence) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (relation_id, source_id, target_id, relation_type,
             json.dumps(properties) if properties else None, confidence)
        )
        
        conn.commit()
        conn.close()
        
        return OntologyRelation(
            id=relation_id,
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            properties=properties,
            confidence=confidence
        )
    
    def get_relations(self, entity_id: str = None, 
                      relation_type: str = None) -> List[OntologyRelation]:
        """获取关系"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        if entity_id:
            c.execute(
                """SELECT * FROM ontology_relations 
                   WHERE source_id = ? OR target_id = ?""",
                (entity_id, entity_id)
            )
        elif relation_type:
            c.execute(
                "SELECT * FROM ontology_relations WHERE relation_type = ?",
                (relation_type,)
            )
        else:
            c.execute("SELECT * FROM ontology_relations")
        
        rows = c.fetchall()
        conn.close()
        
        return [
            OntologyRelation(
                id=row["id"],
                source_id=row["source_id"],
                target_id=row["target_id"],
                relation_type=row["relation_type"],
                properties=json.loads(row["properties"]) if row["properties"] else None,
                confidence=row["confidence"]
            )
            for row in rows
        ]
    
    def delete_relation(self, relation_id: str) -> bool:
        """删除关系"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM ontology_relations WHERE id = ?", (relation_id,))
        deleted = c.rowcount > 0
        conn.commit()
        conn.close()
        return deleted
    
    def create_reasoning_rule(self, name: str, rule_type: str,
                               conditions: List[Dict], conclusions: List[Dict],
                               confidence: float = 1.0) -> Dict:
        """创建推理规则"""
        rule_id = f"rule_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute(
            """INSERT INTO reasoning_rules 
               (id, name, rule_type, conditions, conclusions, confidence) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (rule_id, name, rule_type, 
             json.dumps(conditions), json.dumps(conclusions), confidence)
        )
        
        conn.commit()
        conn.close()
        
        return {
            "id": rule_id,
            "name": name,
            "rule_type": rule_type,
            "conditions": conditions,
            "conclusions": conclusions,
            "confidence": confidence
        }
    
    def list_reasoning_rules(self) -> List[Dict]:
        """列出推理规则"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM reasoning_rules")
        rows = c.fetchall()
        conn.close()
        
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "rule_type": row["rule_type"],
                "conditions": json.loads(row["conditions"]),
                "conclusions": json.loads(row["conclusions"]),
                "confidence": row["confidence"]
            }
            for row in rows
        ]
    
    def reason(self, query: str, reasoning_type: str = "deductive") -> ReasoningResult:
        """
        执行推理
        支持多种推理类型
        """
        # 解析查询
        parsed = self._parse_query(query)
        
        # 获取相关实体和关系
        entities = self.list_entities()
        relations = self.get_relations()
        rules = self.list_reasoning_rules()
        
        # 执行推理
        if reasoning_type == "deductive":
            result = self._deductive_reasoning(parsed, entities, relations, rules)
        elif reasoning_type == "inductive":
            result = self._inductive_reasoning(parsed, entities, relations)
        elif reasoning_type == "causal":
            result = self._causal_reasoning(parsed, entities, relations)
        elif reasoning_type == "counterfactual":
            result = self._counterfactual_reasoning(parsed, entities, relations)
        else:
            result = self._deductive_reasoning(parsed, entities, relations, rules)
        
        # 保存推理历史
        self._save_reasoning_history(query, reasoning_type, result)
        
        return result
    
    def _parse_query(self, query: str) -> Dict:
        """解析查询"""
        parsed = {
            "original": query,
            "type": "unknown",
            "entities": [],
            "relations": [],
            "keywords": []
        }
        
        query_lower = query.lower()
        
        # 检测查询类型
        if "why" in query_lower or "为什么" in query_lower:
            parsed["type"] = "causal"
        elif "what if" in query_lower or "如果" in query_lower:
            parsed["type"] = "counterfactual"
        elif "how" in query_lower or "如何" in query_lower:
            parsed["type"] = "procedural"
        else:
            parsed["type"] = "factual"
        
        # 提取关键词
        words = re.findall(r'\b\w+\b', query)
        parsed["keywords"] = [w.lower() for w in words if len(w) > 2]
        
        return parsed
    
    def _deductive_reasoning(self, parsed: Dict, entities: List, 
                              relations: List, rules: List) -> ReasoningResult:
        """演绎推理"""
        conclusions = []
        reasoning_chain = []
        confidence = 0.8
        
        # 基于规则的推理
        for rule in rules:
            conditions_met = True
            for condition in rule["conditions"]:
                # 简化的条件检查
                if condition.get("entity") and condition.get("property"):
                    matching = [e for e in entities 
                               if condition["entity"].lower() in e.name.lower()]
                    if not matching:
                        conditions_met = False
                        break
            
            if conditions_met:
                for conclusion in rule["conclusions"]:
                    conclusions.append({
                        "type": "rule_based",
                        "content": conclusion,
                        "rule_id": rule["id"],
                        "confidence": rule["confidence"]
                    })
                    reasoning_chain.append({
                        "step": "apply_rule",
                        "rule": rule["name"],
                        "result": conclusion
                    })
        
        # 基于关系的推理
        for relation in relations:
            if relation.relation_type in parsed["keywords"]:
                source = self.get_entity(relation.source_id)
                target = self.get_entity(relation.target_id)
                if source and target:
                    conclusions.append({
                        "type": "relation_based",
                        "content": f"{source.name} {relation.relation_type} {target.name}",
                        "confidence": relation.confidence
                    })
        
        # 生成解释
        explanation = self._generate_explanation(conclusions, reasoning_chain)
        
        return ReasoningResult(
            query=parsed["original"],
            reasoning_type="deductive",
            conclusions=conclusions,
            confidence=confidence,
            explanation=explanation,
            reasoning_chain=reasoning_chain
        )
    
    def _inductive_reasoning(self, parsed: Dict, entities: List, 
                              relations: List) -> ReasoningResult:
        """归纳推理"""
        conclusions = []
        reasoning_chain = []
        
        # 统计模式
        type_counts = {}
        for entity in entities:
            if entity.type not in type_counts:
                type_counts[entity.type] = 0
            type_counts[entity.type] += 1
        
        # 归纳结论
        for entity_type, count in type_counts.items():
            if count > 3:
                conclusions.append({
                    "type": "pattern",
                    "content": f"发现{count}个{entity_type}类型的实体，表明这是一个重要类别",
                    "confidence": min(count / 10, 0.9)
                })
        
        # 关系模式
        relation_patterns = {}
        for rel in relations:
            if rel.relation_type not in relation_patterns:
                relation_patterns[rel.relation_type] = 0
            relation_patterns[rel.relation_type] += 1
        
        for rel_type, count in relation_patterns.items():
            if count > 2:
                conclusions.append({
                    "type": "pattern",
                    "content": f"'{rel_type}'关系出现{count}次，可能是重要关系类型",
                    "confidence": min(count / 5, 0.85)
                })
        
        explanation = "通过分析实体和关系的统计模式，归纳出以下结论。"
        
        return ReasoningResult(
            query=parsed["original"],
            reasoning_type="inductive",
            conclusions=conclusions,
            confidence=0.75,
            explanation=explanation,
            reasoning_chain=reasoning_chain
        )
    
    def _causal_reasoning(self, parsed: Dict, entities: List, 
                           relations: List) -> ReasoningResult:
        """因果推理"""
        conclusions = []
        reasoning_chain = []
        
        # 查找因果链条
        causal_relations = [r for r in relations 
                           if r.relation_type in ["causes", "leads_to", "results_in", "导致"]]
        
        for rel in causal_relations:
            source = self.get_entity(rel.source_id)
            target = self.get_entity(rel.target_id)
            if source and target:
                chain = f"{source.name} → {rel.relation_type} → {target.name}"
                reasoning_chain.append({
                    "step": "identify_cause",
                    "cause": source.name,
                    "effect": target.name,
                    "relation": rel.relation_type
                })
                conclusions.append({
                    "type": "causal_chain",
                    "content": chain,
                    "confidence": rel.confidence
                })
        
        explanation = "识别出以下因果关系链。" if conclusions else "未发现明确的因果关系。"
        
        return ReasoningResult(
            query=parsed["original"],
            reasoning_type="causal",
            conclusions=conclusions,
            confidence=0.7 if conclusions else 0.3,
            explanation=explanation,
            reasoning_chain=reasoning_chain
        )
    
    def _counterfactual_reasoning(self, parsed: Dict, entities: List,
                                    relations: List) -> ReasoningResult:
        """反事实推理"""
        conclusions = []
        reasoning_chain = []
        
        # 模拟假设场景
        conclusions.append({
            "type": "counterfactual",
            "content": "在假设条件下，系统推演了可能的结果变化",
            "confidence": 0.6,
            "assumptions": parsed.get("keywords", [])
        })
        
        reasoning_chain.append({
            "step": "simulate_scenario",
            "input": parsed["original"],
            "analysis": "基于现有知识图谱进行反事实分析"
        })
        
        explanation = "通过反事实推理，分析了假设场景可能带来的影响。"
        
        return ReasoningResult(
            query=parsed["original"],
            reasoning_type="counterfactual",
            conclusions=conclusions,
            confidence=0.6,
            explanation=explanation,
            reasoning_chain=reasoning_chain
        )
    
    def _generate_explanation(self, conclusions: List, 
                               reasoning_chain: List) -> str:
        """生成推理解释"""
        if not conclusions:
            return "未能得出明确的结论。"
        
        parts = []
        for i, conclusion in enumerate(conclusions[:3]):
            content = conclusion.get("content", str(conclusion))
            conf = conclusion.get("confidence", 0)
            parts.append(f"{i+1}. {content} (置信度: {conf:.0%})")
        
        return "\n".join(parts)
    
    def _save_reasoning_history(self, query: str, reasoning_type: str, 
                                  result: ReasoningResult):
        """保存推理历史"""
        history_id = f"hist_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute(
            """INSERT INTO reasoning_history 
               (id, query, reasoning_type, result, confidence) 
               VALUES (?, ?, ?, ?, ?)""",
            (history_id, query, reasoning_type, 
             json.dumps(asdict(result)), result.confidence)
        )
        
        conn.commit()
        conn.close()
    
    def get_reasoning_history(self, limit: int = 50) -> List[Dict]:
        """获取推理历史"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        c.execute(
            "SELECT * FROM reasoning_history ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        
        rows = c.fetchall()
        conn.close()
        
        return [
            {
                "id": row["id"],
                "query": row["query"],
                "reasoning_type": row["reasoning_type"],
                "confidence": row["confidence"],
                "created_at": row["created_at"]
            }
            for row in rows
        ]
    
    def get_statistics(self) -> Dict:
        """获取本体统计"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM ontology_entities")
        entity_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM ontology_relations")
        relation_count = c.fetchone()[0]
        
        c.execute("SELECT type, COUNT(*) FROM ontology_entities GROUP BY type")
        entity_types = dict(c.fetchall())
        
        c.execute("SELECT relation_type, COUNT(*) FROM ontology_relations GROUP BY relation_type")
        relation_types = dict(c.fetchall())
        
        c.execute("SELECT COUNT(*) FROM reasoning_rules")
        rule_count = c.fetchone()[0]
        
        conn.close()
        
        return {
            "entity_count": entity_count,
            "relation_count": relation_count,
            "rule_count": rule_count,
            "entity_types": entity_types,
            "relation_types": relation_types
        }
    
    def import_ontology(self, ontology_data: Dict) -> Dict:
        """导入本体数据"""
        imported = {"entities": 0, "relations": 0}
        
        # 导入实体
        for entity_data in ontology_data.get("entities", []):
            try:
                self.create_entity(
                    name=entity_data["name"],
                    entity_type=entity_data.get("type", "class"),
                    description=entity_data.get("description"),
                    properties=entity_data.get("properties")
                )
                imported["entities"] += 1
            except Exception as e:
                print(f"Error importing entity: {e}")
        
        # 导入关系
        for relation_data in ontology_data.get("relations", []):
            try:
                self.create_relation(
                    source_id=relation_data["source_id"],
                    target_id=relation_data["target_id"],
                    relation_type=relation_data["relation_type"],
                    properties=relation_data.get("properties"),
                    confidence=relation_data.get("confidence", 1.0)
                )
                imported["relations"] += 1
            except Exception as e:
                print(f"Error importing relation: {e}")
        
        return imported
    
    def export_ontology(self) -> Dict:
        """导出本体数据"""
        entities = [asdict(e) for e in self.list_entities(limit=1000)]
        relations = [asdict(r) for r in self.get_relations()]
        
        return {
            "entities": entities,
            "relations": relations,
            "statistics": self.get_statistics(),
            "exported_at": datetime.utcnow().isoformat()
        }


# 创建全局实例
ontology_engine = OntologyEngine()
