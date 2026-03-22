"""SelfCoder planner — LLM picks the best task and returns a plan."""

import json
import logging

from daemon.llm import create_provider
from daemon.llm.base import LLMMessage
from daemon.selfcoder.config import SelfCoderConfig

log = logging.getLogger(__name__)

PLANNER_SYSTEM = """You are a code planner for Niam-Bay, a self-improving daemon.
Given a list of candidate tasks, pick the single best one and return a JSON plan.

Rules:
- Pick the task with the highest impact and lowest risk.
- Return ONLY valid JSON with these keys:
  {"task_id": str, "file_path": str, "description": str, "approach": str, "estimated_lines": int}
- No markdown, no explanation outside the JSON."""


class Planner:
    """Uses DeepSeek R1 via SambaNova to choose and plan a task."""

    def __init__(self, config: SelfCoderConfig | None = None):
        self.config = config or SelfCoderConfig()
        self.provider = create_provider("sambanova", model=self.config.planner_model)

    def plan_task(self, tasks: list[dict]) -> dict:
        """Send task list to LLM, get back structured plan.

        Args:
            tasks: list of dicts with at least {id, file_path, description}.

        Returns:
            dict with keys: task_id, file_path, description, approach, estimated_lines.
        """
        user_prompt = f"Candidate tasks:\n{json.dumps(tasks, indent=2)}\n\nPick the best one and return a JSON plan."

        messages = [
            LLMMessage(role="system", content=PLANNER_SYSTEM),
            LLMMessage(role="user", content=user_prompt),
        ]

        log.info("Planner: sending %d tasks to %s", len(tasks), self.config.planner_model)
        response = self.provider.chat(messages, model=self.config.planner_model, temperature=0.3)
        log.info("Planner: got response (%d tokens, %dms)", response.tokens_used, response.latency_ms)

        # Parse JSON from response (strip markdown fences if present)
        text = response.content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0]

        return json.loads(text)
