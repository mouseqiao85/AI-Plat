"""
本体推理引擎
基于本体模型进行语义推理和关系推断
"""

from .ontology_manager import OntologyManager
from rdflib import Graph, Namespace, RDF, RDFS, OWL
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class InferenceEngine:
    """
    本体推理引擎类，提供基于本体的语义推理能力
    """
    
    def __init__(self, ontology_manager: OntologyManager):
        """
        初始化推理引擎
        
        Args:
            ontology_manager: 本体管理器实例
        """
        self.ontology_manager = ontology_manager
        self.graph = ontology_manager.graph
        self.base_ns = ontology_manager.base_ns
    
    def rdfs_subclass_inference(self) -> List[Tuple]:
        """
        RDFS子类推理：如果A是B的子类，B是C的子类，则A是C的子类
        
        Returns:
            推理结果列表
        """
        query = """
        SELECT ?subclass ?superclass WHERE {
            ?subclass rdfs:subClassOf ?intermediate .
            ?intermediate rdfs:subClassOf ?superclass .
            FILTER (?subclass != ?superclass)
        }
        """
        
        results = []
        for row in self.graph.query(query):
            subclass, superclass = row
            # 添加传递性子类关系
            self.graph.add((subclass, RDFS.subClassOf, superclass))
            results.append((str(subclass), str(superclass), "transitive_subclass"))
            
        return results
    
    def rdfs_domain_range_inference(self) -> List[Tuple]:
        """
        RDFS域和值域推理：如果属性P的域是类C，而实例i具有属性P，则i属于类C
        
        Returns:
            推理结果列表
        """
        query = """
        SELECT ?instance ?domain_class WHERE {
            ?instance ?property ?value .
            ?property rdfs:domain ?domain_class .
            FILTER NOT EXISTS {
                ?instance a ?domain_class .
            }
        }
        """
        
        results = []
        for row in self.graph.query(query):
            instance, domain_class = row
            # 为实例添加类型声明
            self.graph.add((instance, RDF.type, domain_class))
            results.append((str(instance), str(domain_class), "domain_inference"))
            
        return results
    
    def property_chain_inference(self) -> List[Tuple]:
        """
        属性链推理：基于OWL property chain进行推理
        
        Returns:
            推理结果列表
        """
        # 简化的属性链推理示例
        # 在实际应用中，这里会实现更复杂的OWL推理规则
        results = []
        
        # 示例：如果A supplierOf B 且 B locatedIn C，则可能存在 A supplyToRegion C
        query = """
        SELECT ?a ?c WHERE {
            ?a <http://ai-plat.org/ontology#supplierOf> ?b .
            ?b <http://ai-plat.org/ontology#locatedIn> ?c .
        }
        """
        
        for row in self.graph.query(query):
            a, c = row
            # 这里可以添加更复杂的推理逻辑
            results.append((str(a), str(c), "property_chain"))
        
        return results
    
    def class_equivalence_inference(self) -> List[Tuple]:
        """
        类等价推理：基于owl:equivalentClass进行推理
        
        Returns:
            推理结果列表
        """
        query = """
        SELECT ?class1 ?class2 ?instance WHERE {
            ?instance a ?class1 .
            ?class1 owl:equivalentClass ?class2 .
            FILTER NOT EXISTS {
                ?instance a ?class2 .
            }
        }
        """
        
        results = []
        for row in self.graph.query(query):
            class1, class2, instance = row
            # 为实例添加等价类的类型声明
            self.graph.add((instance, RDF.type, class2))
            results.append((str(instance), str(class2), "equivalence_inference"))
            
        return results
    
    def perform_inference(self) -> Dict[str, List[Tuple]]:
        """
        执行所有类型的推理
        
        Returns:
            包含各种推理结果的字典
        """
        logger.info("Starting inference process...")
        
        results = {}
        
        # 执行RDFS子类推理
        results['rdfs_subclass'] = self.rdfs_subclass_inference()
        logger.info(f"RDFS subclass inference: {len(results['rdfs_subclass'])} new facts added")
        
        # 执行RDFS域值域推理
        results['rdfs_domain_range'] = self.rdfs_domain_range_inference()
        logger.info(f"RDFS domain/range inference: {len(results['rdfs_domain_range'])} new facts added")
        
        # 执行属性链推理
        results['property_chain'] = self.property_chain_inference()
        logger.info(f"Property chain inference: {len(results['property_chain'])} patterns found")
        
        # 执行类等价推理
        results['class_equivalence'] = self.class_equivalence_inference()
        logger.info(f"Class equivalence inference: {len(results['class_equivalence'])} new facts added")
        
        logger.info("Inference process completed.")
        
        return results
    
    def query_reasoned_knowledge(self, original_query: str) -> List:
        """
        基于推理后的知识库执行查询
        
        Args:
            original_query: 原始SPARQL查询
            
        Returns:
            查询结果
        """
        # 首先执行推理以丰富知识库
        self.perform_inference()
        
        # 执行查询
        results = self.graph.query(original_query)
        return [dict(row) for row in results]
    
    def consistency_check(self) -> Dict[str, bool]:
        """
        一致性检查：检查本体是否包含矛盾
        
        Returns:
            一致性检查结果
        """
        results = {
            'consistent': True,
            'issues_found': []
        }
        
        # 检查矛盾的类型声明（例如，既是Class又是Individual）
        contradictory_types_query = """
        SELECT ?entity ?type1 ?type2 WHERE {
            ?entity a ?type1 .
            ?entity a ?type2 .
            FILTER (?type1 != ?type2)
            {
                ?type1 rdf:type owl:Class .
                ?type2 rdf:type owl:ObjectProperty .
            } UNION {
                ?type1 rdf:type owl:Class .
                ?type2 rdf:type owl:DatatypeProperty .
            } UNION {
                ?type1 rdf:type owl:ObjectProperty .
                ?type2 rdf:type owl:Class .
            } UNION {
                ?type1 rdf:type owl:DatatypeProperty .
                ?type2 rdf:type owl:Class .
            }
        }
        """
        
        contradictions = list(self.graph.query(contradictory_types_query))
        if contradictions:
            results['consistent'] = False
            results['issues_found'].append({
                'type': 'contradictory_types',
                'count': len(contradictions),
                'examples': [(str(row[0]), str(row[1]), str(row[2])) for row in contradictions[:5]]
            })
        
        # 检查循环的子类关系（A是B的子类，B是A的子类）
        circular_subclass_query = """
        SELECT ?class1 ?class2 WHERE {
            ?class1 rdfs:subClassOf ?class2 .
            ?class2 rdfs:subClassOf ?class1 .
            FILTER (?class1 != ?class2)
        }
        """
        
        circular_relations = list(self.graph.query(circular_subclass_query))
        if circular_relations:
            results['consistent'] = False
            results['issues_found'].append({
                'type': 'circular_subclass',
                'count': len(circular_relations),
                'examples': [(str(row[0]), str(row[1])) for row in circular_relations[:5]]
            })
        
        return results
    
    def impact_analysis(self, entity_uri: str) -> Dict[str, List[str]]:
        """
        影响分析：分析修改某个实体可能带来的影响
        
        Args:
            entity_uri: 实体URI
            
        Returns:
            影响分析结果
        """
        results = {
            'incoming_relations': [],  # 指向该实体的关系
            'outgoing_relations': [],  # 从该实体出发的关系
            'related_classes': [],     # 相关的类
            'dependent_entities': []   # 依赖该实体的实体
        }
        
        # 查询指向该实体的关系
        incoming_query = f"""
        SELECT ?subject ?predicate WHERE {{
            ?subject ?predicate <{entity_uri}> .
        }}
        """
        results['incoming_relations'] = [(str(row[0]), str(row[1])) for row in self.graph.query(incoming_query)]
        
        # 查询从该实体出发的关系
        outgoing_query = f"""
        SELECT ?predicate ?object WHERE {{
            <{entity_uri}> ?predicate ?object .
        }}
        """
        results['outgoing_relations'] = [(str(row[0]), str(row[1])) for row in self.graph.query(outgoing_query)]
        
        # 查询相关的类（如果是类的话）
        related_classes_query = f"""
        SELECT ?related_class WHERE {{
            <{entity_uri}> ?p ?related_class .
            ?related_class rdf:type owl:Class .
            FILTER (<{entity_uri}> != ?related_class)
        }} UNION {{
            ?related_class ?p <{entity_uri}> .
            ?related_class rdf:type owl:Class .
            FILTER (<{entity_uri}> != ?related_class)
        }}
        """
        results['related_classes'] = [str(row[0]) for row in self.graph.query(related_classes_query)]
        
        # 查询依赖该实体的其他实体
        dependency_query = f"""
        SELECT ?dependent WHERE {{
            ?dependent rdfs:subClassOf* <{entity_uri}> .
            FILTER (?dependent != <{entity_uri}>)
        }} UNION {{
            ?dependent ?p <{entity_uri}> .
            ?p rdfs:domain <{entity_uri}> .
            FILTER (?dependent != <{entity_uri}>)
        }}
        """
        results['dependent_entities'] = [str(row[0]) for row in self.graph.query(dependency_query)]
        
        return results


# 示例使用
if __name__ == "__main__":
    # 创建本体管理器
    om = OntologyManager()
    
    # 添加一些示例数据用于推理演示
    om.create_entity("Person", "Class", "人物类")
    om.create_entity("Student", "Class", "学生类")
    om.create_entity("Teacher", "Class", "教师类")
    om.create_entity("Course", "Class", "课程类")
    om.create_entity("teaches", "ObjectProperty", "教学关系")
    om.create_entity("enrolledIn", "ObjectProperty", "注册关系")
    
    # 创建关系
    om.create_relationship("Student", "rdfs:subClassOf", "Person")
    om.create_relationship("Teacher", "rdfs:subClassOf", "Person")
    om.create_relationship("Teacher", "teaches", "Course")
    om.create_relationship("Student", "enrolledIn", "Course")
    
    # 保存本体
    om.save_ontology("inference_demo")
    
    # 创建推理引擎
    ie = InferenceEngine(om)
    
    # 执行推理
    inference_results = ie.perform_inference()
    
    print("Inference Results:")
    for inference_type, results in inference_results.items():
        print(f"  {inference_type}: {len(results)} results")
        for result in results[:3]:  # 显示前3个结果
            print(f"    {result}")
    
    # 进行一致性检查
    consistency = ie.consistency_check()
    print(f"\nConsistency Check: {consistency}")
    
    # 进行影响分析
    impact = ie.impact_analysis("http://ai-plat.org/ontology#Person")
    print(f"\nImpact Analysis for Person: {impact}")