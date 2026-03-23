"""SelfCoder coder — LLM generates code changes."""

import logging
import re

from daemon.llm import create_provider
from daemon.llm.base import LLMMessage
from daemon.selfcoder.config import SelfCoderConfig
from daemon.selfcoder.validator import Validator

log = logging.getLogger(__name__)

CODER_SYSTEM = """You are a Python coder for Niam-Bay, a self-improving daemon.
Given a task plan and the current file content, produce the updated file.

Rules:
- Return the COMPLETE updated file inside a single ```python code block.
- Do NOT use os.system, subprocess.run, eval, exec, __import__, shutil.rmtree, or os.remove.
- Keep changes minimal and focused on the task.
- Preserve existing style and imports."""


class Coder:
    """Uses DeepSeek V3.2 via SambaNova to generate code."""

    def __init__(self, config: SelfCoderConfig | None = None):
        self.config = config or SelfCoderConfig()
        self.provider = create_provider("sambanova", model=self.config.coder_model)
        self.validator = Validator(self.config)

    def generate_code(self, task_plan: dict, current_code: str) -> str:
        """Send plan + current file to LLM, return generated code.

        Args:
            task_plan: dict with task_id, file_path, description, approach.
            current_code: current content of the target file.

        Returns:
            Raw LLM response string.
        """
        user_prompt = (
            f"Task: {task_plan.get('description', '')}\n"
            f"Approach: {task_plan.get('approach', '')}\n"
            f"File: {task_plan.get('file_path', '')}\n\n"
            f"Current code:\n```python\n{current_code}\n```\n\n"
            "Return the complete updated file in a ```python block."
        )

        messages = [
            LLMMessage(role="system", content=CODER_SYSTEM),
            LLMMessage(role="user", content=user_prompt),
        ]

        log.info("Coder: generating code for %s", task_plan.get("task_id", "?"))
        response = self.provider.chat(messages, model=self.config.coder_model, temperature=0.2)
        log.info("Coder: got response (%d tokens, %dms)", response.tokens_used, response.latency_ms)

        return response.content

    @staticmethod
    def extract_code(response: str) -> str:
        """Extract code from LLM response, with flexible parsing.

        Strategy:
        1. If response has ```python blocks, extract the first one.
        2. If response has ``` blocks (without language tag), extract the first one.
        3. If no blocks at all, treat the entire response as code
           (strip leading/trailing markdown or explanation lines).

        Returns extracted code string.
        """
        # Strategy 1: ```python block
        match = re.search(r"```python\s*\n(.*?)```", response, re.DOTALL)
        if match:
            return match.group(1).rstrip("\n")

        # Strategy 2: generic ``` block
        match = re.search(r"```\s*\n(.*?)```", response, re.DOTALL)
        if match:
            return match.group(1).rstrip("\n")

        # Strategy 3: no code blocks — treat entire response as code
        # Strip lines that look like markdown explanations (starting with # not followed by space+code-comment pattern)
        lines = response.strip().splitlines()
        code_lines = []
        for line in lines:
            stripped = line.strip()
            # Skip empty leading/trailing markdown-style lines
            if not code_lines and (stripped.startswith("```") or stripped == ""):
                continue
            if stripped.startswith("```"):
                break
            code_lines.append(line)
        # Remove trailing blank lines
        while code_lines and code_lines[-1].strip() == "":
            code_lines.pop()
        return "\n".join(code_lines)

    def apply_changes(self, file_path: str, new_content: str) -> None:
        """Write new content to file after validator checks.

        Validates syntax and forbidden patterns before writing.
        Raises ValueError if validation fails.
        """
        ok, errors = self.validator.validate_all(
            code=new_content,
            lines=new_content.count("\n") + 1,
            files=1,
            paths=[file_path],
        )
        if not ok:
            raise ValueError(f"Validation failed: {errors}")

        from pathlib import Path
        Path(file_path).write_text(new_content, encoding="utf-8")
        log.info("Coder: wrote %d lines to %s", new_content.count("\n") + 1, file_path)
