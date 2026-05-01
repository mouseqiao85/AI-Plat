"""DeepResearch skill — multi-round web search + LLM synthesis.

Uses Brave Search for information gathering and BCE (百度千帆) API for analysis.
BCE API is OpenAI-compatible, so we use the openai SDK with a custom base_url.
"""
from __future__ import annotations

import os
import json
import time
from typing import List, Dict, Any

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BCE_BASE_URL = "https://qianfan.baidubce.com/v2"
DEFAULT_MODEL = "ernie-4.5-turbo-128k"

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _brave_search(query: str, count: int = 5, brave_api_key: str = "") -> List[Dict[str, Any]]:
    """Call Brave Search API and return result list."""
    import urllib.request
    import urllib.parse

    key = brave_api_key or os.environ.get("BRAVE_API_KEY", "")
    if not key:
        return [{"title": "搜索不可用（未配置 BRAVE_API_KEY）", "url": "", "description": ""}]

    params = urllib.parse.urlencode({"q": query, "count": count, "text_decorations": False})
    url = f"{BRAVE_SEARCH_URL}?{params}"
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": key,
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            import gzip, io
            raw = resp.read()
            if resp.info().get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            data = json.loads(raw.decode("utf-8"))
            results = data.get("web", {}).get("results", [])
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "description": r.get("description", ""),
                }
                for r in results
            ]
    except Exception as e:
        return [{"title": f"搜索失败: {e}", "url": "", "description": ""}]


def _llm_call(messages: list, bce_api_key: str = "", model: str = DEFAULT_MODEL) -> str:
    """Call BCE / OpenAI-compatible LLM."""
    try:
        from openai import OpenAI
    except ImportError:
        return "[ERROR] openai package not installed. Run: pip install openai"

    api_key = bce_api_key or os.environ.get("BCE_API_KEY", "")
    if not api_key:
        return "[ERROR] BCE_API_KEY 未配置，无法调用 LLM 进行分析。请提供 bce_api_key 参数或设置 BCE_API_KEY 环境变量。"

    client = OpenAI(api_key=api_key, base_url=BCE_BASE_URL)
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.3,
            max_tokens=8192,
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        return f"[LLM ERROR] {e}"


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def _decompose_topic(topic: str, bce_api_key: str) -> List[str]:
    """Use LLM to break topic into sub-questions."""
    prompt = f"""你是一位资深研究分析师。请将以下研究主题分解为 4-6 个关键子问题，用于指导多轮网络搜索研究。
每个子问题应覆盖不同维度（背景现状、核心竞争力、竞争格局、风险挑战、未来趋势等）。

研究主题：{topic}

请直接输出子问题列表，每行一个，不要编号，不要多余说明。"""

    result = _llm_call([{"role": "user", "content": prompt}], bce_api_key=bce_api_key)
    lines = [l.strip().lstrip("•-–·").strip() for l in result.strip().splitlines() if l.strip()]
    # Fallback sub-questions
    if len(lines) < 2:
        lines = [
            f"{topic} 现状与背景",
            f"{topic} 核心竞争力",
            f"{topic} 竞争对手分析",
            f"{topic} 面临的挑战与风险",
            f"{topic} 未来发展趋势",
        ]
    return lines[:6]


def _synthesize_report(topic: str, findings: List[Dict[str, Any]], bce_api_key: str) -> str:
    """Generate final research report from all gathered findings."""
    findings_text = ""
    for i, f in enumerate(findings, 1):
        findings_text += f"\n### 子问题 {i}: {f['question']}\n"
        for r in f["results"]:
            if r["description"]:
                findings_text += f"- **{r['title']}**: {r['description']}\n"
                if r["url"]:
                    findings_text += f"  来源: {r['url']}\n"

    prompt = f"""你是一位专业的研究分析师，请基于以下搜索资料，为主题「{topic}」撰写一份深度研究报告。

## 搜集的资料：
{findings_text}

## 报告要求：
1. 报告结构完整，包含：执行摘要、背景与现状、核心发现（分多节展开）、竞争/行业格局、趋势与展望、结论与建议
2. 每个部分要有实质内容，引用具体数据和事实
3. 客观中立，有深度，避免泛泛而谈
4. 使用 Markdown 格式，标题层级清晰
5. 总字数不少于 2000 字

请直接输出报告正文："""

    return _llm_call([{"role": "user", "content": prompt}], bce_api_key=bce_api_key, model=DEFAULT_MODEL)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_deepresearch(
    topic: str,
    bce_api_key: str = "",
    max_rounds: int = 4,
    results_per_query: int = 5,
    brave_api_key: str = "",
) -> str:
    """Run deep research on a topic.

    Args:
        topic: Research topic (e.g. "百度竞争和未来")
        bce_api_key: BCE API key (overrides BCE_API_KEY env var)
        max_rounds: Max number of search rounds
        results_per_query: Results per search query
        brave_api_key: Brave Search API key (overrides BRAVE_API_KEY env var)

    Returns:
        Markdown research report string
    """
    print(f"[DeepResearch] 开始研究主题: {topic}")
    print(f"[DeepResearch] 步骤 1/3: 分解研究子问题...")

    sub_questions = _decompose_topic(topic, bce_api_key)
    print(f"[DeepResearch] 子问题: {sub_questions}")

    # Limit rounds
    sub_questions = sub_questions[:max_rounds]

    print(f"[DeepResearch] 步骤 2/3: 多轮搜索 ({len(sub_questions)} 轮)...")
    findings = []
    for i, question in enumerate(sub_questions, 1):
        print(f"[DeepResearch]   搜索 {i}/{len(sub_questions)}: {question}")
        results = _brave_search(question, count=results_per_query, brave_api_key=brave_api_key)
        findings.append({"question": question, "results": results})
        time.sleep(0.5)  # Rate limit

    print(f"[DeepResearch] 步骤 3/3: 综合分析，生成报告...")
    report = _synthesize_report(topic, findings, bce_api_key)

    header = f"# {topic} — 深度研究报告\n\n*研究时间: {time.strftime('%Y-%m-%d %H:%M')} | 搜索轮次: {len(sub_questions)}*\n\n---\n\n"
    return header + report
