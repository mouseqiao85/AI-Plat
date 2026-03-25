"""
本体模块初始化
V3.0 智能本体引擎
"""
from .ontology_manager import OntologyManager
from .inference_engine import InferenceEngine
from .data_fusioner import DataFusioner
from .dynamic_ontology_builder import DynamicOntologyBuilder
from .cognitive_reasoner import CognitiveReasoner

__all__ = [
    'OntologyManager',
    'InferenceEngine',
    'DataFusioner',
    'DynamicOntologyBuilder',
    'CognitiveReasoner'
]