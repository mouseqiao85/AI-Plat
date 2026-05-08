import asyncio
import json
import re
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

import structlog
from openai import AsyncOpenAI
import httpx

logger = structlog.get_logger(__name__)

from app.agent.memory_manager import MemoryManager
from app.agent.safety_guard import SafetyGuard
from app.agent.stream_adapter import SSEEventType, format_sse_event
from app.agent.system_prompt import build_system_prompt
from app.agent.tool_registry import ToolRegistry
from app.agent.long_term_memory import UserMemoryManager
from app.agent.worker import Worker, WorkerConfig
from app.core.config import settings

# Maximum characters of a tool result to keep in api_messages context.
# Full result is still saved to DB and emitted to frontend; only the LLM context is capped.
TOOL_RESULT_MAX_CHARS = 2000
from app.models import Conversation
from app.tools.brave_search import BraveSearchTool
from app.tools.skill_tools import (
    ReadSkillReferenceTool,
    RunSkillScriptTool,
    MultiSkillScriptTool,
    MultiSkillReferenceTool,
)
from app.tools.plan_tool import CreatePlanTool

# ── Harness subsystems ─────────────────────────────────────────────────────────
from app.harness.session import get_session_manager, SessionStatus
from app.harness.instructions import get_instruction_builder
from app.harness.state import get_state_manager
from app.harness.scope import get_scope_manager
from app.harness.validator import get_validator, ValidationLevel


class AgentEngine:
    """Core agent engine that orchestrates the tool-use loop via OpenAI-compatible API.

    Integrates the five Harness subsystems:
      - SessionManager  – lifecycle tracking
      - InstructionBuilder – prompt construction
      - StateManager    – per-session state / checkpointing
      - ScopeManager    – tool permission enforcement
      - Validator       – input / output / tool validation
    """

    def __init__(self, db_session, redis_client, skill_name: Optional[str] = None) -> None:
        self.db = db_session
        self.redis = redis_client
        self.registry = ToolRegistry()
        self.safety = SafetyGuard()
        self._skill_context: Optional[Dict[str, Any]] = None

        # Harness singletons
        self._session_mgr = get_session_manager()
        self._instruction_builder = get_instruction_builder()
        self._state_mgr = get_state_manager()
        self._scope_mgr = get_scope_manager()
        self._validator = get_validator(ValidationLevel.NORMAL)

        # Attach Redis to StateManager so checkpoints are persisted cross-process
        if redis_client is not None:
            self._state_mgr.attach_redis(redis_client)

        # Build OpenAI client with optional custom header
        default_headers = {}
        if settings.LLM_CUSTOM_HEADER:
            default_headers["comate_custom_header"] = settings.LLM_CUSTOM_HEADER

        self.client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
            default_headers=default_headers,
            timeout=httpx.Timeout(
                connect=10.0,
                read=float(settings.LLM_TIMEOUT),
                write=30.0,
                pool=10.0,
            ),
        )
        self._register_tools(skill_name=skill_name)

    # ------------------------------------------------------------------ #
    # Tool registration
    # ------------------------------------------------------------------ #

    def _register_tools(self, skill_name: Optional[str] = None) -> None:
        """Register core and skill tool implementations.

        Core tools are always registered. If skill_name is given, only that
        skill's tools are loaded; otherwise all enabled skills are loaded.
        """
        from app.skill import get_skill_manager

        # Core tools — always available
        core_tools = [
            BraveSearchTool(),
            CreatePlanTool(),
        ]
        for tool in core_tools:
            self.registry.register(tool)

        # Skill tools — load only the selected skill (if specified) or all enabled skills
        mgr = get_skill_manager()
        if skill_name:
            info = mgr._skills.get(skill_name)
            tool_descs = info.tools if info and mgr.is_enabled(skill_name) else []

            # Register generic script/reference tools if the skill has scripts/ or references/
            if info and mgr.is_enabled(skill_name):
                config_ok = mgr._check_config(info)
                if not config_ok:
                    logger.warning("skill_config_missing", name=skill_name)
                if info.references_path is not None:
                    self.registry.register(ReadSkillReferenceTool(info.references_path))
                if info.scripts_path is not None:
                    self.registry.register(RunSkillScriptTool(info.scripts_path))
                # Build skill context for system prompt
                self._skill_context = info.to_dict(
                    enabled=True, config_ok=config_ok
                )
        else:
            tool_descs = mgr.get_enabled_tools()
            # Register multi-skill script/reference tools for all enabled skills
            skill_scripts_map = {}
            skill_refs_map = {}
            for sname in mgr.get_enabled_skill_names():
                info = mgr._skills.get(sname)
                if info:
                    if info.scripts_path is not None:
                        skill_scripts_map[sname] = info.scripts_path
                    if info.references_path is not None:
                        skill_refs_map[sname] = info.references_path
            if skill_scripts_map:
                self.registry.register(MultiSkillScriptTool(skill_scripts_map))
            if skill_refs_map:
                self.registry.register(MultiSkillReferenceTool(skill_refs_map))
            # Build a multi-skill context for system prompt injection
            catalog = mgr.get_enabled_skills_catalog()
            if catalog:
                self._skill_context = {
                    "name": "multi_skill",
                    "description": "多个技能可用",
                    "skills_catalog": catalog,
                }

        import importlib
        for tool_desc in tool_descs:
            module_name = tool_desc.get("module", "")
            class_name = tool_desc.get("class", "")
            tool_name = tool_desc.get("name", "")
            if not module_name or not class_name:
                continue
            try:
                mod = importlib.import_module(module_name)
                cls = getattr(mod, class_name)
                tool_instance = cls()
                self.registry.register(tool_instance)
                logger.info("skill_tool_registered", tool=tool_name)
            except Exception as exc:
                logger.warning(
                    "skill_tool_load_failed",
                    tool=tool_name,
                    module=module_name,
                    error=str(exc),
                )

    # ------------------------------------------------------------------ #
    # Main entry point
    # ------------------------------------------------------------------ #

    async def run(
        self,
        user: Any,
        message: str,
        conversation_id: Optional[int] = None,
        provider_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Execute the agent tool-use loop and yield SSE event strings.

        Steps:
        1. Harness Validator: input validation
        2. Harness Session: create & activate session
        3. Harness State: initialise AgentState
        4. Get / create conversation + load history
        5. Harness Instructions: build system prompt
        6. Call LLM API (stream=True, tools=registry.get_schemas())
        7. When finish_reason=="tool_calls":
           - Harness Scope: check tool permission
           - Execute each tool
           - Append results to messages
           - Loop back to step 6
        8. When finish_reason=="stop":
           - Harness Validator: output validation + auto-rewrite
           - Emit DONE event
        9. Harness Session: end session
        """
        user_id = getattr(user, "id", 0)
        user_tier = getattr(user, "membership_tier", "free") or "free"

        # ── Slash command: /skill-name auto-activation ─────────────────
        # If user message starts with /skill-name, dynamically activate that skill
        message = self._handle_slash_skill(message)

        # ── Resolve provider-specific client and model ────────────────
        chat_client = self.client
        chat_model = settings.LLM_MODEL

        if provider_id and provider_id != "default":
            from app.core.config import get_llm_providers
            providers = get_llm_providers()
            provider = next((p for p in providers if p["id"] == provider_id), None)
            if provider:
                default_headers: Dict[str, str] = {}
                if provider.get("custom_header"):
                    default_headers["comate_custom_header"] = provider["custom_header"]
                chat_client = AsyncOpenAI(
                    api_key=provider["api_key"],
                    base_url=provider["base_url"],
                    default_headers=default_headers or None,
                    timeout=httpx.Timeout(
                        connect=10.0,
                        read=float(settings.LLM_TIMEOUT),
                        write=30.0,
                        pool=10.0,
                    ),
                )
                if model and model in provider.get("models", []):
                    chat_model = model
                elif provider.get("models"):
                    chat_model = provider["models"][0]
        elif model:
            chat_model = model

        # Detect DeepSeek provider for reasoning/thinking support
        is_deepseek = provider_id == "deepseek" or "deepseek" in (chat_model or "").lower()

        # Step 1: Input validation via Harness Validator
        input_result = self._validator.validate_input(message)
        if not input_result.passed:
            reason_str = "; ".join(input_result.issues)
            yield format_sse_event(SSEEventType.ERROR, {"message": reason_str})
            yield format_sse_event(SSEEventType.DONE, {"stop_reason": "rejected"})
            return

        # ── Skill dependency notice ─────────────────────────────────────
        # Emit a NOTICE event if the active skill has tools with required/optional config
        # Skip for multi_skill context (catalog already injected in system prompt)
        if self._skill_context and self._skill_context.get("name") != "multi_skill":
            skill_name_ctx = self._skill_context.get("name", "")
            requires = self._skill_context.get("requires_config", [])
            optional = self._skill_context.get("optional_config", [])
            tools_list = self._skill_context.get("tools", [])
            deps_list = self._skill_context.get("dependencies", [])
            if requires or optional or tools_list:
                from app.skill import get_skill_manager as _get_mgr
                _mgr = _get_mgr()
                # Detect which required keys are actually missing from env
                missing = [k for k in requires if not getattr(settings, k, "")]
                yield format_sse_event(SSEEventType.NOTICE, {
                    "skill": skill_name_ctx,
                    "tools": [t.get("name") for t in tools_list if t.get("name")],
                    "requires": requires,
                    "optional": optional,
                    "dependencies": deps_list,
                    "missing": missing,
                    "config_ok": not missing,
                })

        # Step 2: Session lifecycle
        try:
            session = self._session_mgr.create_session(
                user_id=user_id,
                metadata={"skill_name": self._skill_context and self._skill_context.get("name")},
            )
            session.activate()
        except RuntimeError as exc:
            yield format_sse_event(SSEEventType.ERROR, {"message": str(exc)})
            yield format_sse_event(SSEEventType.DONE, {"stop_reason": "rejected"})
            return

        # Step 3: AgentState
        skill_name = self._skill_context.get("name") if self._skill_context else None
        agent_state = self._state_mgr.create(
            session_id=session.session_id,
            user_id=user_id,
            user_tier=user_tier,
            skill_name=skill_name,
        )
        agent_state.current_task = message
        agent_state.add_message("user", message)

        # Step 4a: Load long-term user profile from Redis
        user_memory_mgr = UserMemoryManager(self.redis, self.client, settings.LLM_MODEL)
        user_profile = await user_memory_mgr.load_profile(user_id)
        profile_str = user_memory_mgr.format_for_prompt(user_profile)

        # Step 4b: Get or create conversation + load history (compress first if needed)
        conversation = await self._get_or_create_conversation(user, conversation_id)
        conv_id = conversation.id if conversation else 0

        # Emit conversation_id so the frontend can track the active conversation
        if conv_id:
            yield format_sse_event(SSEEventType.CONVERSATION_ID, {"conversation_id": conv_id})

        # Load history via MemoryManager
        history = []
        memory = None
        if conv_id:
            try:
                memory = MemoryManager(self.db, conv_id)
                await memory.compress_if_needed(self.client, settings.LLM_MODEL)
                history = await memory.load_history()
                is_new = len(history) == 0
                await memory.save_message(role="user", content=message)
                # Set title from first message for new conversations
                if is_new:
                    title = await self._set_title_if_new(conv_id, message)
                    if title:
                        yield format_sse_event(SSEEventType.CONVERSATION_TITLE, {
                            "conversation_id": conv_id, "title": title,
                        })
                # Touch Conversation.updated_at so the list stays sorted by activity
                await self._touch_conversation(conv_id)
            except Exception:
                logger.warning("memory_init_failed", conv_id=conv_id, exc_info=True)
                # Don't set memory=None — keep trying each iteration
        else:
            memory = None

        # Step 5: Build system prompt via Harness InstructionBuilder
        skill_desc = ""
        if self._skill_context:
            if self._skill_context.get("name") == "multi_skill":
                # Format multi-skill catalog for prompt
                # IMPORTANT: Only advertise tools that are ACTUALLY registered in the ToolRegistry.
                # Skill metadata tools (browser_init, etc.) without module/class implementations
                # must NOT be listed, otherwise LLM hallucinates tool_calls that cannot execute.
                registered_tool_names = set(self.registry.list_tools())
                catalog = self._skill_context.get("skills_catalog", [])
                parts = []
                for skill in catalog:
                    # Filter: only show tools that have a real implementation (module+class)
                    # or are the generic script/reference tools
                    real_tools = [
                        t for t in skill.get("tools", [])
                        if t.get("name") in registered_tool_names
                    ]
                    skill_has_scripts = skill.get("scripts_path") is not None
                    skill_has_refs = len(skill.get("references", [])) > 0

                    # Build tool usage guidance for this skill
                    tool_lines = ""
                    if real_tools:
                        tool_lines = "\n".join(
                            f"  - {t['name']}: {t['description']}"
                            for t in real_tools
                        )
                    if skill_has_scripts:
                        tool_lines += f"\n  - 通过 run_skill_script(skill_name=\"{skill['name']}\", ...) 执行脚本"
                    if skill_has_refs:
                        tool_lines += f"\n  - 通过 read_skill_reference(skill_name=\"{skill['name']}\", ...) 读取文档"

                    if not tool_lines.strip():
                        # Skip skills with no usable tools
                        continue

                    parts.append(
                        f"技能: {skill['name']}\n"
                        f"说明: {skill['description']}\n"
                        f"关键词: {', '.join(skill.get('keywords', []))}\n"
                        f"使用方式:\n{tool_lines}"
                    )
                skill_desc = (
                    "当前有多个技能可用。注意：只能调用已注册的工具（run_skill_script、read_skill_reference、web_search 等），"
                    "不要调用技能文档中描述但未注册的工具名。\n\n"
                    + "\n\n".join(parts)
                )
            else:
                skill_desc = self._skill_context.get("skill_md_content", "")
        system_prompt = self._instruction_builder.build_full_system(
            user_tier=user_tier,
            skill_description=skill_desc,
            user_profile_str=profile_str,
        )
        # Fall back to legacy builder if instruction builder returns empty
        if not system_prompt:
            system_prompt = build_system_prompt(
                user_tier=user_tier,
                tool_descriptions=self.registry.get_schemas(),
                skill_context=self._skill_context,
            )
        agent_state.system_prompt = system_prompt

        # Prepare messages list for the API (OpenAI format)
        # System prompt goes first, then history, then current user message
        api_messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        api_messages.extend(history)
        api_messages.append({"role": "user", "content": message})

        # Steps 5-7: Tool-use loop
        max_iterations = settings.MAX_TOOL_ITERATIONS
        _llm_retries = 0  # track LLM call retry count (max 3)
        _iteration_tool_types: List[str] = []  # dominant tool type per iteration for repetition detection
        _iteration_tool_failed: List[bool] = []  # whether tool failed in each iteration

        for iteration in range(max_iterations):
            logger.info("iteration_start", iteration=iteration, max_iterations=max_iterations, messages_count=len(api_messages))

            # ── Repetition guard: detect stuck loops and intervene ──────────────
            # Strategy:
            #   - If same tool FAILED N consecutive times → hard stop with error
            #   - If same tool succeeded N consecutive times → soft hint to synthesize
            _FAIL_THRESHOLD = 3   # consecutive failures on same tool → hard stop
            _SUCCESS_THRESHOLD = 8  # consecutive successes on same tool → suggest synthesis
            if _iteration_tool_types:
                # Check consecutive failures first (higher priority)
                if len(_iteration_tool_failed) >= _FAIL_THRESHOLD:
                    last_fails = _iteration_tool_failed[-_FAIL_THRESHOLD:]
                    last_tools = _iteration_tool_types[-_FAIL_THRESHOLD:]
                    if all(last_fails) and len(set(last_tools)) == 1:
                        failed_tool = last_tools[0]
                        logger.warning("repetition_guard_fail_stop", tool=failed_tool, consecutive_failures=_FAIL_THRESHOLD)
                        api_messages.append({
                            "role": "system",
                            "content": (
                                f"工具 {failed_tool} 已连续失败 {_FAIL_THRESHOLD} 次，"
                                f"停止重试。请直接告知用户该工具当前不可用，并基于已有信息回答。"
                                f"不要再调用 {failed_tool}。"
                            ),
                        })
                # Check consecutive successes (soft hint)
                elif len(_iteration_tool_types) >= _SUCCESS_THRESHOLD:
                    last_n = _iteration_tool_types[-_SUCCESS_THRESHOLD:]
                    if len(set(last_n)) == 1:
                        logger.warning("repetition_guard_triggered", tool=last_n[0], iterations=_SUCCESS_THRESHOLD)
                        api_messages.append({
                            "role": "system",
                            "content": f"你已经连续{_SUCCESS_THRESHOLD}轮调用 {last_n[0]} 工具。信息已经足够充分，请停止调用工具，基于已有信息直接给出完整回答。",
                        })

            # ── Checkpoint before each LLM call ──────────────────────────
            await self._state_mgr.checkpoint_async(session.session_id)

            # ── Mid-session auto-compact check ───────────────────────────
            if memory:
                try:
                    compact_needed, compact_summary = await memory.compact_if_exceeds_tokens(
                        api_messages, self.client, settings.LLM_MODEL,
                    )
                    if compact_needed:
                        yield format_sse_event(SSEEventType.COMPACT_START, {
                            "message": "正在压缩对话历史以释放空间..."
                        })
                        yield format_sse_event(SSEEventType.COMPACT_DONE, {
                            "message": "对话历史已压缩",
                            "summary_preview": (compact_summary or "")[:100],
                        })
                except Exception as exc:
                    logger.warning("mid_session_compact_error", error=str(exc))

            # Step 5: Call LLM API
            assistant_text = ""
            reasoning_content = ""
            tool_calls: List[Dict[str, Any]] = []
            finish_reason = None

            try:
                create_kwargs: Dict[str, Any] = dict(
                    model=chat_model,
                    max_tokens=20000,
                    messages=api_messages,
                    tools=self.registry.get_schemas(),
                    stream=True,
                )
                if is_deepseek:
                    create_kwargs["extra_body"] = {"thinking": {"type": "enabled"}}

                stream = await chat_client.chat.completions.create(**create_kwargs)  # type: ignore[arg-type]

                async for chunk in stream:
                    if not chunk.choices:
                        continue

                    delta = chunk.choices[0].delta
                    choice_finish = chunk.choices[0].finish_reason

                    # Accumulate reasoning/thinking content (DeepSeek)
                    if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                        reasoning_content += delta.reasoning_content
                        yield format_sse_event(SSEEventType.THINKING, {"text": delta.reasoning_content})

                    # Accumulate text content
                    if delta.content:
                        assistant_text += delta.content
                        yield format_sse_event(SSEEventType.TEXT, {"text": delta.content})

                    # Accumulate tool calls
                    if delta.tool_calls:
                        for tc_delta in delta.tool_calls:
                            idx = tc_delta.index
                            # Extend list if needed
                            while len(tool_calls) <= idx:
                                tool_calls.append({"id": "", "name": "", "arguments": ""})

                            if tc_delta.id:
                                tool_calls[idx]["id"] = tc_delta.id
                            if tc_delta.function and tc_delta.function.name:
                                tool_calls[idx]["name"] = tc_delta.function.name
                            if tc_delta.function and tc_delta.function.arguments:
                                tool_calls[idx]["arguments"] += tc_delta.function.arguments

                    # Track finish reason
                    if choice_finish:
                        finish_reason = choice_finish

                # LLM call succeeded — reset retry counter
                _llm_retries = 0
                logger.debug(
                    "llm_call_ok",
                    iteration=iteration,
                    finish_reason=finish_reason,
                    has_tool_calls=bool(tool_calls),
                    text_len=len(assistant_text),
                )

            except Exception as exc:
                err_msg = str(exc)
                # ── Retry up to 3 times with checkpoint-restore ──────────
                _llm_retries += 1
                if _llm_retries <= 3:
                    restored = self._state_mgr.restore(session.session_id)
                    if restored is None:
                        restored = await self._state_mgr.restore_from_redis(session.session_id)
                    logger.warning(
                        "llm_error_retrying",
                        session_id=session.session_id,
                        attempt=_llm_retries,
                        error=err_msg,
                    )
                    yield format_sse_event(SSEEventType.NOTICE, {
                        "type": "retry",
                        "message": f"网络波动，正在自动重试（{_llm_retries}/3）…",
                    })
                    await asyncio.sleep(1.5 * _llm_retries)
                    continue  # retry this iteration

                # All 3 retries exhausted — graceful degradation:
                # Try to generate a summary response from context so far
                logger.error(
                    "llm_retries_exhausted",
                    session_id=session.session_id,
                    error=err_msg,
                )
                degraded_text = "抱歉，模型服务暂时不稳定，已重试3次仍未成功。"
                # If we have any tool results, summarize what we have
                if agent_state.tool_results:
                    tool_names = ", ".join(agent_state.tool_results.keys())
                    degraded_text += f" 已完成的工具调用：{tool_names}。请稍后重试以获取完整回答。"
                else:
                    degraded_text += " 请稍后重试。"

                yield format_sse_event(SSEEventType.TEXT, {"text": degraded_text})
                if memory:
                    try:
                        await memory.save_message(role="assistant", content=degraded_text)
                    except Exception:
                        pass
                self._session_mgr.close_session(session.session_id)
                await self._state_mgr.end_async(session.session_id)
                yield format_sse_event(SSEEventType.DONE, {"stop_reason": "degraded"})
                return

            # Build the assistant message for the API
            # DeepSeek: content must be empty string (not None) when tool_calls present
            if is_deepseek and tool_calls:
                assistant_msg: Dict[str, Any] = {"role": "assistant", "content": assistant_text or ""}
            else:
                assistant_msg: Dict[str, Any] = {"role": "assistant", "content": assistant_text or None}
            if reasoning_content:
                assistant_msg["reasoning_content"] = reasoning_content
            if tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": tc["arguments"],
                        },
                    }
                    for tc in tool_calls
                ]

            # Save assistant message
            if memory:
                try:
                    await memory.save_message(
                        role="assistant",
                        content=assistant_text,
                        tool_calls=tool_calls if tool_calls else None,
                        reasoning_content=reasoning_content or None,
                    )
                except Exception:
                    logger.warning("save_assistant_msg_failed", exc_info=True)

            # Append assistant turn to API messages
            api_messages.append(assistant_msg)

            # Step 7: Handle tool_calls
            # Note: Some LLM APIs (especially behind gateways) may return tool_calls
            # without setting finish_reason to "tool_calls". We treat any response
            # with non-empty tool_calls as a tool-call turn regardless of finish_reason.
            if tool_calls:
                # ── Degradation check: on final iteration, force a final text response ─────
                if iteration >= max_iterations - 1:
                    yield format_sse_event(SSEEventType.NOTICE, {
                        "type": "degradation",
                        "message": "正在整合信息生成回答...",
                        "iteration": iteration + 1,
                        "max_iterations": max_iterations,
                    })
                    # Make ONE final LLM call WITHOUT tools to force a text response
                    api_messages.append({
                        "role": "system",
                        "content": (
                            "请直接基于当前已有的工具执行结果和对话历史给出最佳回答。"
                            "不要再调用任何工具，不要提及任何系统限制或错误，直接回答用户的问题。"
                        ),
                    })
                    try:
                        final_stream = await chat_client.chat.completions.create(
                            model=chat_model,
                            messages=api_messages,
                            stream=True,
                            # No tools parameter — forces text-only response
                        )
                        degraded_text = ""
                        async for chunk in final_stream:
                            if not chunk.choices:
                                continue
                            delta = chunk.choices[0].delta
                            if delta.content:
                                degraded_text += delta.content
                                yield format_sse_event(SSEEventType.TEXT, {"text": delta.content})
                        # Save and finalize
                        if memory and degraded_text:
                            try:
                                await memory.save_message(role="assistant", content=degraded_text)
                            except Exception:
                                pass
                        session.turn_count += 1
                    except Exception as exc:
                        logger.error("degradation_final_call_failed", error=str(exc))
                        fallback = "抱歉，处理过程中遇到问题，请重新提问或稍后重试。"
                        yield format_sse_event(SSEEventType.TEXT, {"text": fallback})
                    break  # Exit the loop — we're done

                # Emit thinking event
                yield format_sse_event(SSEEventType.THINKING, {"status": "executing_tools"})
                session.mark_waiting()

                # Execute each tool and collect results
                _iter_tool_statuses: List[str] = []  # track status of each tool call in this iteration
                for tc in tool_calls:
                    tool_name = tc["name"]
                    tool_id = tc["id"]
                    try:
                        tool_input = json.loads(tc["arguments"]) if tc["arguments"] else {}
                    except json.JSONDecodeError:
                        tool_input = {}

                    # ── Emit tool_call START event (before execution) ──────
                    yield format_sse_event(SSEEventType.TOOL_CALL, {
                        "tool_use_id": tool_id,
                        "name": tool_name,
                        "status": "running",
                        "tool_args": tool_input,
                    })

                    # ── Harness Scope: permission check ──────────────────
                    scope_ok, scope_reason = self._scope_mgr.check_tool(tool_name, user_tier)
                    if not scope_ok:
                        result_str = f"权限不足，无法调用工具 {tool_name}：{scope_reason}"
                        yield format_sse_event(SSEEventType.TOOL_CALL, {
                            "tool_use_id": tool_id,
                            "name": tool_name,
                            "status": "blocked",
                            "reason": scope_reason,
                        })
                        api_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "content": result_str,
                        })
                        _iter_tool_statuses.append("blocked")
                        continue

                    # ── Harness Scope: rate limit check ────────────────────
                    rate_ok, rate_reason = self._scope_mgr.check_rate_limit(tool_name, user_id, user_tier)
                    if not rate_ok:
                        result_str = f"调用频率超限：{rate_reason}"
                        yield format_sse_event(SSEEventType.TOOL_CALL, {
                            "tool_use_id": tool_id,
                            "name": tool_name,
                            "status": "blocked",
                            "reason": rate_reason,
                        })
                        api_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "content": result_str,
                        })
                        _iter_tool_statuses.append("blocked")
                        continue

                    # ── Harness Validator: tool params check ──────────────
                    param_result = self._validator.validate_tool(tool_name, tool_input, user_tier)
                    if not param_result.passed:
                        result_str = "参数验证失败：" + "; ".join(param_result.issues)
                        api_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "content": result_str,
                        })
                        _iter_tool_statuses.append("error")
                        continue

                    # ── Plan step tracking: mark as running before execution ──────
                    matching_plan_steps = [
                        s for s in agent_state.plan
                        if s.action == tool_name and s.status == "pending"
                    ]
                    if matching_plan_steps:
                        matching_plan_steps[0].status = "running"
                        yield format_sse_event(SSEEventType.PLAN_STEP_UPDATE, {
                            "plan_id": agent_state.plan_id,
                            "step": matching_plan_steps[0].step,
                            "status": "running",
                        })

                    tool_status = "completed"
                    tool_retry_count = 0
                    max_tool_retries = 3
                    result = None

                    while tool_retry_count <= max_tool_retries:
                        try:
                            result = await asyncio.wait_for(
                                self.registry.execute_tool(tool_name, **tool_input),
                                timeout=settings.TOOL_TIMEOUT,
                            )
                            result_str = json.dumps(result, ensure_ascii=False) if not isinstance(result, str) else result
                            agent_state.tool_results[tool_name] = result
                            session.tool_calls += 1
                            tool_status = "completed"
                            # ── Plan step tracking: mark as completed ────────
                            if matching_plan_steps:
                                agent_state.mark_step_done(tool_name, result)
                                yield format_sse_event(SSEEventType.PLAN_STEP_UPDATE, {
                                    "plan_id": agent_state.plan_id,
                                    "step": matching_plan_steps[0].step,
                                    "status": "completed",
                                })
                            break  # success, exit retry loop
                        except KeyError as exc:
                            # Tool not registered — no point retrying
                            result_str = f"工具 {tool_name} 不存在，请检查可用工具列表后重试"
                            tool_status = "error"
                            agent_state.mark_step_failed(tool_name, "not_registered")
                            logger.warning("tool_not_registered", tool=tool_name)
                            break
                        except asyncio.TimeoutError:
                            tool_retry_count += 1
                            if tool_retry_count <= max_tool_retries:
                                logger.warning("tool_timeout_retrying", tool=tool_name, attempt=tool_retry_count)
                                await asyncio.sleep(1)
                                continue
                            result_str = f"工具 {tool_name} 执行超时（{settings.TOOL_TIMEOUT}秒），已重试{max_tool_retries}次仍失败，已跳过"
                            tool_status = "timeout"
                            agent_state.mark_step_failed(tool_name, "timeout")
                            if matching_plan_steps:
                                yield format_sse_event(SSEEventType.PLAN_STEP_UPDATE, {
                                    "plan_id": agent_state.plan_id,
                                    "step": matching_plan_steps[0].step,
                                    "status": "failed",
                                    "error": "timeout",
                                })
                        except Exception as exc:
                            tool_retry_count += 1
                            if tool_retry_count <= max_tool_retries:
                                logger.warning("tool_error_retrying", tool=tool_name, attempt=tool_retry_count, error=str(exc))
                                await asyncio.sleep(1)
                                continue
                            result_str = f"工具 {tool_name} 执行出错（{str(exc)}），已重试{max_tool_retries}次仍失败，请根据现有信息作答"
                            tool_status = "error"
                            agent_state.mark_step_failed(tool_name, str(exc))
                            if matching_plan_steps:
                                yield format_sse_event(SSEEventType.PLAN_STEP_UPDATE, {
                                    "plan_id": agent_state.plan_id,
                                    "step": matching_plan_steps[0].step,
                                    "status": "failed",
                                    "error": str(exc),
                                })

                    # Emit tool_call COMPLETION event (after execution)
                    yield format_sse_event(SSEEventType.TOOL_CALL, {
                        "tool_use_id": tool_id,
                        "name": tool_name,
                        "status": tool_status,
                        "result": result if tool_status == "completed" else None,
                    })

                    # ── create_plan callback: populate AgentState plan + emit PLAN_CREATED ──
                    if tool_name == "create_plan" and isinstance(result, dict) and result.get("plan_created"):
                        import uuid as _uuid
                        plan_id = str(_uuid.uuid4())[:8]
                        agent_state.plan_id = plan_id
                        agent_state.plan.clear()

                        plan_steps_data = []
                        for s in result.get("steps", []):
                            ps = agent_state.add_plan_step(
                                action=s.get("action", ""),
                                description=s.get("description", s.get("action", "")),
                            )
                            plan_steps_data.append({
                                "step": ps.step,
                                "action": ps.action,
                                "description": ps.description,
                                "status": ps.status,
                            })

                        yield format_sse_event(SSEEventType.PLAN_CREATED, {
                            "plan_id": plan_id,
                            "steps": plan_steps_data,
                            "needs_workers": result.get("needs_workers", False),
                        })

                        # ── If needs_workers, orchestrate workers for independent subtasks ──
                        if result.get("needs_workers"):
                            subtasks = result.get("steps", [])
                            worker_summary = ""
                            async for sse_event in self._orchestrate_workers(subtasks, agent_state, chat_client, chat_model):
                                yield sse_event
                                # Extract the summary from the return value (last WORKER_DONE)
                            # _orchestrate_workers returns the summary, but since it's a generator
                            # we need a different approach — collect worker results from agent_state
                            worker_parts = []
                            for wid, winfo in agent_state.child_workers.items():
                                worker_parts.append(f"### {wid}: {winfo['task']}\n状态: {winfo['status']}")
                            if worker_parts:
                                worker_summary = "\n\n".join(worker_parts)
                                # Inject as user message so LLM can synthesize
                                api_messages.append({
                                    "role": "user",
                                    "content": f"[子任务执行结果]\n{worker_summary}\n\n请根据以上子任务结果，综合输出最终答案。",
                                })

                    # Emit card event if result is structured
                    if isinstance(result, dict):
                        yield format_sse_event(SSEEventType.CARD, {
                            "tool_use_id": tool_id,
                            "name": tool_name,
                            "data": result,
                        })

                    # Append tool result message (OpenAI format)
                    # Truncate for LLM context to control token usage;
                    # full result is already emitted to frontend via SSE and saved to DB below.
                    context_content = result_str
                    if len(context_content) > TOOL_RESULT_MAX_CHARS:
                        context_content = context_content[:TOOL_RESULT_MAX_CHARS] + f"\n...[结果已截断，原长{len(result_str)}字符]"
                    # If tool failed, append a hint encouraging LLM to fix and retry
                    if tool_status in ("error", "timeout"):
                        context_content += "\n\n[系统提示：该工具调用失败，请分析错误原因，修正参数后重试，或使用其他方式回答用户问题。]"
                    api_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": context_content,
                    })

                    # Save tool result message
                    if memory:
                        try:
                            await memory.save_message(
                                role="tool",
                                content=result_str,
                                tool_call_id=tool_id,
                            )
                        except Exception:
                            pass

                    _iter_tool_statuses.append(tool_status)

                # Continue the loop to call LLM again with tool results
                # Track dominant tool type for this iteration (repetition detection)
                tool_names_this_iter = [tc["name"] for tc in tool_calls]
                dominant_tool = max(set(tool_names_this_iter), key=tool_names_this_iter.count)
                _iteration_tool_types.append(dominant_tool)
                # Determine if this iteration's dominant tool failed
                _iter_all_failed = all(s in ("error", "timeout", "blocked") for s in _iter_tool_statuses)
                _iteration_tool_failed.append(_iter_all_failed)
                session.resume_from_waiting()
                await self._state_mgr.checkpoint_async(session.session_id)
                logger.info("tool_calls_done_continuing", iteration=iteration, tool_count=len(tool_calls))
                continue

            # Step 8: End turn – Harness Validator output check
            # Handle finish_reason="length" (max_tokens hit): treat partial text as response
            if finish_reason == "length":
                logger.warning("llm_finish_length", iteration=iteration, text_len=len(assistant_text), tool_calls_count=len(tool_calls))
                # If we have partial tool_calls but they're incomplete, discard them
                # and use whatever text was produced
                if tool_calls and not assistant_text.strip():
                    # Truncated mid-tool-call with no text — retry once
                    if api_messages and api_messages[-1].get("role") == "assistant":
                        api_messages.pop()
                    continue
                # Otherwise, we have usable text — fall through to finalize it
                # Clear incomplete tool_calls so the response is treated as text-only
                tool_calls = []

            if finish_reason == "stop" or finish_reason is None or finish_reason == "length":
                # Guard: if LLM returned empty response (no text, no tool_calls),
                # retry instead of terminating with blank output
                if not assistant_text.strip() and not tool_calls:
                    _llm_retries += 1
                    if _llm_retries <= 3:
                        logger.warning("llm_empty_response_retrying", attempt=_llm_retries)
                        # Remove the empty assistant message we appended
                        if api_messages and api_messages[-1].get("role") == "assistant":
                            api_messages.pop()
                        await asyncio.sleep(1)
                        continue
                    # All retries exhausted with empty response — degrade
                    assistant_text = "抱歉，模型返回了空响应，请重试。"
                    yield format_sse_event(SSEEventType.TEXT, {"text": assistant_text})

                session.turn_count += 1
                agent_state.add_message("assistant", assistant_text)

                # Harness Validator: output validation + auto-rewrite
                out_result = self._validator.validate_output(assistant_text, auto_rewrite=True)
                final_text = out_result.rewritten if out_result.rewritten else assistant_text

            # Fallback: legacy safety guard check
                is_safe, modified_text, _ = self.safety.check_output(final_text)
                if modified_text != final_text:
                    final_text = modified_text

                # Emit any delta text (disclaimer / rewrites)
                if final_text != assistant_text:
                    delta_text = final_text[len(assistant_text):]
                    if delta_text:
                        yield format_sse_event(SSEEventType.TEXT, {"text": delta_text})

                # ── Check if output should be saved as a downloadable file ────
                if self._should_generate_file(final_text):
                    try:
                        from app.services.file_storage import save_generated_file

                        # Determine content type and filename hint
                        content_type = "text/plain"
                        filename_hint = "report.txt"
                        if re.search(r"<(!DOCTYPE\s+)?html", final_text, re.IGNORECASE):
                            content_type = "text/html"
                            filename_hint = "report.html"
                        elif re.search(r"```html\s+", final_text):
                            # Extract HTML from code block for cleaner download
                            html_match = re.search(r"```html\s+(.*?)```", final_text, re.DOTALL)
                            if html_match:
                                final_text_for_file = html_match.group(1).strip()
                                content_type = "text/html"
                                filename_hint = "report.html"
                            else:
                                final_text_for_file = final_text
                                content_type = "text/markdown"
                                filename_hint = "report.md"
                        else:
                            content_type = "text/markdown"
                            filename_hint = "report.md"
                            final_text_for_file = final_text

                        file_info = await save_generated_file(
                            content=final_text_for_file,
                            filename_hint=filename_hint,
                            content_type=content_type,
                            redis_client=self.redis,
                        )
                        yield format_sse_event(SSEEventType.FILE_DOWNLOAD, file_info)

                        # Persist file_downloads in the last assistant message row
                        if memory:
                            try:
                                import json as _json
                                from sqlalchemy import select as _sa_select
                                from app.models.message import Message as _Msg
                                _fd_list = [file_info]
                                # Find the last assistant message in this conversation
                                _last_stmt = (
                                    _sa_select(_Msg.id)
                                    .where(_Msg.conversation_id == conv_id, _Msg.role == "assistant")
                                    .order_by(_Msg.id.desc())
                                    .limit(1)
                                )
                                _last_result = await self.db.execute(_last_stmt)
                                _last_msg_id = _last_result.scalar()
                                if _last_msg_id:
                                    from sqlalchemy import update as _sa_update
                                    await self.db.execute(
                                        _sa_update(_Msg)
                                        .where(_Msg.id == _last_msg_id)
                                        .values(file_downloads=_json.dumps(_fd_list, ensure_ascii=False))
                                    )
                            except Exception:
                                logger.debug("file_downloads_persist_failed", exc_info=True)

                        # Append a brief hint in the chat
                        hint = "\n\n---\n📄 完整报告已生成，请点击下方卡片下载"
                        yield format_sse_event(SSEEventType.TEXT, {"text": hint})
                    except Exception as exc:
                        logger.warning("file_download_save_failed", error=str(exc))

                # ── Schedule async long-term memory update ──────────────
                import asyncio as _asyncio
                task = _asyncio.create_task(user_memory_mgr.update_profile(
                    user_id=user_id,
                    conversation_messages=api_messages,
                    tools_used=list(agent_state.tool_results.keys()),
                ))
                # Track for graceful shutdown
                from app.main import _background_tasks
                _background_tasks.add(task)
                task.add_done_callback(_background_tasks.discard)

                # ── Write back runtime tool usage to skill state ────────
                if self._skill_context:
                    _skill_name_wb = self._skill_context.get("name", "")
                    _tools_called = list(agent_state.tool_results.keys())
                    _requires = self._skill_context.get("requires_config", [])
                    _missing_wb = [k for k in _requires if not getattr(settings, k, "")]
                    try:
                        from app.skill import get_skill_manager as _get_mgr_wb
                        _get_mgr_wb().update_skill_runtime_info(
                            name=_skill_name_wb,
                            tools_called=_tools_called,
                            missing_deps=_missing_wb if _missing_wb else None,
                        )
                    except Exception:
                        pass

                # Commit before DONE so the conversation & messages are visible to
                # the frontend's immediate GET /conversations/ refresh call.
                try:
                    await self.db.commit()
                except Exception:
                    logger.warning("db_commit_failed", exc_info=True)
                self._session_mgr.close_session(session.session_id)
                await self._state_mgr.end_async(session.session_id)

                yield format_sse_event(SSEEventType.DONE, {"stop_reason": "end_turn"})
                return

        # If we hit max iterations, emit a done event
        import asyncio as _asyncio
        task = _asyncio.create_task(user_memory_mgr.update_profile(
            user_id=user_id,
            conversation_messages=api_messages,
            tools_used=list(agent_state.tool_results.keys()),
        ))
        from app.main import _background_tasks
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
        try:
            await self.db.commit()
        except Exception:
            logger.warning("db_commit_failed_max_iter", exc_info=True)
        # Clean up session & state
        self._session_mgr.close_session(session.session_id)
        await self._state_mgr.end_async(session.session_id)

        yield format_sse_event(SSEEventType.DONE, {"stop_reason": "max_iterations"})

    # ------------------------------------------------------------------ #
    # Worker orchestration
    # ------------------------------------------------------------------ #

    async def _orchestrate_workers(
        self,
        subtasks: List[Dict[str, Any]],
        agent_state: Any,
        chat_client: AsyncOpenAI,
        chat_model: str,
    ) -> AsyncGenerator[str, None]:
        """Create and run workers for independent subtasks, yielding SSE events.

        Results are stored in agent_state.child_workers for the caller to use.
        MVP: sequential execution. Can be upgraded to asyncio.gather for parallelism.
        """
        for i, task in enumerate(subtasks):
            worker_id = f"worker-{i + 1}"
            task_desc = task.get("description", task.get("action", f"子任务{i + 1}"))
            config = WorkerConfig(worker_id=worker_id, task=task_desc)

            yield format_sse_event(SSEEventType.WORKER_STARTED, {
                "worker_id": worker_id,
                "task": task_desc[:100],
            })

            # Track in agent_state
            agent_state.child_workers[worker_id] = {
                "task": task_desc,
                "status": "running",
            }

            worker = Worker(config, chat_client, self.registry, self.db, self.redis, model=chat_model)
            try:
                async for progress in worker.run():
                    yield format_sse_event(SSEEventType.WORKER_PROGRESS, {
                        "worker_id": worker_id,
                        **progress,
                    })
            except Exception as exc:
                agent_state.child_workers[worker_id]["status"] = "failed"
                # Sync plan step status
                matching_steps = [
                    s for s in agent_state.plan
                    if s.status == "pending" and (
                        s.action == task.get("action", "") or s.description == task_desc
                    )
                ]
                if matching_steps:
                    step_obj = matching_steps[0]
                    step_obj.status = "failed"
                    yield format_sse_event(SSEEventType.PLAN_STEP_UPDATE, {
                        "plan_id": agent_state.plan_id,
                        "step": step_obj.step,
                        "status": "failed",
                        "error": str(exc),
                    })
                yield format_sse_event(SSEEventType.WORKER_DONE, {
                    "worker_id": worker_id,
                    "status": "failed",
                    "error": str(exc),
                })
                continue

            # Worker completed
            wresult = worker.result
            if wresult:
                agent_state.child_workers[worker_id]["status"] = wresult.status
                agent_state.child_workers[worker_id]["content"] = wresult.content

            # Sync plan step status with worker result
            worker_status = wresult.status if wresult else "completed"
            matching_steps = [
                s for s in agent_state.plan
                if s.status == "pending" and (
                    s.action == task.get("action", "") or s.description == task_desc
                )
            ]
            if matching_steps:
                step_obj = matching_steps[0]
                step_obj.status = "completed" if worker_status == "completed" else "failed"
                yield format_sse_event(SSEEventType.PLAN_STEP_UPDATE, {
                    "plan_id": agent_state.plan_id,
                    "step": step_obj.step,
                    "status": step_obj.status,
                })

            yield format_sse_event(SSEEventType.WORKER_DONE, {
                "worker_id": worker_id,
                "status": worker_status,
                "result_preview": (wresult.content or "")[:200] if wresult else "",
            })

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _handle_slash_skill(self, message: str) -> str:
        """Detect /skill-name prefix and dynamically activate the skill.

        If the message starts with /some-skill-name, switches the engine's
        skill context to that skill (registering its tools/instructions).
        Returns the message with the slash command stripped.
        """
        import re
        match = re.match(r"^/([a-zA-Z0-9_-]+)\s*(.*)", message, re.DOTALL)
        if not match:
            return message

        candidate_name = match.group(1)
        rest_message = match.group(2).strip()

        from app.skill import get_skill_manager
        mgr = get_skill_manager()
        if not mgr._loaded:
            mgr.discover()

        # Check if this is a valid, enabled skill
        info = mgr._skills.get(candidate_name)
        if info is None or not mgr._enabled.get(candidate_name, False):
            return message  # Not a known skill — pass through as normal message

        # Activate the skill: register its tools and build context
        config_ok = mgr._check_config(info)
        if info.scripts_path is not None:
            from app.tools.skill_tools import RunSkillScriptTool
            self.registry.register(RunSkillScriptTool(info.scripts_path))
        if info.references_path is not None:
            from app.tools.skill_tools import ReadSkillReferenceTool
            self.registry.register(ReadSkillReferenceTool(info.references_path))

        self._skill_context = info.to_dict(enabled=True, config_ok=config_ok)
        logger.info("slash_skill_activated", skill=candidate_name)

        # If no message body after the slash command, use a default prompt
        if not rest_message:
            rest_message = f"请使用 {candidate_name} 技能帮我完成操作。"

        return rest_message

    @staticmethod
    def _should_generate_file(text: str) -> bool:
        """Check if the output is long enough / contains HTML to warrant file download."""
        if len(text) > settings.FILE_DOWNLOAD_THRESHOLD:
            return True
        # Check for ```html code block > 500 chars
        html_block_match = re.search(r"```html\s+(.*?)```", text, re.DOTALL)
        if html_block_match and len(html_block_match.group(1)) > 500:
            return True
        # Check for <html / <!DOCTYPE html tags with substantial content
        if re.search(r"<(!DOCTYPE\s+)?html", text, re.IGNORECASE) and len(text) > 500:
            return True
        return False

    async def _get_or_create_conversation(
        self, user: Any, conversation_id: Optional[int]
    ) -> Optional[Conversation]:
        """Retrieve an existing conversation or create a new one. Returns None if DB unavailable."""
        try:
            from sqlalchemy import select

            if conversation_id:
                stmt = select(Conversation).where(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user.id,
                )
                result = await self.db.execute(stmt)
                conv = result.scalar_one_or_none()
                if conv:
                    return conv

            # Create new conversation
            conv = Conversation(user_id=user.id, title="新对话")
            self.db.add(conv)
            await self.db.flush()
            return conv
        except Exception:
            return None

    async def _touch_conversation(self, conv_id: int) -> None:
        """Update Conversation.updated_at so the list stays sorted by latest activity."""
        try:
            from sqlalchemy import update as sa_update
            from datetime import datetime, timezone
            await self.db.execute(
                sa_update(Conversation)
                .where(Conversation.id == conv_id)
                .values(updated_at=datetime.now(timezone.utc))
            )
        except Exception:
            pass

    async def _set_title_if_new(self, conv_id: int, message: str) -> Optional[str]:
        """Set conversation title to the first user message (up to 30 chars). Returns the title."""
        try:
            from sqlalchemy import update as sa_update
            title = message.strip().replace("\n", " ")[:30]
            if len(message.strip()) > 30:
                title += "…"
            await self.db.execute(
                sa_update(Conversation)
                .where(Conversation.id == conv_id)
                .values(title=title)
            )
            return title
        except Exception:
            return None
