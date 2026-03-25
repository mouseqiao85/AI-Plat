"""
技能市场模块
支持技能发布、发现、评价、组合
"""

import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging
import json

logger = logging.getLogger(__name__)


class SkillCategory(str, Enum):
    """技能类别"""
    DATA_PROCESSING = "data_processing"
    ML_TRAINING = "ml_training"
    NLP = "nlp"
    COMPUTER_VISION = "computer_vision"
    ONTOLOGY = "ontology"
    AGENT = "agent"
    INTEGRATION = "integration"
    WORKFLOW = "workflow"
    MONITORING = "monitoring"
    UTILITY = "utility"


class SkillStatus(str, Enum):
    """技能状态"""
    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    SUSPENDED = "suspended"


class SkillVisibility(str, Enum):
    """技能可见性"""
    PRIVATE = "private"
    PUBLIC = "public"
    ORGANIZATION = "organization"


@dataclass
class SkillVersion:
    """技能版本"""
    version: str
    description: str
    changes: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    dependencies: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "description": self.description,
            "changes": self.changes,
            "created_at": self.created_at.isoformat(),
            "dependencies": self.dependencies
        }


@dataclass
class SkillReview:
    """技能评价"""
    id: str
    skill_id: str
    user_id: str
    rating: int
    comment: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    helpful_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "skill_id": self.skill_id,
            "user_id": self.user_id,
            "rating": self.rating,
            "comment": self.comment,
            "created_at": self.created_at.isoformat(),
            "helpful_count": self.helpful_count
        }


@dataclass
class SkillStats:
    """技能统计"""
    downloads: int = 0
    executions: int = 0
    success_rate: float = 0.0
    avg_rating: float = 0.0
    review_count: int = 0
    favorite_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "downloads": self.downloads,
            "executions": self.executions,
            "success_rate": self.success_rate,
            "avg_rating": self.avg_rating,
            "review_count": self.review_count,
            "favorite_count": self.favorite_count
        }


@dataclass
class Skill:
    """技能定义"""
    id: str
    name: str
    display_name: str
    description: str
    category: SkillCategory
    author_id: str
    author_name: str
    version: str = "1.0.0"
    status: SkillStatus = SkillStatus.DRAFT
    visibility: SkillVisibility = SkillVisibility.PUBLIC
    tags: List[str] = field(default_factory=list)
    icon: Optional[str] = None
    documentation_url: Optional[str] = None
    repository_url: Optional[str] = None
    config_schema: Dict[str, Any] = field(default_factory=dict)
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    examples: List[Dict[str, Any]] = field(default_factory=list)
    dependencies: Dict[str, str] = field(default_factory=dict)
    versions: List[SkillVersion] = field(default_factory=list)
    stats: SkillStats = field(default_factory=SkillStats)
    reviews: List[SkillReview] = field(default_factory=list)
    price: float = 0.0
    is_free: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category.value,
            "author_id": self.author_id,
            "author_name": self.author_name,
            "version": self.version,
            "status": self.status.value,
            "visibility": self.visibility.value,
            "tags": self.tags,
            "icon": self.icon,
            "documentation_url": self.documentation_url,
            "repository_url": self.repository_url,
            "config_schema": self.config_schema,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "examples": self.examples,
            "price": self.price,
            "is_free": self.is_free,
            "stats": self.stats.to_dict(),
            "review_count": len(self.reviews),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "published_at": self.published_at.isoformat() if self.published_at else None
        }


@dataclass
class SkillCombination:
    """技能组合"""
    id: str
    name: str
    description: str
    author_id: str
    skills: List[str]
    workflow_template: Dict[str, Any] = field(default_factory=dict)
    stats: SkillStats = field(default_factory=SkillStats)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "author_id": self.author_id,
            "skills": self.skills,
            "workflow_template": self.workflow_template,
            "stats": self.stats.to_dict(),
            "created_at": self.created_at.isoformat()
        }


class SkillMarket:
    """技能市场"""
    
    def __init__(self):
        self.skills: Dict[str, Skill] = {}
        self.combinations: Dict[str, SkillCombination] = {}
        self.user_favorites: Dict[str, List[str]] = {}
        self.categories: Dict[SkillCategory, List[str]] = {cat: [] for cat in SkillCategory}
        
        self._load_default_skills()
        
        logger.info("Skill Market initialized")
    
    def _load_default_skills(self):
        default_skills = [
            {
                "name": "text_analysis",
                "display_name": "文本分析",
                "description": "对文本进行情感分析、关键词提取、实体识别等",
                "category": SkillCategory.NLP,
                "tags": ["nlp", "text", "analysis"],
                "config_schema": {
                    "language": {"type": "string", "default": "zh"},
                    "tasks": {"type": "array", "items": ["sentiment", "keywords", "entities"]}
                }
            },
            {
                "name": "image_classification",
                "display_name": "图像分类",
                "description": "对图像进行分类识别",
                "category": SkillCategory.COMPUTER_VISION,
                "tags": ["vision", "classification", "image"],
                "config_schema": {
                    "model": {"type": "string", "default": "resnet50"},
                    "top_k": {"type": "integer", "default": 5}
                }
            },
            {
                "name": "ontology_query",
                "display_name": "本体查询",
                "description": "执行SPARQL本体查询",
                "category": SkillCategory.ONTOLOGY,
                "tags": ["ontology", "sparql", "query"],
                "config_schema": {
                    "query_type": {"type": "string", "default": "select"}
                }
            },
            {
                "name": "agent_task",
                "display_name": "代理任务执行",
                "description": "执行智能体任务",
                "category": SkillCategory.AGENT,
                "tags": ["agent", "task", "execution"],
                "config_schema": {
                    "timeout": {"type": "integer", "default": 300},
                    "retry_count": {"type": "integer", "default": 3}
                }
            },
            {
                "name": "data_transform",
                "display_name": "数据转换",
                "description": "数据格式转换和处理",
                "category": SkillCategory.DATA_PROCESSING,
                "tags": ["data", "transform", "etl"],
                "config_schema": {
                    "input_format": {"type": "string"},
                    "output_format": {"type": "string"}
                }
            },
            {
                "name": "model_training",
                "display_name": "模型训练",
                "description": "训练机器学习模型",
                "category": SkillCategory.ML_TRAINING,
                "tags": ["ml", "training", "model"],
                "config_schema": {
                    "model_type": {"type": "string"},
                    "hyperparameters": {"type": "object"}
                }
            }
        ]
        
        for skill_data in default_skills:
            skill_id = str(uuid.uuid4())
            skill = Skill(
                id=skill_id,
                name=skill_data["name"],
                display_name=skill_data["display_name"],
                description=skill_data["description"],
                category=skill_data["category"],
                author_id="system",
                author_name="System",
                status=SkillStatus.PUBLISHED,
                tags=skill_data.get("tags", []),
                config_schema=skill_data.get("config_schema", {}),
                published_at=datetime.utcnow()
            )
            self.skills[skill_id] = skill
            self.categories[skill.category].append(skill_id)
    
    def publish_skill(
        self,
        name: str,
        display_name: str,
        description: str,
        category: SkillCategory,
        author_id: str,
        author_name: str,
        tags: List[str] = None,
        config_schema: Dict[str, Any] = None,
        input_schema: Dict[str, Any] = None,
        output_schema: Dict[str, Any] = None,
        visibility: SkillVisibility = SkillVisibility.PUBLIC,
        price: float = 0.0
    ) -> Skill:
        """发布技能"""
        skill_id = str(uuid.uuid4())
        
        skill = Skill(
            id=skill_id,
            name=name,
            display_name=display_name,
            description=description,
            category=category,
            author_id=author_id,
            author_name=author_name,
            tags=tags or [],
            config_schema=config_schema or {},
            input_schema=input_schema or {},
            output_schema=output_schema or {},
            visibility=visibility,
            price=price,
            is_free=price == 0
        )
        
        self.skills[skill_id] = skill
        self.categories[category].append(skill_id)
        
        logger.info(f"Published skill: {name} ({skill_id})")
        return skill
    
    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """获取技能"""
        return self.skills.get(skill_id)
    
    def get_skill_by_name(self, name: str) -> Optional[Skill]:
        """根据名称获取技能"""
        for skill in self.skills.values():
            if skill.name == name:
                return skill
        return None
    
    def list_skills(
        self,
        category: SkillCategory = None,
        tags: List[str] = None,
        author_id: str = None,
        status: SkillStatus = None,
        search: str = None,
        sort_by: str = "downloads",
        limit: int = 20,
        offset: int = 0
    ) -> List[Skill]:
        """列出技能"""
        skills = list(self.skills.values())
        
        if status:
            skills = [s for s in skills if s.status == status]
        else:
            skills = [s for s in skills if s.status == SkillStatus.PUBLISHED]
        
        if category:
            skills = [s for s in skills if s.category == category]
        
        if tags:
            skills = [s for s in skills if any(t in s.tags for t in tags)]
        
        if author_id:
            skills = [s for s in skills if s.author_id == author_id]
        
        if search:
            search_lower = search.lower()
            skills = [s for s in skills if 
                     search_lower in s.name.lower() or
                     search_lower in s.display_name.lower() or
                     search_lower in s.description.lower() or
                     search_lower in s.tags]
        
        sort_keys = {
            "downloads": lambda s: s.stats.downloads,
            "rating": lambda s: s.stats.avg_rating,
            "created": lambda s: s.created_at,
            "updated": lambda s: s.updated_at,
            "name": lambda s: s.name
        }
        
        if sort_by in sort_keys:
            skills = sorted(skills, key=sort_keys[sort_by], reverse=True)
        
        return skills[offset:offset + limit]
    
    def update_skill(self, skill_id: str, updates: Dict[str, Any]) -> Optional[Skill]:
        """更新技能"""
        skill = self.get_skill(skill_id)
        if not skill:
            return None
        
        for key, value in updates.items():
            if hasattr(skill, key):
                setattr(skill, key, value)
        
        skill.updated_at = datetime.utcnow()
        return skill
    
    def publish(self, skill_id: str) -> bool:
        """发布技能"""
        skill = self.get_skill(skill_id)
        if not skill:
            return False
        
        skill.status = SkillStatus.PUBLISHED
        skill.published_at = datetime.utcnow()
        skill.updated_at = datetime.utcnow()
        return True
    
    def deprecate(self, skill_id: str) -> bool:
        """废弃技能"""
        skill = self.get_skill(skill_id)
        if not skill:
            return False
        
        skill.status = SkillStatus.DEPRECATED
        skill.updated_at = datetime.utcnow()
        return True
    
    def add_version(
        self,
        skill_id: str,
        version: str,
        description: str,
        changes: List[str] = None,
        dependencies: Dict[str, str] = None
    ) -> bool:
        """添加版本"""
        skill = self.get_skill(skill_id)
        if not skill:
            return False
        
        new_version = SkillVersion(
            version=version,
            description=description,
            changes=changes or [],
            dependencies=dependencies or {}
        )
        
        skill.versions.append(new_version)
        skill.version = version
        skill.updated_at = datetime.utcnow()
        return True
    
    def record_download(self, skill_id: str):
        """记录下载"""
        skill = self.get_skill(skill_id)
        if skill:
            skill.stats.downloads += 1
    
    def record_execution(self, skill_id: str, success: bool):
        """记录执行"""
        skill = self.get_skill(skill_id)
        if skill:
            skill.stats.executions += 1
            total = skill.stats.executions
            current_rate = skill.stats.success_rate
            skill.stats.success_rate = (current_rate * (total - 1) + (1 if success else 0)) / total
    
    def add_review(
        self,
        skill_id: str,
        user_id: str,
        rating: int,
        comment: str
    ) -> Optional[SkillReview]:
        """添加评价"""
        skill = self.get_skill(skill_id)
        if not skill or rating < 1 or rating > 5:
            return None
        
        review = SkillReview(
            id=str(uuid.uuid4()),
            skill_id=skill_id,
            user_id=user_id,
            rating=rating,
            comment=comment
        )
        
        skill.reviews.append(review)
        
        total_rating = sum(r.rating for r in skill.reviews)
        skill.stats.avg_rating = total_rating / len(skill.reviews)
        skill.stats.review_count = len(skill.reviews)
        
        return review
    
    def get_reviews(self, skill_id: str, limit: int = 20) -> List[SkillReview]:
        """获取评价"""
        skill = self.get_skill(skill_id)
        if not skill:
            return []
        return skill.reviews[-limit:]
    
    def add_favorite(self, user_id: str, skill_id: str) -> bool:
        """添加收藏"""
        skill = self.get_skill(skill_id)
        if not skill:
            return False
        
        if user_id not in self.user_favorites:
            self.user_favorites[user_id] = []
        
        if skill_id not in self.user_favorites[user_id]:
            self.user_favorites[user_id].append(skill_id)
            skill.stats.favorite_count += 1
        
        return True
    
    def remove_favorite(self, user_id: str, skill_id: str) -> bool:
        """移除收藏"""
        skill = self.get_skill(skill_id)
        if not skill:
            return False
        
        if user_id in self.user_favorites and skill_id in self.user_favorites[user_id]:
            self.user_favorites[user_id].remove(skill_id)
            skill.stats.favorite_count = max(0, skill.stats.favorite_count - 1)
        
        return True
    
    def get_user_favorites(self, user_id: str) -> List[Skill]:
        """获取用户收藏"""
        skill_ids = self.user_favorites.get(user_id, [])
        return [self.skills[sid] for sid in skill_ids if sid in self.skills]
    
    def create_combination(
        self,
        name: str,
        description: str,
        author_id: str,
        skills: List[str],
        workflow_template: Dict[str, Any] = None
    ) -> SkillCombination:
        """创建技能组合"""
        combination_id = str(uuid.uuid4())
        
        combination = SkillCombination(
            id=combination_id,
            name=name,
            description=description,
            author_id=author_id,
            skills=skills,
            workflow_template=workflow_template or {}
        )
        
        self.combinations[combination_id] = combination
        return combination
    
    def get_combination(self, combination_id: str) -> Optional[SkillCombination]:
        """获取技能组合"""
        return self.combinations.get(combination_id)
    
    def list_combinations(self, author_id: str = None) -> List[SkillCombination]:
        """列出技能组合"""
        combinations = list(self.combinations.values())
        if author_id:
            combinations = [c for c in combinations if c.author_id == author_id]
        return combinations
    
    def search_skills(self, query: str, limit: int = 10) -> List[Skill]:
        """搜索技能"""
        return self.list_skills(search=query, limit=limit)
    
    def get_trending_skills(self, limit: int = 10) -> List[Skill]:
        """获取热门技能"""
        return self.list_skills(sort_by="downloads", limit=limit)
    
    def get_top_rated_skills(self, limit: int = 10) -> List[Skill]:
        """获取高评分技能"""
        return self.list_skills(sort_by="rating", limit=limit)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取市场统计"""
        total_skills = len(self.skills)
        total_combinations = len(self.combinations)
        
        by_category = {}
        for cat, skill_ids in self.categories.items():
            by_category[cat.value] = len(skill_ids)
        
        total_downloads = sum(s.stats.downloads for s in self.skills.values())
        total_executions = sum(s.stats.executions for s in self.skills.values())
        
        return {
            "total_skills": total_skills,
            "total_combinations": total_combinations,
            "total_downloads": total_downloads,
            "total_executions": total_executions,
            "by_category": by_category
        }


skill_market = SkillMarket()
