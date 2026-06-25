from datetime import datetime
from typing import Any, Dict, List, Optional


def build_system_prompt(
    *,
    user_tier: str = "free",
    current_time: Optional[datetime] = None,
    tool_descriptions: Optional[List[Dict[str, Any]]] = None,
    skill_context: Optional[Dict[str, Any]] = None,
) -> str:
    """Build a dynamic system prompt for the general-purpose agent."""

    if current_time is None:
        current_time = datetime.now()

    time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")

    # ---- Tool descriptions section ----
    tools_section = ""
    if tool_descriptions:
        tool_lines = []
        for td in tool_descriptions:
            func = td.get("function", td)
            name = func.get("name", "unknown")
            desc = func.get("description", "")
            tool_lines.append(f"  - {name}: {desc}")
        tools_section = "\n可用工具：\n" + "\n".join(tool_lines) + "\n"

    # ---- Skill context section ----
    skill_section = ""
    if skill_context:
        skill_name = skill_context.get("name", "")

        if skill_name == "multi_skill":
            # Multi-skill mode: show catalog of available skills
            catalog = skill_context.get("skills_catalog", [])
            if catalog:
                skill_section = "\n\n【可用技能列表】\n"
                skill_section += "用户可能会使用 /技能名 来激活某个技能，或直接描述需求由你判断调用哪个技能的脚本。\n"
                skill_section += "使用 run_skill_script 工具时需指定 skill_name 参数。\n\n"
                for s in catalog:
                    sname = s.get("name", "")
                    sdesc = s.get("description", "")
                    stools = s.get("tools", [])
                    skill_section += f"- **{sname}**：{sdesc}\n"
                    if stools:
                        tool_names = [t.get("name", "") for t in stools if t.get("name")]
                        if tool_names:
                            skill_section += f"  工具：{', '.join(tool_names)}\n"
        else:
            # Single skill mode
            skill_md = skill_context.get("skill_md_content", "")
            references = skill_context.get("references", [])
            scripts_path = skill_context.get("scripts_path")

            skill_section = f"\n\n【当前激活技能：{skill_name}】\n"
            if skill_md:
                skill_section += skill_md + "\n"
            if scripts_path:
                skill_section += f"\n技能代码目录：{scripts_path}\n"
                skill_section += "你可以通过 run_skill_script 工具执行该目录下的脚本完成任务。\n"
            if references:
                skill_section += f"\n技能参考文档（references/目录）：{', '.join(references)}\n"
                skill_section += "调用API前请先用 read_skill_reference 工具读取对应文档了解参数细节。\n"

    prompt = f"""你是一个通用智能助手，能够帮助用户完成各类任务：信息查询、内容创作、代码编写、分析推理、工具调用等。

当前时间：{time_str}
用户等级：{user_tier}
{tools_section}
【回复规范】
- 回答准确、简洁，结构清晰。
- 需要外部信息时主动调用工具，不要凭空编造数据。
- 对于不确定的内容，明确说明不确定性。
- 使用用户的语言回复（中文问题用中文回答）。
{skill_section}"""
    return prompt
