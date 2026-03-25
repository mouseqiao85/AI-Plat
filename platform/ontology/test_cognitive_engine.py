"""
智能本体引擎测试
测试动态本体构建器和认知推理器
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ontology import (
    OntologyManager,
    InferenceEngine,
    DynamicOntologyBuilder,
    CognitiveReasoner
)


class TestOntologyManager(unittest.TestCase):
    """测试本体管理器"""
    
    def setUp(self):
        """测试前准备"""
        self.manager = OntologyManager(storage_path="./test_ontology")
    
    def test_create_entity(self):
        """测试创建实体"""
        self.manager.create_entity("TestPerson", "Class", "测试人物类")
        
        entities = self.manager.get_entities_by_type("Class")
        entity_names = [str(e).split("#")[-1] for e in entities]
        
        self.assertIn("TestPerson", entity_names)
    
    def test_create_relationship(self):
        """测试创建关系"""
        self.manager.create_entity("Employee", "Class", "员工类")
        self.manager.create_entity("Department", "Class", "部门类")
        self.manager.create_relationship("Employee", "worksIn", "Department")
        
        query = """
        SELECT ?s ?p ?o WHERE {
            ?s ?p ?o .
            FILTER (str(?p) CONTAINS "worksIn")
        }
        """
        results = self.manager.query_ontology(query)
        
        self.assertIsNotNone(results)


class TestInferenceEngine(unittest.TestCase):
    """测试推理引擎"""
    
    def setUp(self):
        """测试前准备"""
        self.manager = OntologyManager(storage_path="./test_ontology")
        self.engine = InferenceEngine(self.manager)
    
    def test_perform_inference(self):
        """测试执行推理"""
        results = self.engine.perform_inference()
        
        self.assertIsInstance(results, dict)
        self.assertIn('rdfs_subclass', results)
        self.assertIn('rdfs_domain_range', results)
    
    def test_consistency_check(self):
        """测试一致性检查"""
        results = self.engine.consistency_check()
        
        self.assertIsInstance(results, dict)
        self.assertIn('consistent', results)


class TestDynamicOntologyBuilder(unittest.TestCase):
    """测试动态本体构建器"""
    
    def setUp(self):
        """测试前准备"""
        self.manager = OntologyManager(storage_path="./test_ontology")
        self.builder = DynamicOntologyBuilder(self.manager)
    
    def test_analyze_data_patterns(self):
        """测试数据模式分析"""
        sample_data = [
            {
                "id": "person_001",
                "name": "张三",
                "age": 30,
                "department": "sales"
            },
            {
                "id": "person_002",
                "name": "李四",
                "age": 25,
                "department": "engineering"
            }
        ]
        
        patterns = self.builder._analyze_data_patterns(sample_data)
        
        self.assertIsInstance(patterns, dict)
        self.assertIn("entities", patterns)
        self.assertIn("properties", patterns)
    
    def test_adapt_to_data_pattern(self):
        """测试自适应建模"""
        sample_data = [
            {
                "id": "product_001",
                "name": "Laptop",
                "price": 999.99,
                "category": "electronics"
            }
        ]
        
        result = self.builder.adapt_to_data_pattern(sample_data, "test_domain")
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result["status"], "completed")
        self.assertIn("patterns_detected", result)
    
    def test_incremental_update(self):
        """测试增量更新"""
        new_data = [
            {
                "id": "order_001",
                "customer": "customer_001",
                "amount": 100.00
            }
        ]
        
        result = self.builder.incremental_update(new_data)
        
        self.assertIsInstance(result, dict)
        self.assertIn("status", result)
        self.assertIn("update_id", result)
    
    def test_version_management(self):
        """测试版本管理"""
        version_history = self.builder.get_version_history()
        
        self.assertIsInstance(version_history, list)
    
    def test_conflict_detection(self):
        """测试冲突检测"""
        conflicts = self.builder._detect_conflicts()
        
        self.assertIsInstance(conflicts, list)


class TestCognitiveReasoner(unittest.TestCase):
    """测试认知推理器"""
    
    def setUp(self):
        """测试前准备"""
        self.manager = OntologyManager(storage_path="./test_ontology")
        self.inference_engine = InferenceEngine(self.manager)
        self.reasoner = CognitiveReasoner(self.manager, self.inference_engine)
    
    def test_parse_query(self):
        """测试查询解析"""
        query = "Why did sales increase?"
        parsed = self.reasoner._parse_query(query)
        
        self.assertIsInstance(parsed, dict)
        self.assertEqual(parsed["type"], "causal")
    
    def test_deep_reasoning(self):
        """测试深度推理"""
        result = self.reasoner.deep_reasoning("What is the relationship?", max_depth=2)
        
        self.assertIsInstance(result, dict)
        self.assertIn("query", result)
        self.assertIn("confidence", result)
    
    def test_uncertain_reasoning(self):
        """测试不确定性推理"""
        result = self.reasoner.uncertain_reasoning(
            "Will this project succeed?",
            evidence={"team_experience": 0.8, "resource_availability": 0.6}
        )
        
        self.assertIsInstance(result, dict)
        self.assertIn("overall_confidence", result)
        self.assertGreater(result["overall_confidence"], 0)
    
    def test_causal_reasoning(self):
        """测试因果推理"""
        result = self.reasoner.causal_reasoning("Sales increased after marketing campaign", depth=2)
        
        self.assertIsInstance(result, dict)
        self.assertIn("reasoning_result", result)
        self.assertIn("causal_model", result)
    
    def test_counterfactual_reasoning(self):
        """测试反事实推理"""
        result = self.reasoner.counterfactual_reasoning(
            "The company invested in R&D and developed a new product"
        )
        
        self.assertIsInstance(result, dict)
        self.assertIn("original_scenario", result)
        self.assertIn("alternative_scenario", result)
        self.assertIn("reasoning_result", result)
    
    def test_generate_alternative_scenario(self):
        """测试生成替代场景"""
        parsed = {
            "original": "The project was successful",
            "agents": [],
            "actions": [],
            "states": ["successful"],
            "conditions": [],
            "outcomes": []
        }
        
        alternative = self.reasoner._generate_alternative_scenario(parsed)
        
        self.assertIsInstance(alternative, str)
        self.assertNotEqual(alternative, parsed["original"])


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def setUp(self):
        """测试前准备"""
        self.manager = OntologyManager(storage_path="./test_ontology")
        self.inference_engine = InferenceEngine(self.manager)
        self.builder = DynamicOntologyBuilder(self.manager)
        self.reasoner = CognitiveReasoner(self.manager, self.inference_engine)
    
    def test_full_workflow(self):
        """测试完整工作流"""
        # 1. 使用动态构建器创建本体
        sample_data = [
            {
                "id": "supplier_001",
                "name": "供应商A",
                "location": "北京",
                "products": ["product_001", "product_002"]
            }
        ]
        
        adaptation_result = self.builder.adapt_to_data_pattern(sample_data, "supply_chain")
        self.assertEqual(adaptation_result["status"], "completed")
        
        # 2. 使用推理引擎进行推理
        inference_result = self.inference_engine.perform_inference()
        self.assertIsInstance(inference_result, dict)
        
        # 3. 使用认知推理器进行深度推理
        reasoning_result = self.reasoner.deep_reasoning("What are the supply chain relationships?")
        self.assertIn("confidence", reasoning_result)
        
        # 4. 检查版本历史
        version_history = self.builder.get_version_history()
        self.assertGreater(len(version_history), 0)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestOntologyManager))
    suite.addTests(loader.loadTestsFromTestCase(TestInferenceEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestDynamicOntologyBuilder))
    suite.addTests(loader.loadTestsFromTestCase(TestCognitiveReasoner))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    run_tests()
