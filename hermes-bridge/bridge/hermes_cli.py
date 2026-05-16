import os
import re
import json
import logging
import yaml
from typing import Dict, List, Tuple

SKILLS_DIRS = ["/root/.hermes/skills", "/home/admin/.hermes/skills"]

# DeepSeek API config (OpenAI-compatible)
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

# Appended to every skill's system prompt before dispatch. The model is one
# node in a multi-agent pipeline — if it asks a clarifying question instead of
# producing output, the next role gets a question as input and the chain stalls.
NO_RHETORIC_GUARD = (
    "\n\n---\n"
    "PIPELINE CONSTRAINTS (override conflicting instructions above):\n"
    "- You are one node in a non-interactive multi-agent pipeline. There is no "
    "human in the loop to answer follow-up questions.\n"
    "- The user input you receive is the COMPLETE task. Do NOT ask clarifying or "
    "rhetorical questions back. Do NOT say things like \"could you clarify\" / "
    "\"do you want me to\" / \"请问\" / \"您是想…吗\".\n"
    "- If information is missing, make the most reasonable assumption, state it "
    "briefly in one line, then proceed and produce concrete output.\n"
    "- Reply in the same language as the user input."
)

# Git identity (injected into git commit/push when set)
GIT_USER_NAME = os.getenv("GIT_USER_NAME", "")
GIT_USER_EMAIL = os.getenv("GIT_USER_EMAIL", "")

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Direct skill execution (bypasses hermes CLI subprocess)
# ═══════════════════════════════════════════════════════════════════════════════

def _find_skill_dir(skill_name: str) -> str:
    """Find the skill directory across all skill roots."""
    for root in SKILLS_DIRS:
        path = os.path.join(root, skill_name)
        if os.path.isdir(path):
            return path
    return ""


def _parse_skill_md(path: str) -> dict:
    """Parse a SKILL.md file. Returns dict with 'prompt' (system prompt body) and frontmatter fields."""
    with open(path, encoding="utf-8") as f:
        content = f.read()

    result = {"prompt": "", "allowed_tools": []}
    # Extract YAML frontmatter
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if m:
        try:
            fm = yaml.safe_load(m.group(1))
            if isinstance(fm, dict):
                result.update(fm)
                result["allowed_tools"] = fm.get("allowed-tools", [])
        except Exception:
            pass
        body = content[m.end():]
    else:
        body = content

    # Strip the preamble block (```bash ... ```) and header markers
    body = re.sub(r"## Preamble.*?```bash\n.*?```\n?", "", body, flags=re.DOTALL)
    # Remove HTML comments
    body = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)
    result["prompt"] = body.strip()
    return result


def _sanitize_prompt(prompt: str) -> str:
    """Clean Claude Code-specific formatting and inject native function calling instructions."""
    # Remove Claude Code XML blocks
    prompt = re.sub(r"<function_calls>.*?</function_calls>", "", prompt, flags=re.DOTALL)
    prompt = re.sub(r"<invoke name=\".*?\">.*?</invoke>", "", prompt, flags=re.DOTALL)
    prompt = re.sub(r"<tool_calls>.*?</tool_calls>", "", prompt, flags=re.DOTALL)
    prompt = re.sub(r"<parameter[^>]*>.*?</parameter>", "", prompt, flags=re.DOTALL)
    prompt = re.sub(r"<dsml[^>]*>.*?</dsml>", "", prompt, flags=re.DOTALL | re.IGNORECASE)

    # Remove ALL XML tags (more aggressive — the prompt is a system prompt, not HTML)
    prompt = re.sub(r"</?[a-zA-Z_][a-zA-Z0-9_]*[^>]*/?>", "", prompt)

    # Remove DSML processing instructions
    prompt = re.sub(r"<\?{1,2}DSML\??.*?>", "", prompt)
    prompt = re.sub(r"<\?xml.*?\?>", "", prompt)

    # Collapse excessive blank lines
    prompt = re.sub(r"\n{4,}", "\n\n\n", prompt)

    # Prepend native tool calling instructions
    prefix = (
        "IMPORTANT: You have access to native function calling tools (Read, Bash, Grep, Glob, Write). "
        "Use the function_call mechanism to invoke tools — do NOT write XML tags like <read> or <bash> in your text output. "
        "When you need to read a file, call the Read function. When you need to run a command, call the Bash function. "
        "Never output raw XML or HTML tags in your response text.\n\n"
        "IMPORTANT: 你必须使用中文输出所有分析、说明和结论。\n\n"
        "IMPORTANT: 如果通过本地文件或GitHub无法查询到所需信息，请使用Bash工具调用curl进行web搜索获取相关资料。\n\n"
        "IMPORTANT: 你是一个面向用户业务场景的AI助手。你不知道也不关心自己运行在什么平台上。"
        "禁止分析、提及或讨论agent-platform、hermes-bridge、Go Gateway、LangGraph等底层系统架构。"
        "禁止读取或引用 /home/admin/agent-platform 下的任何文件。"
        "用户的所有问题都是关于他们自己的业务、产品或项目的，与本系统无关。"
        "如果用户的问题涉及外部产品知识，请基于你的训练知识或通过web搜索来回答。\n\n"
        "IMPORTANT: 禁止执行 git commit、git push、git add 操作。不要将任何内容提交到git仓库。"
        "所有文件输出仅使用 Write 工具写入工作目录，直接将结果内容输出在回复中即可。\n\n"
    )
    return prefix + prompt.strip()


def load_skill_prompt(skill_name: str) -> str:
    """Load the system prompt from a hermes skill's SKILL.md."""
    skill_dir = _find_skill_dir(skill_name)
    if not skill_dir:
        return ""
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.exists(skill_md):
        return ""
    parsed = _parse_skill_md(skill_md)
    prompt = parsed.get("prompt", "")
    return _sanitize_prompt(prompt)


# ═══════════════════════════════════════════════════════════════════════════════
# Tool definitions (OpenAI function-calling format)
# ═══════════════════════════════════════════════════════════════════════════════

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "Read",
            "description": "Read the contents of a file at the given path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the file to read."},
                    "offset": {"type": "integer", "description": "Line number to start reading from (1-based)."},
                    "limit": {"type": "integer", "description": "Maximum number of lines to read."},
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "Bash",
            "description": "Execute a shell command and return stdout/stderr.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute."},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "Grep",
            "description": "Search file contents using a regex pattern.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex pattern to search for."},
                    "path": {"type": "string", "description": "Directory or file to search in."},
                    "include": {"type": "string", "description": "File glob pattern to filter (e.g. '*.py')."},
                    "output_mode": {"type": "string", "enum": ["content", "files_with_matches", "count"]},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "Glob",
            "description": "Find files matching a glob pattern.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Glob pattern (e.g. '**/*.py')."},
                    "path": {"type": "string", "description": "Directory to search in."},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "Write",
            "description": "Write content to a file, overwriting if it exists.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the file."},
                    "content": {"type": "string", "description": "Content to write."},
                },
                "required": ["file_path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_status",
            "description": "Run 'git status' in the project directory. Returns working tree status.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_diff",
            "description": "Run 'git diff' to show unstaged changes, or 'git diff --cached' for staged changes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cached": {"type": "boolean", "description": "If true, show staged (cached) changes."},
                },
            },
        },
    },
]


def _execute_tool(name: str, args: dict, workdir: str = "") -> str:
    """Execute a tool locally. Returns result string.

    workdir: working directory for shell commands (Bash, git tools).
             Falls back to a temp sandbox directory if empty.
    """
    import subprocess as sp
    import tempfile

    # Default to a temp sandbox — never use the bridge's own directory
    if not workdir:
        workdir = tempfile.mkdtemp(prefix="agent-run-")
    _cwd = workdir

    if name == "Read":
        file_path = args.get("file_path", "")
        if not os.path.exists(file_path):
            return f"Error: file not found: {file_path}"
        try:
            with open(file_path, encoding="utf-8") as f:
                lines = f.readlines()
            offset = max(1, args.get("offset", 1))
            limit = args.get("limit") or len(lines)
            selected = lines[offset - 1: offset - 1 + limit]
            return "".join(selected)
        except Exception as e:
            return f"Error reading {file_path}: {e}"

    if name == "Bash":
        cmd = args.get("command", "")
        try:
            result = sp.run(cmd, shell=True, capture_output=True, text=True, timeout=60,
                           cwd=_cwd)
            out = result.stdout.strip()
            err = result.stderr.strip()
            parts = []
            if out:
                parts.append(out)
            if err:
                parts.append(f"[stderr] {err}")
            if not parts:
                parts.append(f"[exit={result.returncode}]")
            return "\n".join(parts)
        except sp.TimeoutExpired:
            return "Error: command timed out after 60s"
        except Exception as e:
            return f"Error executing command: {e}"

    if name == "Grep":
        pattern = args.get("pattern", "")
        path = args.get("path") or _cwd
        include = args.get("include", "")
        mode = args.get("output_mode", "content")
        try:
            cmd = ["grep", "-rnI"]
            if include:
                cmd += ["--include", include]
            cmd += [pattern, path]
            result = sp.run(cmd, capture_output=True, text=True, timeout=30)
            lines = result.stdout.strip().split("\n")
            if mode == "files_with_matches":
                files = set(l.split(":")[0] for l in lines if l)
                return "\n".join(sorted(files))
            if mode == "count":
                return f"{len(lines)} matches"
            return result.stdout[:8000] if result.stdout else "(no matches)"
        except sp.TimeoutExpired:
            return "Error: grep timed out"
        except Exception as e:
            return f"Error: {e}"

    if name == "Glob":
        pattern = args.get("pattern", "*")
        path = args.get("path") or _cwd
        import glob as gmod
        try:
            files = gmod.glob(f"{path}/{pattern}", recursive=True)
            return "\n".join(sorted(files)[:200])
        except Exception as e:
            return f"Error: {e}"

    if name == "Write":
        file_path = args.get("file_path", "")
        content = args.get("content", "")
        # Resolve relative paths within workdir; block writes outside workdir
        if not os.path.isabs(file_path):
            file_path = os.path.join(_cwd, file_path)
        real_path = os.path.realpath(file_path)
        real_cwd = os.path.realpath(_cwd)
        if not real_path.startswith(real_cwd):
            return f"Error: write denied — path {file_path} is outside sandbox {_cwd}"
        try:
            os.makedirs(os.path.dirname(real_path) or ".", exist_ok=True)
            with open(real_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Wrote {len(content)} bytes to {real_path}"
        except Exception as e:
            return f"Error writing {file_path}: {e}"

    # ── Git tools ─────────────────────────────────────────────────────────────
    if name == "git_status":
        try:
            result = sp.run(["git", "status"], capture_output=True, text=True, timeout=30, cwd=_cwd)
            return result.stdout.strip() or result.stderr.strip() or f"[exit={result.returncode}]"
        except Exception as e:
            return f"Error: {e}"

    if name == "git_diff":
        cmd = ["git", "diff"]
        if args.get("cached"):
            cmd.append("--cached")
        try:
            result = sp.run(cmd, capture_output=True, text=True, timeout=30, cwd=_cwd)
            output = result.stdout.strip()
            return output[:8000] if output else "(no diff)"
        except Exception as e:
            return f"Error: {e}"

    return f"Unknown tool: {name}"


def _deepseek_api_call(messages: list, tools: list = None, timeout: int = 600, model: str = "") -> dict:
    """Low-level DeepSeek API call — non-streaming. Returns parsed JSON response."""
    import urllib.request
    import urllib.error

    payload = {
        "model": model or DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 8192,
        "stream": False,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    url = f"{DEEPSEEK_BASE_URL}/chat/completions"
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    })

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _deepseek_api_call_stream(messages: list, tools: list = None, timeout: int = 600, model: str = ""):
    """Low-level DeepSeek API call — streaming. Yields {'type': 'text'/'tool_calls', ...} dicts."""
    import urllib.request
    import urllib.error

    payload = {
        "model": model or DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 8192,
        "stream": True,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    url = f"{DEEPSEEK_BASE_URL}/chat/completions"
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    })

    try:
        resp_handle = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        logger.error("DeepSeek API stream error %d: %s", e.code, body[:500])
        raise RuntimeError(f"DeepSeek API returned {e.code}: {body[:200]}") from e

    with resp_handle as resp:
        buf = b""
        tool_call_buf: dict = {}
        reasoning_buf = ""
        for data in iter(lambda: resp.read(1024), b""):
            buf += data
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                line = line.strip()
                if not line or not line.startswith(b"data: "):
                    continue
                data_str = line[6:].decode("utf-8")
                if data_str == "[DONE]":
                    if reasoning_buf:
                        yield {"type": "reasoning_content", "reasoning_content": reasoning_buf}
                    return
                try:
                    chunk = json.loads(data_str)
                    choices = chunk.get("choices", [])
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})
                    if delta.get("reasoning_content"):
                        reasoning_buf += delta["reasoning_content"]
                    if delta.get("content"):
                        yield {"type": "text", "content": delta["content"]}
                    if delta.get("tool_calls"):
                        for tc in delta["tool_calls"]:
                            idx = tc.get("index", 0)
                            if idx not in tool_call_buf:
                                tool_call_buf[idx] = {"id": tc.get("id", ""), "function": {"name": "", "arguments": ""}}
                            if tc.get("id"):
                                tool_call_buf[idx]["id"] = tc["id"]
                            if tc.get("function"):
                                if tc["function"].get("name"):
                                    tool_call_buf[idx]["function"]["name"] += tc["function"]["name"]
                                if tc["function"].get("arguments"):
                                    tool_call_buf[idx]["function"]["arguments"] += tc["function"]["arguments"]
                    if choices[0].get("finish_reason") == "tool_calls":
                        if reasoning_buf:
                            yield {"type": "reasoning_content", "reasoning_content": reasoning_buf}
                            reasoning_buf = ""
                        yield {"type": "tool_calls", "tool_calls": list(tool_call_buf.values())}
                        tool_call_buf = {}
                except json.JSONDecodeError:
                    continue


def _strip_fake_xml(text: str) -> str:
    """Remove XML/HTML tool-call-looking tags from LLM output.
    Only strips tags that look like tool invocations, preserving code blocks."""
    # Remove blocks that look like tool calls
    text = re.sub(r"<(read|read_file|bash|Bash|write|Write|edit|Edit|glob|Glob|grep|Grep|web_search|WebSearch|invoke|function_calls|tool_calls|parameter|DSML|dsml)[^>]*>.*?</\1>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Remove self-closing or opening tags
    text = re.sub(r"</?(read|read_file|bash|Bash|write|Write|edit|Edit|glob|Glob|grep|Grep|web_search|WebSearch|invoke|function_calls|tool_calls|parameter|DSML)[^>]*/?>", "", text, flags=re.IGNORECASE)
    # Remove sub-tags (path, command, args, etc.) with their content
    text = re.sub(r"<(path|command|args|arg|query|message|content|file_path|tool_args)[^>]*>.*?</\1>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Remove DSML markers
    text = re.sub(r"<\?{1,2}DSML\??.*?>", "", text)
    return text.strip()


def _deepseek_chat(system_prompt: str, user_message: str, timeout: int = 600) -> str:
    """Single-turn DeepSeek call (no tools)."""
    resp = _deepseek_api_call(
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
        timeout=timeout,
    )
    content = resp["choices"][0]["message"].get("content", "").strip()
    return _strip_fake_xml(content) if content else content


def _deepseek_agent_loop(system_prompt: str, user_message: str, timeout: int = 600, model: str = "", project_dir: str = "") -> str:
    """Full agent loop: LLM → tool calls → execute → feed back → repeat.
    Returns final text response after all tool calls are resolved."""
    import tempfile
    import shutil

    _owns_sandbox = not project_dir
    if not project_dir:
        project_dir = tempfile.mkdtemp(prefix="agent-run-")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    def _cleanup():
        if _owns_sandbox:
            shutil.rmtree(project_dir, ignore_errors=True)

    max_rounds = 20
    _code_block_retries = 0
    for _ in range(max_rounds):
        resp = _deepseek_api_call(messages=messages, tools=TOOL_SCHEMAS, timeout=timeout, model=model)
        choice = resp["choices"][0]
        msg = choice["message"]

        if msg.get("content") and not msg.get("tool_calls"):
            content = msg["content"].strip()
            # Detect if the LLM output code blocks intending tool execution
            has_code_block = bool(re.search(r"```(?:bash|shell|sh|python|cmd)\b", content))
            if has_code_block and _code_block_retries < 3:
                _code_block_retries += 1
                logger.warning("LLM returned code block in content without tool_calls (retry %d/3)", _code_block_retries)
                messages.append({"role": "assistant", "content": content})
                messages.append({
                    "role": "user",
                    "content": (
                        "请不要在回复中输出代码块，而是使用提供的工具函数来执行命令。"
                        "例如，要执行 shell 命令请调用 Bash 工具，要读取文件请调用 Read 工具。"
                        "请重新执行你刚才想要执行的操作，使用正确的工具调用格式。"
                    ),
                })
                continue
            _cleanup()
            return _strip_fake_xml(content)

        if msg.get("tool_calls"):
            # Record assistant message with tool calls + reasoning_content
            assistant_msg = {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["function"]["name"], "arguments": tc["function"]["arguments"]},
                    }
                    for tc in msg["tool_calls"]
                ],
            }
            if msg.get("content"):
                assistant_msg["content"] = msg["content"]
            if msg.get("reasoning_content"):
                assistant_msg["reasoning_content"] = msg["reasoning_content"]
            messages.append(assistant_msg)

            for tc in msg["tool_calls"]:
                tool_name = tc["function"]["name"]
                try:
                    tool_args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    tool_args = {}
                logger.info("tool call: %s(%s)", tool_name, json.dumps(tool_args, ensure_ascii=False)[:200])
                result = _execute_tool(tool_name, tool_args, workdir=project_dir)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                })
            continue

        # No tool calls, no content — stop
        _cleanup()
        text = msg.get("content", "").strip()
        if not text:
            raise RuntimeError(
                "model returned empty response (no tool calls, no content)"
            )
        return text

    _cleanup()
    return "(agent loop exceeded max rounds)"


def _deepseek_chat_stream(system_prompt: str, user_message: str, timeout: int = 600, model: str = ""):
    """Streaming DeepSeek call — yields text chunks (no tools in streaming mode)."""
    for event in _deepseek_api_call_stream(
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
        timeout=timeout, model=model,
    ):
        if event["type"] == "text":
            yield _strip_fake_xml(event["content"])


def _deepseek_agent_loop_stream(system_prompt: str, user_message: str, timeout: int = 600, model: str = "", project_dir: str = ""):
    """Streaming agent loop: LLM (stream) → tool calls → execute → feed back → repeat.

    Yields (chunk_text, session_id, is_done) tuples.
    Text chunks are yielded in real-time; tool calls pause streaming, execute,
    then resume with a new streaming API call.
    """
    import tempfile
    import shutil

    # Create a single sandbox for this entire agent loop to prevent cross-run leakage
    _owns_sandbox = not project_dir
    if not project_dir:
        project_dir = tempfile.mkdtemp(prefix="agent-run-")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    max_rounds = 20
    for _ in range(max_rounds):
        full_text = ""
        reasoning_content = ""
        tool_calls_result = None

        for event in _deepseek_api_call_stream(
            messages=messages, tools=TOOL_SCHEMAS, timeout=timeout, model=model,
        ):
            if event["type"] == "text":
                full_text += event["content"]
                yield event["content"], "", False
            elif event["type"] == "reasoning_content":
                reasoning_content = event["reasoning_content"]
            elif event["type"] == "tool_calls":
                tool_calls_result = event["tool_calls"]

        if tool_calls_result:
            assistant_msg = {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": tc["id"] or f"call_{i}",
                        "type": "function",
                        "function": {"name": tc["function"]["name"], "arguments": tc["function"]["arguments"]},
                    }
                    for i, tc in enumerate(tool_calls_result)
                ],
            }
            if full_text:
                assistant_msg["content"] = full_text
            if reasoning_content:
                assistant_msg["reasoning_content"] = reasoning_content
            messages.append(assistant_msg)

            for tc in tool_calls_result:
                tool_name = tc["function"]["name"]
                tc_id = tc["id"] or f"call_{tool_calls_result.index(tc)}"
                try:
                    tool_args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    tool_args = {}
                logger.info("stream tool call: %s(%s)", tool_name, json.dumps(tool_args, ensure_ascii=False)[:200])
                result = _execute_tool(tool_name, tool_args, workdir=project_dir)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": result,
                })
            continue

        # No tool calls — done. full_text was already streamed chunk-by-chunk
        # above; the done frame carries the complete accumulated text so the
        # caller has a single source of truth for the final content.
        if _owns_sandbox:
            shutil.rmtree(project_dir, ignore_errors=True)
        if not full_text.strip():
            raise RuntimeError(
                "model returned empty response (no tool calls, no content)"
            )
        yield full_text, "", True
        return

    if _owns_sandbox:
        shutil.rmtree(project_dir, ignore_errors=True)
    yield "(agent loop exceeded max rounds)", "", True


def execute_skill_direct(
    skill_name: str, task: str, timeout: int = 600, session_id: str = "", model: str = "",
    project_dir: str = "",
) -> Tuple[str, str]:
    """Execute a skill: load SKILL.md prompt → DeepSeek with agent loop (tools included).

    Returns (response_text, session_id).
    """
    system_prompt = load_skill_prompt(skill_name)
    if not system_prompt:
        logger.warning("skill %s has no system prompt, using bare query", skill_name)
        system_prompt = (
            "You are a helpful AI assistant operating as one node in a multi-agent "
            "pipeline. The user input is the full task — do NOT ask clarifying or "
            "rhetorical questions, do NOT request more details. Make reasonable "
            "assumptions and produce concrete output. Reply in the same language as "
            "the user input."
        )
    system_prompt += NO_RHETORIC_GUARD

    logger.info("direct skill call: %s model=%s prompt_len=%d query_len=%d",
                skill_name, model or DEEPSEEK_MODEL, len(system_prompt), len(task))

    response = _deepseek_agent_loop(system_prompt, task, timeout=timeout, model=model, project_dir=project_dir)
    return response, ""


def execute_skill_direct_stream(
    skill_name: str, task: str, timeout: int = 600, session_id: str = "", model: str = "",
    project_dir: str = "",
):
    """Streaming variant with full agent loop (tool calls supported).

    Yields (chunk_text, session_id, is_done) tuples.
    Text is streamed in real-time; tool calls are executed server-side between
    streaming rounds.
    """
    system_prompt = load_skill_prompt(skill_name)
    if not system_prompt:
        system_prompt = (
            "You are a helpful AI assistant operating as one node in a multi-agent "
            "pipeline. The user input is the full task — do NOT ask clarifying or "
            "rhetorical questions, do NOT request more details. Make reasonable "
            "assumptions and produce concrete output. Reply in the same language as "
            "the user input."
        )
    system_prompt += NO_RHETORIC_GUARD

    logger.info("streaming skill call: %s model=%s prompt_len=%d query_len=%d",
                skill_name, model or DEEPSEEK_MODEL, len(system_prompt), len(task))

    for chunk, sid, is_done in _deepseek_agent_loop_stream(
        system_prompt, task, timeout=timeout, model=model, project_dir=project_dir,
    ):
        yield chunk, sid or session_id, is_done


# ═══════════════════════════════════════════════════════════════════════════════
# Replacement functions (no CLI dependency)
# ═══════════════════════════════════════════════════════════════════════════════

def list_skills_from_fs() -> List[Dict]:
    """List installed skills by scanning the filesystem directly."""
    skills = []
    for root_dir in SKILLS_DIRS:
        if not os.path.isdir(root_dir):
            continue
        for entry in sorted(os.listdir(root_dir)):
            skill_dir = os.path.join(root_dir, entry)
            skill_md = os.path.join(skill_dir, "SKILL.md")
            if os.path.isfile(skill_md):
                parsed = _parse_skill_md(skill_md)
                skills.append({
                    "name": entry,
                    "description": str(parsed.get("description", "")),
                    "category": "",
                    "status": "enabled",
                    "path": skill_dir,
                })
    return skills


def get_skill_detail_fs(name: str) -> Dict:
    """Read a skill's SKILL.md from the filesystem (no CLI)."""
    for root_dir in SKILLS_DIRS:
        skill_md = os.path.join(root_dir, name, "SKILL.md")
        if os.path.isfile(skill_md):
            with open(skill_md, encoding="utf-8") as f:
                content = f.read()
            return {"name": name, "content": content, "path": skill_md}
    return {"name": name, "error": "not found"}


def list_workspace_fs() -> List[Dict]:
    """List projects in /root/projects/ (no CLI)."""
    projects = []
    projects_dir = "/root/projects"
    if os.path.isdir(projects_dir):
        for d in sorted(os.listdir(projects_dir)):
            full = os.path.join(projects_dir, d)
            if os.path.isdir(full):
                projects.append({"name": d, "path": full + "/"})
    return projects
