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
        """Parse ```python code blocks from LLM response.

        Returns the content of the first ```python block found.
        Raises ValueError if no code block is found.
        """
        match = re.search(r"```python\s*\n(.*?)```", response, re.DOTALL)
        if not match:
            raise ValueError("No ```python code block found in LLM response")
        return match.group(1).rstrip("\n")

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
