"""
本体管理器
负责本体的创建、编辑、存储和查询
"""

from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL
import json
import os
from typing import Dict, List, Optional, Union
from pathlib import Path


class OntologyManager:
    """
    本体管理器类，提供本体创建、编辑、存储和查询功能
    """
    
    def __init__(self, storage_path: str = "./ontology/definitions"):
        """
        初始化本体管理器
        
        Args:
            storage_path: 本体存储路径
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 创建RDF图
        self.graph = Graph()
        
        # 定义命名空间
        self.base_ns = Namespace("http://ai-plat.org/ontology#")
        self.owl_ns = Namespace("http://www.w3.org/2002/07/owl#")
        
        # 注册命名空间
        self.graph.bind("base", self.base_ns)
        self.graph.bind("owl", self.owl_ns)
        self.graph.bind("rdf", RDF)
        self.graph.bind("rdfs", RDFS)
        
        # 加载现有的本体文件
        self._load_existing_ontologies()
    
    def _load_existing_ontologies(self):
        """
        加载现有的本体文件
        """
        for ontology_file in self.storage_path.glob("*.ttl"):
            try:
                self.graph.parse(ontology_file, format="turtle")
                print(f"Loaded ontology from {ontology_file}")
            except Exception as e:
                print(f"Error loading ontology {ontology_file}: {str(e)}")
    
    def create_entity(self, entity_name: str, entity_type: str = "Class", 
                     description: str = "", properties: Dict = None):
        """
        创建实体
        
        Args:
            entity_name: 实体名称
            entity_type: 实体类型 (Class, ObjectProperty, DatatypeProperty等)
            description: 描述
            properties: 属性字典
        """
        entity_uri = self.base_ns[entity_name]
        
        if entity_type == "Class":
            self.graph.add((entity_uri, RDF.type, OWL.Class))
        elif entity_type == "ObjectProperty":
            self.graph.add((entity_uri, RDF.type, OWL.ObjectProperty))
        elif entity_type == "DatatypeProperty":
            self.graph.add((entity_uri, RDF.type, OWL.DatatypeProperty))
        else:
            self.graph.add((entity_uri, RDF.type, OWL[entity_type]))
        
        if description:
            self.graph.add((entity_uri, RDFS.comment, Literal(description)))
            
        if properties:
            for prop_name, prop_value in properties.items():
                prop_uri = self.base_ns[prop_name]
                self.graph.add((entity_uri, prop_uri, Literal(prop_value)))
                
        print(f"Created entity: {entity_name} ({entity_type})")
    
    def create_relationship(self, subject: str, predicate: str, obj: str):
        """
        创建关系
        
        Args:
            subject: 主体实体
            predicate: 关系谓词
            obj: 客体实体
        """
        subj_uri = self.base_ns[subject]
        pred_uri = self.base_ns[predicate]
        obj_uri = self.base_ns[obj]
        
        self.graph.add((subj_uri, pred_uri, obj_uri))
        print(f"Created relationship: {subject} -> {predicate} -> {obj}")
    
    def save_ontology(self, filename: str):
        """
        保存本体到文件
        
        Args:
            filename: 文件名
        """
        filepath = self.storage_path / f"{filename}.ttl"
        self.graph.serialize(destination=str(filepath), format="turtle")
        print(f"Ontology saved to {filepath}")
    
    def query_ontology(self, sparql_query: str) -> List[Dict]:
        """
        查询本体
        
        Args:
            sparql_query: SPARQL查询语句
            
        Returns:
            查询结果列表
        """
        try:
            results = self.graph.query(sparql_query)
            return [dict(row) for row in results]
        except Exception as e:
            print(f"Query error: {str(e)}")
            return []
    
    def get_entities_by_type(self, entity_type: str) -> List[str]:
        """
        根据类型获取实体
        
        Args:
            entity_type: 实体类型
            
        Returns:
            实体URI列表
        """
        query = f"""
        SELECT ?entity WHERE {{
            ?entity rdf:type owl:{entity_type} .
        }}
        """
        results = self.graph.query(query)
        return [str(row[0]) for row in results]
    
    def export_to_json(self) -> Dict:
        """
        导出本体为JSON格式
        
        Returns:
            JSON格式的本体数据
        """
        entities = {}
        
        # 获取所有类
        classes = self.get_entities_by_type("Class")
        entities["classes"] = [str(c).split("#")[-1] for c in classes]
        
        # 获取所有对象属性
        object_properties = self.get_entities_by_type("ObjectProperty")
        entities["object_properties"] = [str(op).split("#")[-1] for op in object_properties]
        
        # 获取所有数据类型属性
        datatype_properties = self.get_entities_by_type("DatatypeProperty")
        entities["datatype_properties"] = [str(dp).split("#")[-1] for dp in datatype_properties]
        
        # 获取所有个体
        individuals_query = """
        SELECT DISTINCT ?individual WHERE {
            ?individual ?p ?o .
            FILTER(isIRI(?individual))
            FILTER NOT EXISTS {?individual rdf:type owl:Class}
            FILTER NOT EXISTS {?individual rdf:type owl:ObjectProperty}
            FILTER NOT EXISTS {?individual rdf:type owl:DatatypeProperty}
        }
        """
        individuals = [str(row[0]).split("#")[-1] for row in self.graph.query(individuals_query)]
        entities["individuals"] = individuals
        
        return entities


# 示例使用
if __name__ == "__main__":
    # 创建本体管理器实例
    om = OntologyManager()
    
    # 创建一些示例实体
    om.create_entity("Supplier", "Class", "供应商实体")
    om.create_entity("Product", "Class", "产品实体")
    om.create_entity("Location", "Class", "地理位置实体")
    om.create_entity("supplies", "ObjectProperty", "供应关系")
    
    # 创建关系
    om.create_relationship("Supplier", "supplies", "Product")
    
    # 保存本体
    om.save_ontology("supply_chain_demo")
    
    # 导出为JSON
    ontology_json = om.export_to_json()
    print(json.dumps(ontology_json, indent=2, ensure_ascii=False))