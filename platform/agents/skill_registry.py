"""
技能注册中心
统一管理所有可用的技能
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
from enum import Enum
import inspect
import logging

logger = logging.getLogger(__name__)


class SkillStatus(Enum):
    """技能状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"
    TESTING = "testing"


class SkillCategory(Enum):
    """技能分类枚举"""
    DATA_PROCESSING = "data_processing"
    ML_MODEL = "ml_model"
    NLP = "nlp"
    SEARCH = "search"
    COMMUNICATION = "communication"
    UTILITIES = "utilities"
    CUSTOM = "custom"


@dataclass
class SkillMetadata:
    """技能元数据"""
    id: str
    name: str
    description: str
    version: str
    author: str
    category: SkillCategory
    status: SkillStatus
    created_at: datetime
    updated_at: datetime
    dependencies: List[str]
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    tags: List[str]


class Skill:
    """技能类封装"""
    
    def __init__(self, func: Callable, metadata: SkillMetadata):
        """
        初始化技能
        
        Args:
            func: 技能执行函数
            metadata: 技能元数据
        """
        self.func = func
        self.metadata = metadata
        self.signature = inspect.signature(func)
    
    def execute(self, **kwargs) -> Any:
        """
        执行技能
        
        Args:
            **kwargs: 技能参数
            
        Returns:
            技能执行结果
        """
        try:
            # 验证输入参数
            bound_args = self.signature.bind(**kwargs)
            bound_args.apply_defaults()
            
            # 执行技能
            result = self.func(**bound_args.arguments)
            return result
        except Exception as e:
            logger.error(f"Skill execution failed: {str(e)}")
            raise


class SkillRegistry:
    """技能注册中心"""
    
    def __init__(self):
        """初始化技能注册中心"""
        self.skills: Dict[str, Skill] = {}
        self.skill_index: Dict[str, List[str]] = {}  # 按分类索引
        self.skill_tags: Dict[str, List[str]] = {}   # 按标签索引
    
    def register_skill(self, 
                      name: str, 
                      description: str,
                      version: str = "1.0.0",
                      author: str = "unknown",
                      category: SkillCategory = SkillCategory.CUSTOM,
                      dependencies: List[str] = None,
                      input_schema: Dict[str, Any] = None,
                      output_schema: Dict[str, Any] = None,
                      tags: List[str] = None) -> Callable:
        """
        装饰器：注册技能
        
        Args:
            name: 技能名称
            description: 技能描述
            version: 版本号
            author: 作者
            category: 技能分类
            dependencies: 依赖技能列表
            input_schema: 输入参数模式
            output_schema: 输出参数模式
            tags: 标签列表
            
        Returns:
            装饰器函数
        """
        if dependencies is None:
            dependencies = []
        if input_schema is None:
            input_schema = {}
        if output_schema is None:
            output_schema = {}
        if tags is None:
            tags = []
        
        def decorator(func: Callable) -> Callable:
            # 生成唯一ID
            skill_id = str(uuid.uuid4())
            
            # 创建元数据
            metadata = SkillMetadata(
                id=skill_id,
                name=name,
                description=description,
                version=version,
                author=author,
                category=category,
                status=SkillStatus.ACTIVE,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                dependencies=dependencies,
                input_schema=input_schema,
                output_schema=output_schema,
                tags=tags
            )
            
            # 创建技能实例
            skill = Skill(func, metadata)
            
            # 注册技能
            self.skills[skill_id] = skill
            self._update_indexes(skill_id, metadata)
            
            logger.info(f"Registered skill: {name} (ID: {skill_id})")
            return func
        
        return decorator
    
    def _update_indexes(self, skill_id: str, metadata: SkillMetadata):
        """更新索引"""
        # 按分类索引
        category = metadata.category.value
        if category not in self.skill_index:
            self.skill_index[category] = []
        if skill_id not in self.skill_index[category]:
            self.skill_index[category].append(skill_id)
        
        # 按标签索引
        for tag in metadata.tags:
            if tag not in self.skill_tags:
                self.skill_tags[tag] = []
            if skill_id not in self.skill_tags[tag]:
                self.skill_tags[tag].append(skill_id)
    
    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """
        获取技能实例
        
        Args:
            skill_id: 技能ID
            
        Returns:
            技能实例或None
        """
        return self.skills.get(skill_id)
    
    def get_skill_by_name(self, name: str) -> Optional[Skill]:
        """
        通过名称获取技能
        
        Args:
            name: 技能名称
            
        Returns:
            技能实例或None
        """
        for skill in self.skills.values():
            if skill.metadata.name == name:
                return skill
        return None
    
    def list_skills(self, 
                   category: SkillCategory = None, 
                   status: SkillStatus = None,
                   tag: str = None) -> List[Skill]:
        """
        列出技能
        
        Args:
            category: 技能分类过滤
            status: 技能状态过滤
            tag: 标签过滤
            
        Returns:
            技能列表
        """
        result = []
        
        for skill in self.skills.values():
            # 分类过滤
            if category and skill.metadata.category != category:
                continue
            
            # 状态过滤
            if status and skill.metadata.status != status:
                continue
            
            # 标签过滤
            if tag and tag not in skill.metadata.tags:
                continue
            
            result.append(skill)
        
        return result
    
    def search_skills(self, query: str) -> List[Skill]:
        """
        搜索技能
        
        Args:
            query: 搜索查询
            
        Returns:
            匹配的技能列表
        """
        result = []
        query_lower = query.lower()
        
        for skill in self.skills.values():
            # 检查名称、描述和标签
            if (query_lower in skill.metadata.name.lower() or
                query_lower in skill.metadata.description.lower() or
                any(query_lower in tag.lower() for tag in skill.metadata.tags)):
                result.append(skill)
        
        return result
    
    def update_skill_status(self, skill_id: str, status: SkillStatus) -> bool:
        """
        更新技能状态
        
        Args:
            skill_id: 技能ID
            status: 新状态
            
        Returns:
            更新是否成功
        """
        if skill_id not in self.skills:
            return False
        
        skill = self.skills[skill_id]
        skill.metadata.status = status
        skill.metadata.updated_at = datetime.now()
        
        logger.info(f"Updated skill {skill.metadata.name} status to {status.value}")
        return True
    
    def remove_skill(self, skill_id: str) -> bool:
        """
        移除技能
        
        Args:
            skill_id: 技能ID
            
        Returns:
            移除是否成功
        """
        if skill_id not in self.skills:
            return False
        
        skill = self.skills[skill_id]
        name = skill.metadata.name
        
        # 从索引中移除
        category = skill.metadata.category.value
        if category in self.skill_index:
            if skill_id in self.skill_index[category]:
                self.skill_index[category].remove(skill_id)
        
        for tag_list in self.skill_tags.values():
            if skill_id in tag_list:
                tag_list.remove(skill_id)
        
        # 从主字典中移除
        del self.skills[skill_id]
        
        logger.info(f"Removed skill: {name} (ID: {skill_id})")
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取技能统计信息
        
        Returns:
            统计信息字典
        """
        stats = {
            'total_skills': len(self.skills),
            'by_category': {},
            'by_status': {},
            'by_tag': {}
        }
        
        # 按分类统计
        for category in SkillCategory:
            count = len(self.list_skills(category=category))
            stats['by_category'][category.value] = count
        
        # 按状态统计
        for status in SkillStatus:
            count = sum(1 for skill in self.skills.values() 
                       if skill.metadata.status == status)
            stats['by_status'][status.value] = count
        
        # 按标签统计
        all_tags = set()
        for skill in self.skills.values():
            all_tags.update(skill.metadata.tags)
        
        for tag in all_tags:
            count = len([skill for skill in self.skills.values() 
                        if tag in skill.metadata.tags])
            stats['by_tag'][tag] = count
        
        return stats
    
    def export_registry(self, filepath: str):
        """
        导出注册中心到文件
        
        Args:
            filepath: 输出文件路径
        """
        export_data = {
            'exported_at': datetime.now().isoformat(),
            'skills': []
        }
        
        for skill in self.skills.values():
            skill_data = {
                'metadata': asdict(skill.metadata),
                'signature': str(skill.signature)
            }
            export_data['skills'].append(skill_data)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2, 
                     default=str)
        
        logger.info(f"Exported registry to {filepath}")
    
    def import_registry(self, filepath: str):
        """
        从文件导入注册中心
        
        Args:
            filepath: 输入文件路径
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            import_data = json.load(f)
        
        # 注意：实际导入需要重新注册函数，这里仅作演示
        logger.info(f"Imported registry from {filepath}")


# 全局技能注册中心实例
global_skill_registry = SkillRegistry()


# 示例技能定义
@global_skill_registry.register_skill(
    name="data_processor",
    description="处理和清洗数据的技能",
    version="1.0.0",
    author="AI-Plat Team",
    category=SkillCategory.DATA_PROCESSING,
    tags=["data", "processing", "cleaning"]
)
def data_processor(data: List[Dict], operation: str = "clean") -> List[Dict]:
    """
    示例数据处理技能
    
    Args:
        data: 输入数据
        operation: 操作类型
        
    Returns:
        处理后的数据
    """
    if operation == "clean":
        # 简单的数据清洗逻辑
        cleaned_data = []
        for item in data:
            cleaned_item = {k: v for k, v in item.items() if v is not None}
            cleaned_data.append(cleaned_item)
        return cleaned_data
    else:
        return data


@global_skill_registry.register_skill(
    name="text_analyzer",
    description="分析文本内容的技能",
    version="1.0.0",
    author="AI-Plat Team",
    category=SkillCategory.NLP,
    tags=["text", "analysis", "nlp"]
)
def text_analyzer(text: str, analyze_type: str = "sentiment") -> Dict[str, Any]:
    """
    示例文本分析技能
    
    Args:
        text: 输入文本
        analyze_type: 分析类型
        
    Returns:
        分析结果
    """
    if analyze_type == "sentiment":
        # 简单的情感分析模拟
        positive_words = ["好", "棒", "优秀", "满意", "喜欢"]
        negative_words = ["差", "坏", "糟糕", "不满", "讨厌"]
        
        pos_count = sum(1 for word in positive_words if word in text)
        neg_count = sum(1 for word in negative_words if word in text)
        
        sentiment = "positive" if pos_count > neg_count else "negative" if neg_count > pos_count else "neutral"
        
        return {
            "sentiment": sentiment,
            "positive_score": pos_count,
            "negative_score": neg_count,
            "word_count": len(text.split())
        }
    else:
        return {"text": text, "length": len(text)}


if __name__ == "__main__":
    # 测试技能注册中心
    print("=== 技能注册中心测试 ===")
    
    # 列出所有技能
    all_skills = global_skill_registry.list_skills()
    print(f"Total skills registered: {len(all_skills)}")
    
    for skill in all_skills:
        meta = skill.metadata
        print(f"- {meta.name} ({meta.id}): {meta.description}")
        print(f"  Category: {meta.category.value}, Status: {meta.status.value}")
        print(f"  Tags: {meta.tags}")
    
    # 搜索技能
    search_results = global_skill_registry.search_skills("data")
    print(f"\nSearch 'data': Found {len(search_results)} skills")
    
    # 执行技能
    test_data = [{"name": "张三", "age": 30, "city": "北京"}, 
                 {"name": "李四", "age": None, "city": "上海"}]
    
    processor_skill = global_skill_registry.get_skill_by_name("data_processor")
    if processor_skill:
        result = processor_skill.execute(data=test_data, operation="clean")
        print(f"\nData processing result: {result}")
    
    # 获取统计信息
    stats = global_skill_registry.get_statistics()
    print(f"\nStatistics: {stats}")