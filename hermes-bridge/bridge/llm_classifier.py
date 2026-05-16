"""LLM-based skill classifier and scenario generator.

Uses DeepSeek API to analyze imported SKILL.md files and produce:
- Category classification (planning vs implementation)
- Display names (Chinese)
- Capability tags
- Tool recommendations
- Auto-generated scenarios for groups of related skills
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_CLASSIFIER_MODEL", "") or os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")


@dataclass
class SkillClassification:
    """LLM-generated classification for a single skill."""
    role_id: str
    display_name: str = ""
    category: str = ""
    classification: str = ""  # "planning" | "implementation"
    description: str = ""
    capabilities: List[str] = field(default_factory=list)
    recommended_tools: List[str] = field(default_factory=list)
    compatible_scenarios: List[str] = field(default_factory=list)


@dataclass
class GeneratedScenario:
    """LLM-generated tool scenario for a group of skills."""
    id: str
    name: str
    description: str = ""
    tools: List[str] = field(default_factory=list)
    recommended_roles: List[str] = field(default_factory=list)


def _llm_call(messages: list, timeout: int = 60) -> str:
    """Make a DeepSeek API call and return the content string."""
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY not configured")

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 4096,
        "stream": False,
    }

    url = f"{DEEPSEEK_BASE_URL}/chat/completions"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        logger.error("LLM classifier API error %d: %s", e.code, body[:300])
        raise RuntimeError(f"LLM API error {e.code}") from e


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM response (handles markdown code blocks)."""
    import re
    # Try to find JSON in code blocks
    m = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    if m:
        text = m.group(1)
    # Try direct parse
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        # Try to find first { ... } or [ ... ]
        for start_char, end_char in [('{', '}'), ('[', ']')]:
            start = text.find(start_char)
            end = text.rfind(end_char)
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(text[start:end + 1])
                except json.JSONDecodeError:
                    continue
        raise ValueError(f"Could not extract JSON from LLM response: {text[:200]}")


CLASSIFY_PROMPT = """你是一个 skill 分类专家。分析以下 SKILL.md 的内容，输出 JSON 格式的分类结果。

SKILL 名称: {skill_name}
SKILL 描述: {skill_description}
SKILL 内容摘要（前2000字）:
{skill_content}

请输出以下 JSON 格式（不要输出其他内容）:
```json
{{
  "display_name": "中文显示名称（简短，2-6个字）",
  "category": "分类（如：风险管理/合规审查/市场分析/交易/报告/数据分析/规划/实现/评审/测试/部署/运维）",
  "classification": "planning 或 implementation（规划类=分析、评审、建议、决策；实现类=执行、操作、产出、自动化）",
  "description": "一句话描述该 skill 的功能",
  "capabilities": ["能力标签1", "能力标签2", "能力标签3"],
  "recommended_tools": ["推荐工具1", "推荐工具2"],
  "compatible_scenarios": ["适用场景描述1", "适用场景描述2"]
}}
```"""


def classify_skill(
    skill_id: str,
    skill_name: str,
    skill_description: str,
    skill_content: str,
) -> SkillClassification:
    """Classify a single skill using LLM."""
    content_truncated = skill_content[:2000]

    prompt = CLASSIFY_PROMPT.format(
        skill_name=skill_name,
        skill_description=skill_description,
        skill_content=content_truncated,
    )

    try:
        response = _llm_call([
            {"role": "system", "content": "你是一个专业的 AI skill 分类专家，擅长分析 skill 的用途并进行结构化分类。只输出 JSON。"},
            {"role": "user", "content": prompt},
        ])

        data = _extract_json(response)

        return SkillClassification(
            role_id=skill_id,
            display_name=str(data.get("display_name", skill_name)),
            category=str(data.get("category", "")),
            classification=str(data.get("classification", "implementation")),
            description=str(data.get("description", skill_description)),
            capabilities=list(data.get("capabilities", [])),
            recommended_tools=list(data.get("recommended_tools", [])),
            compatible_scenarios=list(data.get("compatible_scenarios", [])),
        )
    except Exception as e:
        logger.warning("LLM classification failed for %s: %s, using defaults", skill_id, e)
        return SkillClassification(
            role_id=skill_id,
            display_name=skill_name,
            category="other",
            classification="implementation",
            description=skill_description,
        )


def classify_batch(
    skills: List[Dict],
) -> List[SkillClassification]:
    """Classify multiple skills. Each dict needs: skill_id, name, description, content."""
    results = []
    for skill in skills:
        cls = classify_skill(
            skill_id=skill["skill_id"],
            skill_name=skill["name"],
            skill_description=skill.get("description", ""),
            skill_content=skill.get("content", ""),
        )
        results.append(cls)
    return results


SCENARIO_PROMPT = """你是一个多智能体工作流设计专家。以下是一组已分类的专家角色，请为它们设计 1-3 个推荐的工具场景（Tool Scenario）。

角色列表:
{roles_desc}

每个场景应该描述一组角色协作完成特定任务的组合。请输出 JSON 数组格式:
```json
[
  {{
    "id": "scenario-id-kebab-case",
    "name": "场景中文名称",
    "description": "场景描述（一句话说明用途）",
    "tools": ["read", "write", "bash", "websearch"],
    "recommended_roles": ["role_id_1", "role_id_2", "role_id_3"]
  }}
]
```

只输出 JSON 数组，不要其他内容。"""


def generate_scenarios(
    roles: List[Dict],
    tab_name: str = "",
) -> List[GeneratedScenario]:
    """Generate tool scenarios for a group of roles using LLM."""
    if len(roles) < 3:
        return []

    roles_desc = "\n".join(
        f"- {r['role_id']} ({r.get('display_name', r['role_id'])}): "
        f"{r.get('classification', '?')} | {r.get('description', '')}"
        for r in roles
    )

    prompt = SCENARIO_PROMPT.format(roles_desc=roles_desc)

    try:
        response = _llm_call([
            {"role": "system", "content": f"你是多智能体工作流设计专家。为「{tab_name}」领域设计协作场景。只输出 JSON 数组。"},
            {"role": "user", "content": prompt},
        ])

        data = _extract_json(response)
        if not isinstance(data, list):
            data = [data]

        scenarios = []
        for item in data[:3]:  # Max 3 scenarios
            scenarios.append(GeneratedScenario(
                id=str(item.get("id", f"auto-{len(scenarios)}")),
                name=str(item.get("name", "")),
                description=str(item.get("description", "")),
                tools=list(item.get("tools", [])),
                recommended_roles=list(item.get("recommended_roles", [])),
            ))
        return scenarios
    except Exception as e:
        logger.warning("Scenario generation failed: %s", e)
        return []
