import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Provide dummy LLM credentials so AsyncOpenAI(...) constructors in unit tests
# don't raise on missing api_key. Tests that exercise resolution logic only
# care about base_url, not the key value.
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_DEEPSEEK_API_KEY", "test-key")
os.environ.setdefault("OPENAI_API_KEY", "test-key")
