"""
数据融合器
将异构数据源映射到统一的本体模型
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import json
import csv
from .ontology_manager import OntologyManager
from rdflib import URIRef, Literal, XSD
import logging

logger = logging.getLogger(__name__)


class DataFusioner:
    """
    数据融合器类，负责将异构数据源映射到统一的本体模型
    """
    
    def __init__(self, ontology_manager: OntologyManager):
        """
        初始化数据融合器
        
        Args:
            ontology_manager: 本体管理器实例
        """
        self.ontology_manager = ontology_manager
        self.graph = ontology_manager.graph
        self.base_ns = ontology_manager.base_ns
        self.mapping_rules = {}  # 数据映射规则
    
    def register_mapping_rule(self, source_type: str, target_entity: str, 
                             field_mappings: Dict[str, str]):
        """
        注册数据映射规则
        
        Args:
            source_type: 数据源类型
            target_entity: 目标本体实体
            field_mappings: 字段映射字典
        """
        self.mapping_rules[source_type] = {
            'target_entity': target_entity,
            'field_mappings': field_mappings
        }
        logger.info(f"Registered mapping rule: {source_type} -> {target_entity}")
    
    def load_csv_data(self, file_path: str, source_type: str) -> pd.DataFrame:
        """
        加载CSV数据
        
        Args:
            file_path: CSV文件路径
            source_type: 数据源类型
            
        Returns:
            DataFrame对象
        """
        df = pd.read_csv(file_path)
        logger.info(f"Loaded CSV data from {file_path}, shape: {df.shape}")
        return df
    
    def load_json_data(self, file_path: str, source_type: str) -> List[Dict]:
        """
        加载JSON数据
        
        Args:
            file_path: JSON文件路径
            source_type: 数据源类型
            
        Returns:
            JSON数据列表
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, dict):
            data = [data]  # 如果是单个对象，转为列表
        
        logger.info(f"Loaded JSON data from {file_path}, count: {len(data)}")
        return data
    
    def transform_data_to_rdf(self, data: Union[pd.DataFrame, List[Dict]], 
                             source_type: str) -> List:
        """
        将数据转换为RDF三元组
        
        Args:
            data: 输入数据（DataFrame或字典列表）
            source_type: 数据源类型
            
        Returns:
            RDF三元组列表
        """
        if source_type not in self.mapping_rules:
            raise ValueError(f"No mapping rule registered for source type: {source_type}")
        
        rule = self.mapping_rules[source_type]
        target_entity = rule['target_entity']
        field_mappings = rule['field_mappings']
        
        triples = []
        
        if isinstance(data, pd.DataFrame):
            records = data.to_dict('records')
        else:
            records = data
        
        for idx, record in enumerate(records):
            # 创建个体实例URI
            individual_uri = self.base_ns[f"{target_entity.lower()}_{idx}"]
            
            # 添加类型声明
            triples.append((individual_uri, URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'), 
                           self.base_ns[target_entity]))
            
            # 映射字段到本体属性
            for source_field, target_property in field_mappings.items():
                if source_field in record and pd.notna(record[source_field]):
                    value = record[source_field]
                    
                    # 根据值的类型确定RDF字面量类型
                    if isinstance(value, (int, float)):
                        literal_value = Literal(value)
                    elif isinstance(value, str) and self._is_valid_date(value):
                        literal_value = Literal(value, datatype=XSD.date)
                    else:
                        literal_value = Literal(str(value))
                    
                    triples.append((individual_uri, self.base_ns[target_property], literal_value))
        
        logger.info(f"Transformed {len(records)} records to {len(triples)} RDF triples")
        return triples
    
    def _is_valid_date(self, value: str) -> bool:
        """
        检查字符串是否为有效日期
        
        Args:
            value: 待检查的字符串
            
        Returns:
            是否为有效日期
        """
        try:
            pd.to_datetime(value)
            return True
        except:
            return False
    
    def fuse_data_from_source(self, data: Union[pd.DataFrame, List[Dict]], 
                            source_type: str) -> bool:
        """
        融合来自指定源的数据
        
        Args:
            data: 数据
            source_type: 数据源类型
            
        Returns:
            融合是否成功
        """
        try:
            # 转换数据为RDF三元组
            triples = self.transform_data_to_rdf(data, source_type)
            
            # 添加三元组到图中
            for subject, predicate, obj in triples:
                self.graph.add((subject, predicate, obj))
            
            logger.info(f"Successfully fused {len(triples)} triples from {source_type}")
            return True
        except Exception as e:
            logger.error(f"Failed to fuse data from {source_type}: {str(e)}")
            return False
    
    def fuse_csv_file(self, file_path: str, source_type: str) -> bool:
        """
        融合CSV文件数据
        
        Args:
            file_path: CSV文件路径
            source_type: 数据源类型
            
        Returns:
            融合是否成功
        """
        try:
            data = self.load_csv_data(file_path, source_type)
            return self.fuse_data_from_source(data, source_type)
        except Exception as e:
            logger.error(f"Failed to fuse CSV file {file_path}: {str(e)}")
            return False
    
    def fuse_json_file(self, file_path: str, source_type: str) -> bool:
        """
        融合JSON文件数据
        
        Args:
            file_path: JSON文件路径
            source_type: 数据源类型
            
        Returns:
            融合是否成功
        """
        try:
            data = self.load_json_data(file_path, source_type)
            return self.fuse_data_from_source(data, source_type)
        except Exception as e:
            logger.error(f"Failed to fuse JSON file {file_path}: {str(e)}")
            return False
    
    def detect_schema(self, data: Union[pd.DataFrame, List[Dict]]) -> Dict:
        """
        检测数据模式
        
        Args:
            data: 输入数据
            
        Returns:
            检测到的模式
        """
        if isinstance(data, pd.DataFrame):
            records = data.to_dict('records')
        else:
            records = data
        
        if not records:
            return {}
        
        # 获取所有字段及其类型
        schema = {}
        sample_record = records[0]  # 使用第一条记录作为样本
        
        for field, value in sample_record.items():
            field_type = type(value).__name__
            schema[field] = {
                'type': field_type,
                'nullable': any(pd.isna(record.get(field)) for record in records),
                'sample_value': str(value)[:100] if value is not None else None
            }
        
        return schema
    
    def suggest_ontology_mapping(self, schema: Dict, target_entity: str) -> Dict:
        """
        基于数据模式建议本体映射
        
        Args:
            schema: 数据模式
            target_entity: 目标实体
            
        Returns:
            建议的映射规则
        """
        # 简单的启发式匹配
        common_mappings = {
            'name': ['name', 'title', 'full_name', 'displayName'],
            'description': ['description', 'desc', 'notes', 'comment'],
            'id': ['id', 'identifier', 'uid', 'uuid'],
            'type': ['type', 'category', 'class'],
            'created': ['created', 'created_at', 'date_created', 'timestamp'],
            'updated': ['updated', 'updated_at', 'last_modified'],
            'email': ['email', 'email_address', 'contact_email'],
            'phone': ['phone', 'phone_number', 'tel'],
            'address': ['address', 'location', 'addr'],
            'status': ['status', 'state', 'active'],
        }
        
        suggested_mappings = {}
        
        for field, field_info in schema.items():
            matched = False
            
            # 检查是否匹配常见字段
            for ont_property, possible_names in common_mappings.items():
                if field.lower() in possible_names or \
                   any(name.lower() in field.lower() for name in possible_names):
                    suggested_mappings[field] = ont_property
                    matched = True
                    break
            
            if not matched:
                # 如果没有匹配，使用原字段名作为属性名
                suggested_mappings[field] = field.replace(' ', '_').replace('-', '_')
        
        return {
            'target_entity': target_entity,
            'field_mappings': suggested_mappings
        }
    
    def calculate_fusion_quality(self) -> Dict[str, float]:
        """
        计算数据融合质量指标
        
        Returns:
            质量指标字典
        """
        total_triples = len(self.graph)
        
        # 计算命名实体的数量
        named_individuals_query = """
        SELECT (COUNT(DISTINCT ?individual) AS ?count) WHERE {
            ?individual rdf:type ?class .
            FILTER(isIRI(?individual))
            ?class rdf:type owl:Class .
        }
        """
        individuals_count = 0
        for row in self.graph.query(named_individuals_query):
            individuals_count = int(row['count'])
        
        # 计算不同类型实体的数量
        classes_query = """
        SELECT (COUNT(DISTINCT ?class) AS ?count) WHERE {
            ?class rdf:type owl:Class .
        }
        """
        classes_count = 0
        for row in self.graph.query(classes_query):
            classes_count = int(row['count'])
        
        # 计算属性数量
        properties_query = """
        SELECT (COUNT(DISTINCT ?property) AS ?count) WHERE {
            ?property rdf:type ?propType .
            VALUES ?propType { owl:ObjectProperty owl:DatatypeProperty }
        }
        """
        properties_count = 0
        for row in self.graph.query(properties_query):
            properties_count = int(row['count'])
        
        quality_metrics = {
            'total_triples': total_triples,
            'named_individuals': individuals_count,
            'defined_classes': classes_count,
            'defined_properties': properties_count,
            'average_triples_per_individual': total_triples / max(individuals_count, 1),
            'data_richness_ratio': (classes_count + properties_count) / max(individuals_count, 1)
        }
        
        return quality_metrics


# 示例使用
if __name__ == "__main__":
    # 创建本体管理器
    om = OntologyManager()
    
    # 定义一些本体类和属性
    om.create_entity("Person", "Class", "人物实体")
    om.create_entity("name", "DatatypeProperty", "姓名")
    om.create_entity("age", "DatatypeProperty", "年龄")
    om.create_entity("email", "DatatypeProperty", "邮箱")
    om.create_entity("department", "DatatypeProperty", "部门")
    
    # 创建数据融合器
    df = DataFusioner(om)
    
    # 注册映射规则
    df.register_mapping_rule(
        source_type="employee_csv",
        target_entity="Person",
        field_mappings={
            "full_name": "name",
            "age": "age", 
            "email_address": "email",
            "dept": "department"
        }
    )
    
    # 创建示例CSV数据
    sample_data = {
        "full_name": ["张三", "李四", "王五"],
        "age": [30, 25, 35],
        "email_address": ["zhangsan@example.com", "lisi@example.com", "wangwu@example.com"],
        "dept": ["IT", "HR", "Finance"]
    }
    df_sample = pd.DataFrame(sample_data)
    
    # 融合数据
    success = df.fuse_data_from_source(df_sample, "employee_csv")
    print(f"Data fusion success: {success}")
    
    # 保存融合后的本体
    om.save_ontology("fused_data_demo")
    
    # 计算融合质量
    quality = df.calculate_fusion_quality()
    print(f"Fusion quality metrics: {quality}")
    
    # 检测模式并建议映射
    schema = df.detect_schema(df_sample)
    print(f"Detected schema: {schema}")
    
    suggested = df.suggest_ontology_mapping(schema, "Person")
    print(f"Suggested mapping: {suggested}")