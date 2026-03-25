"""
Skills Management API Routes
技能管理API - 支持技能CRUD、执行、市场等功能
"""

from fastapi import APIRouter, HTTPException, Query, Depends, Body
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import json

from auth.models import User
from auth.dependencies import get_current_active_user, get_optional_user

router = APIRouter(prefix="/skills", tags=["Skills"])


mock_skills: Dict[str, Dict] = {}
mock_skill_usage: List[Dict] = []


class SkillCreate(BaseModel):
    skillKey: str = Field(..., description="技能唯一标识")
    name: str = Field(..., description="技能名称")
    description: Optional[str] = Field(None, description="技能描述")
    category: str = Field(default="TOOLS", description="分类: AI, TOOLS, AUTOMATION, DATA, INTEGRATION")
    skillContent: str = Field(..., description="skill.md内容")
    tags: List[str] = Field(default_factory=list, description="标签")
    isPublic: bool = Field(default=True, description="是否公开")
    iconUrl: Optional[str] = Field(None, description="图标URL")


class SkillUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    skillContent: Optional[str] = None
    tags: Optional[List[str]] = None
    isPublic: Optional[bool] = None
    iconUrl: Optional[str] = None


class SkillExecute(BaseModel):
    parameters: Dict[str, Any] = Field(default_factory=dict, description="执行参数")


def init_mock_skills():
    if not mock_skills:
        mock_skills["weather-forecast"] = {
            "id": 1,
            "skillKey": "weather-forecast",
            "name": "天气预报",
            "description": "获取指定城市的实时天气信息和未来天气预报",
            "category": "TOOLS",
            "author": {"id": 1, "username": "admin"},
            "version": "1.0.0",
            "skillContent": """# 天气预报技能

## 描述
获取指定城市的实时天气信息和未来天气预报

## 参数
- city (string): 城市名称
- days (number, optional): 预报天数，默认1天

## 使用示例
```python
result = execute_skill("weather-forecast", {"city": "北京", "days": 3})
```

## 返回值
```json
{
  "city": "北京",
  "temperature": 25,
  "weather": "晴",
  "forecast": [...]
}
```
""",
            "iconUrl": None,
            "tags": ["天气", "API", "实用工具"],
            "isPublic": True,
            "isVerified": True,
            "usageCount": 150,
            "rating": 4.5,
            "createdAt": "2026-03-17T08:00:00Z",
            "updatedAt": "2026-03-17T08:00:00Z"
        }
        mock_skills["code-review"] = {
            "id": 2,
            "skillKey": "code-review",
            "name": "代码审查",
            "description": "自动审查代码质量，发现潜在问题和改进建议",
            "category": "AI",
            "author": {"id": 1, "username": "admin"},
            "version": "2.1.0",
            "skillContent": """# 代码审查技能

## 描述
使用AI自动审查代码质量，发现潜在问题和改进建议

## 参数
- code (string): 要审查的代码
- language (string): 编程语言
- rules (array, optional): 自定义规则

## 使用示例
```python
result = execute_skill("code-review", {
    "code": "def hello(): print('hello')",
    "language": "python"
})
```

## 返回值
```json
{
  "score": 85,
  "issues": [...],
  "suggestions": [...]
}
```
""",
            "iconUrl": None,
            "tags": ["代码", "AI", "质量"],
            "isPublic": True,
            "isVerified": True,
            "usageCount": 320,
            "rating": 4.8,
            "createdAt": "2026-03-16T10:00:00Z",
            "updatedAt": "2026-03-17T09:00:00Z"
        }
        mock_skills["data-extraction"] = {
            "id": 3,
            "skillKey": "data-extraction",
            "name": "数据抽取",
            "description": "从非结构化文本中抽取结构化数据",
            "category": "DATA",
            "author": {"id": 2, "username": "developer"},
            "version": "1.5.0",
            "skillContent": """# 数据抽取技能

## 描述
从非结构化文本中抽取结构化数据，支持多种实体类型

## 参数
- text (string): 输入文本
- entities (array): 要抽取的实体类型

## 使用示例
```python
result = execute_skill("data-extraction", {
    "text": "张三的电话是13800138000",
    "entities": ["person", "phone"]
})
```
""",
            "iconUrl": None,
            "tags": ["数据", "NLP", "抽取"],
            "isPublic": True,
            "isVerified": False,
            "usageCount": 89,
            "rating": 4.2,
            "createdAt": "2026-03-15T14:30:00Z",
            "updatedAt": "2026-03-15T14:30:00Z"
        }


init_mock_skills()


@router.get("")
async def list_skills(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    category: Optional[str] = Query(None, description="分类筛选"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """获取技能列表"""
    skills_list = list(mock_skills.values())
    
    if category and category != "all":
        skills_list = [s for s in skills_list if s.get("category") == category]
    
    if search:
        search_lower = search.lower()
        skills_list = [
            s for s in skills_list 
            if search_lower in s.get("name", "").lower() 
            or search_lower in s.get("description", "").lower()
            or any(search_lower in tag.lower() for tag in s.get("tags", []))
        ]
    
    total = len(skills_list)
    start = (page - 1) * size
    end = start + size
    paginated = skills_list[start:end]
    
    return {
        "code": 200,
        "message": "获取成功",
        "data": {
            "page": page,
            "size": size,
            "total": total,
            "list": paginated
        }
    }


@router.post("")
async def create_skill(
    skill: SkillCreate,
    current_user: User = Depends(get_current_active_user)
):
    """创建技能"""
    if skill.skillKey in mock_skills:
        raise HTTPException(status_code=400, detail="技能key已存在")
    
    new_skill = {
        "id": len(mock_skills) + 1,
        "skillKey": skill.skillKey,
        "name": skill.name,
        "description": skill.description or "",
        "category": skill.category,
        "author": {"id": current_user.id, "username": current_user.username},
        "version": "1.0.0",
        "skillContent": skill.skillContent,
        "iconUrl": skill.iconUrl,
        "tags": skill.tags,
        "isPublic": skill.isPublic,
        "isVerified": False,
        "usageCount": 0,
        "rating": 0.0,
        "createdAt": datetime.utcnow().isoformat() + "Z",
        "updatedAt": datetime.utcnow().isoformat() + "Z"
    }
    
    mock_skills[skill.skillKey] = new_skill
    
    return {
        "code": 201,
        "message": "技能创建成功",
        "data": {
            "id": new_skill["id"],
            "skillKey": new_skill["skillKey"],
            "name": new_skill["name"]
        }
    }


@router.get("/{skill_key}")
async def get_skill(
    skill_key: str,
    current_user: Optional[User] = Depends(get_optional_user)
):
    """获取技能详情"""
    if skill_key not in mock_skills:
        raise HTTPException(status_code=404, detail="技能不存在")
    
    skill = mock_skills[skill_key].copy()
    
    return {
        "code": 200,
        "message": "获取成功",
        "data": skill
    }


@router.put("/{skill_key}")
async def update_skill(
    skill_key: str,
    update: SkillUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """更新技能"""
    if skill_key not in mock_skills:
        raise HTTPException(status_code=404, detail="技能不存在")
    
    skill = mock_skills[skill_key]
    
    if skill["author"]["id"] != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="无权限修改此技能")
    
    update_data = update.dict(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            skill[key] = value
    
    version_parts = skill["version"].split(".")
    version_parts[-1] = str(int(version_parts[-1]) + 1)
    skill["version"] = ".".join(version_parts)
    skill["updatedAt"] = datetime.utcnow().isoformat() + "Z"
    
    return {
        "code": 200,
        "message": "技能更新成功",
        "data": {
            "id": skill["id"],
            "skillKey": skill["skillKey"],
            "version": skill["version"]
        }
    }


@router.delete("/{skill_key}")
async def delete_skill(
    skill_key: str,
    current_user: User = Depends(get_current_active_user)
):
    """删除技能"""
    if skill_key not in mock_skills:
        raise HTTPException(status_code=404, detail="技能不存在")
    
    skill = mock_skills[skill_key]
    
    if skill["author"]["id"] != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="无权限删除此技能")
    
    del mock_skills[skill_key]
    
    return {
        "code": 200,
        "message": "技能删除成功"
    }


@router.post("/{skill_key}/execute")
async def execute_skill(
    skill_key: str,
    request: SkillExecute,
    current_user: User = Depends(get_current_active_user)
):
    """执行技能"""
    if skill_key not in mock_skills:
        raise HTTPException(status_code=404, detail="技能不存在")
    
    import time
    start_time = time.time()
    
    skill = mock_skills[skill_key]
    skill["usageCount"] = skill.get("usageCount", 0) + 1
    
    execution_time = int((time.time() - start_time) * 1000) + 100
    
    usage_record = {
        "id": len(mock_skill_usage) + 1,
        "userId": current_user.id,
        "skillId": skill["id"],
        "skillKey": skill_key,
        "parameters": request.parameters,
        "result": f"技能 {skill['name']} 执行成功",
        "success": True,
        "executionTimeMs": execution_time,
        "createdAt": datetime.utcnow().isoformat() + "Z"
    }
    mock_skill_usage.append(usage_record)
    
    mock_result = {
        "weather-forecast": {
            "result": {
                "city": request.parameters.get("city", "北京"),
                "temperature": 25,
                "weather": "晴",
                "humidity": 45,
                "wind": "东南风3级",
                "forecast": [
                    {"date": "2026-03-18", "high": 27, "low": 18, "weather": "多云"},
                    {"date": "2026-03-19", "high": 26, "low": 17, "weather": "晴"}
                ]
            }
        },
        "code-review": {
            "result": {
                "score": 85,
                "issues": [
                    {"line": 5, "type": "warning", "message": "缺少类型注解"},
                    {"line": 10, "type": "info", "message": "建议添加文档字符串"}
                ],
                "suggestions": [
                    "考虑使用更明确的变量名",
                    "添加单元测试覆盖"
                ],
                "metrics": {
                    "complexity": "低",
                    "maintainability": "良好",
                    "coverage": "建议提升至80%以上"
                }
            }
        },
        "data-extraction": {
            "result": {
                "entities": [
                    {"type": "person", "value": request.parameters.get("text", "")[:10], "confidence": 0.95},
                    {"type": "phone", "value": "138****8000", "confidence": 0.99}
                ],
                "structured_data": {
                    "person": request.parameters.get("text", "")[:10] if request.parameters.get("text") else None,
                    "phone": "138****8000"
                }
            }
        }
    }
    
    result = mock_result.get(skill_key, {
        "result": f"技能 {skill['name']} 执行完成",
        "output": request.parameters
    })
    
    return {
        "code": 200,
        "message": "执行成功",
        "data": {
            **result,
            "executionTime": execution_time,
            "success": True
        }
    }


@router.get("/{skill_key}/versions")
async def get_skill_versions(
    skill_key: str,
    current_user: Optional[User] = Depends(get_optional_user)
):
    """获取技能版本历史"""
    if skill_key not in mock_skills:
        raise HTTPException(status_code=404, detail="技能不存在")
    
    skill = mock_skills[skill_key]
    
    versions = [
        {
            "version": skill["version"],
            "changes": "初始版本",
            "createdAt": skill["createdAt"],
            "author": skill["author"]["username"]
        }
    ]
    
    return {
        "code": 200,
        "message": "获取成功",
        "data": {
            "skillKey": skill_key,
            "currentVersion": skill["version"],
            "versions": versions
        }
    }


@router.get("/market/popular")
async def get_popular_skills(
    limit: int = Query(10, ge=1, le=50),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """获取热门技能（技能市场）"""
    skills_list = list(mock_skills.values())
    skills_list.sort(key=lambda x: x.get("usageCount", 0), reverse=True)
    
    return {
        "code": 200,
        "message": "获取成功",
        "data": {
            "skills": skills_list[:limit],
            "count": len(skills_list[:limit])
        }
    }


@router.get("/market/categories")
async def get_skill_categories(
    current_user: Optional[User] = Depends(get_optional_user)
):
    """获取技能分类列表"""
    categories = [
        {"key": "AI", "label": "AI智能", "count": sum(1 for s in mock_skills.values() if s.get("category") == "AI")},
        {"key": "TOOLS", "label": "工具类", "count": sum(1 for s in mock_skills.values() if s.get("category") == "TOOLS")},
        {"key": "AUTOMATION", "label": "自动化", "count": sum(1 for s in mock_skills.values() if s.get("category") == "AUTOMATION")},
        {"key": "DATA", "label": "数据处理", "count": sum(1 for s in mock_skills.values() if s.get("category") == "DATA")},
        {"key": "INTEGRATION", "label": "集成服务", "count": sum(1 for s in mock_skills.values() if s.get("category") == "INTEGRATION")},
    ]
    
    return {
        "code": 200,
        "message": "获取成功",
        "data": categories
    }


@router.post("/{skill_key}/rate")
async def rate_skill(
    skill_key: str,
    rating: float = Body(..., ge=0, le=5),
    comment: Optional[str] = Body(None),
    current_user: User = Depends(get_current_active_user)
):
    """评价技能"""
    if skill_key not in mock_skills:
        raise HTTPException(status_code=404, detail="技能不存在")
    
    skill = mock_skills[skill_key]
    current_rating = skill.get("rating", 0.0)
    usage_count = skill.get("usageCount", 0)
    
    if usage_count > 0:
        skill["rating"] = round((current_rating * usage_count + rating) / (usage_count + 1), 2)
    else:
        skill["rating"] = rating
    
    return {
        "code": 200,
        "message": "评价成功",
        "data": {
            "skillKey": skill_key,
            "newRating": skill["rating"]
        }
    }


@router.get("/usage/history")
async def get_usage_history(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user)
):
    """获取技能使用历史"""
    user_usage = [u for u in mock_skill_usage if u["userId"] == current_user.id]
    
    total = len(user_usage)
    start = (page - 1) * size
    end = start + size
    paginated = user_usage[start:end]
    
    return {
        "code": 200,
        "message": "获取成功",
        "data": {
            "page": page,
            "size": size,
            "total": total,
            "list": paginated
        }
    }


# ========== Export & Import ==========

@router.get("/{skill_key}/export")
async def export_skill(skill_key: str):
    init_mock_skills()
    if skill_key not in mock_skills:
        raise HTTPException(status_code=404, detail="Skill not found")
    skill = mock_skills[skill_key]
    md_content = f"# {skill['name']}

---
skillKey: {skill['skillKey']}
category: {skill['category']}
version: {skill['version']}
---

## Description
{skill['description']}

{skill.get('skillContent', '')}"
    return {"filename": f"{skill_key}.md", "content": md_content, "mimeType": "text/markdown"}


class SkillImportRequest(BaseModel):
    filename: str
    content: str


class SkillImportResponse(BaseModel):
    success: bool
    skill: Optional[Dict[str, Any]] = None
    message: str
    warnings: List[str] = []


@router.post("/import", response_model=SkillImportResponse)
async def import_skill(request: SkillImportRequest):
    import re
    warnings = []
    try:
        content = request.content
        frontmatter = {}
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                fm_text = parts[1].strip()
                for line in fm_text.split('
'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        frontmatter[key.strip()] = value.strip()
                content = parts[2].strip()
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        name = title_match.group(1) if title_match else request.filename.replace('.md', '')
        skill_key = frontmatter.get('skillKey', name.lower().replace(' ', '-'))
        init_mock_skills()
        skill = {
            "id": len(mock_skills) + 1,
            "skillKey": skill_key,
            "name": name,
            "description": frontmatter.get('description', ''),
            "category": frontmatter.get('category', 'TOOLS'),
            "author": {"id": 1, "username": "current_user"},
            "version": frontmatter.get('version', '1.0.0'),
            "skillContent": content,
            "tags": [],
            "isPublic": True,
            "usageCount": 0,
            "rating": 0.0,
            "createdAt": datetime.now().isoformat(),
        }
        mock_skills[skill_key] = skill
        return SkillImportResponse(success=True, skill=skill, message=f"Skill '{name}' imported", warnings=warnings)
    except Exception as e:
        return SkillImportResponse(success=False, message=str(e), warnings=warnings)


# ========== Version Management ==========

mock_skill_versions: Dict[str, List[Dict]] = {}


@router.get("/{skill_key}/versions")
async def get_skill_versions(skill_key: str):
    init_mock_skills()
    if skill_key not in mock_skills:
        raise HTTPException(status_code=404, detail="Skill not found")
    if skill_key not in mock_skill_versions:
        skill = mock_skills[skill_key]
        mock_skill_versions[skill_key] = [{"version_id": f"{skill_key}-v1", "version_number": skill['version'], "created_at": skill['createdAt'], "created_by": skill['author']}]
    return {"skill_key": skill_key, "versions": mock_skill_versions[skill_key], "total": len(mock_skill_versions[skill_key])}


class RollbackRequest(BaseModel):
    target_version: str


@router.post("/{skill_key}/rollback")
async def rollback_skill(skill_key: str, request: RollbackRequest):
    init_mock_skills()
    if skill_key not in mock_skills:
        raise HTTPException(status_code=404, detail="Skill not found")
    current = mock_skills[skill_key]['version']
    mock_skills[skill_key]['version'] = request.target_version
    return {"success": True, "current_version": request.target_version, "previous_version": current}


# ========== Statistics ==========

@router.get("/stats")
async def get_skill_stats():
    init_mock_skills()
    skills = list(mock_skills.values())
    return {
        "total_skills": len(skills),
        "total_usage": sum(s.get('usageCount', 0) for s in skills),
        "avg_rating": round(sum(s.get('rating', 0) for s in skills) / len(skills), 2) if skills else 0,
        "top_categories": [{"category": "TOOLS", "count": 2}, {"category": "AI", "count": 1}],
    }


# ========== Reviews ==========

mock_reviews: Dict[str, List[Dict]] = {}


class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: str


@router.post("/{skill_key}/reviews")
async def create_review(skill_key: str, request: ReviewCreate):
    init_mock_skills()
    if skill_key not in mock_skills:
        raise HTTPException(status_code=404, detail="Skill not found")
    if skill_key not in mock_reviews:
        mock_reviews[skill_key] = []
    review = {"id": len(mock_reviews[skill_key]) + 1, "skill_key": skill_key, "user": {"id": 1, "username": "current_user"}, "rating": request.rating, "comment": request.comment, "created_at": datetime.now().isoformat()}
    mock_reviews[skill_key].append(review)
    ratings = [r['rating'] for r in mock_reviews[skill_key]]
    mock_skills[skill_key]['rating'] = round(sum(ratings) / len(ratings), 1)
    return {"success": True, "review": review}


@router.get("/{skill_key}/reviews")
async def get_reviews(skill_key: str):
    init_mock_skills()
    if skill_key not in mock_skills:
        raise HTTPException(status_code=404, detail="Skill not found")
    reviews = mock_reviews.get(skill_key, [])
    return {"skill_key": skill_key, "reviews": reviews, "total": len(reviews), "avg_rating": mock_skills[skill_key].get('rating', 0)}
