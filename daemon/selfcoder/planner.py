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

        # Parse JSON from response (handle thinking tags, markdown fences)
        text = response.content.strip()

        # DeepSeek R1 wraps response in <think>...</think> tags
        if "<think>" in text:
            text = text.split("</think>")[-1].strip()

        # Strip markdown fences
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        # Try to find JSON object in the text
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Find first { and last }
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                return json.loads(text[start:end+1])
            # Fallback: return first task as-is
            log.warning("Planner: could not parse LLM response, using first task")
            if tasks:
                t = tasks[0]
                return {"task_id": t.get("description","")[:50], "file_path": t.get("file",""), "description": t.get("description",""), "approach": "fix", "estimated_lines": 10}
            raise
