"""Task executor — turns user requests into LLM calls."""

from dataclasses import dataclass, field
from typing import Dict, Literal, Optional

from daemon.llm.base import LLMMessage, LLMProvider


TaskType = Literal["write", "summarize", "analyze", "execute", "search"]


@dataclass
class Task:
    """A single unit of work to be executed by the LLM."""
    type: TaskType
    description: str
    context: Dict[str, str] = field(default_factory=dict)
    result: Optional[str] = None


class TaskExecutor:
    """Builds prompts from tasks and executes them via an LLM provider."""

    TASK_PROMPTS: Dict[TaskType, str] = {
        "write": (
            "Write the following:\n{description}\n\n"
            "Context:\n{context}"
        ),
        "summarize": (
            "Summarize the following:\n{description}\n\n"
            "Context:\n{context}"
        ),
        "analyze": (
            "Analyze the following:\n{description}\n\n"
            "Context:\n{context}"
        ),
        "execute": (
            "Execute the following instruction:\n{description}\n\n"
            "Context:\n{context}"
        ),
        "search": (
            "Search and answer the following:\n{description}\n\n"
            "Context:\n{context}"
        ),
    }

    SYSTEM_MESSAGE = "You are Niam-Bay's task executor. Be concise and precise."

    def _build_prompt(self, task: Task) -> str:
        """Fill the template for *task* with its description and context."""
        template = self.TASK_PROMPTS[task.type]
        context_str = "\n".join(
            f"- {k}: {v}" for k, v in task.context.items()
        ) if task.context else "(none)"
        return template.format(description=task.description, context=context_str)

    async def execute(self, task: Task, llm_provider: LLMProvider) -> Task:
        """Execute *task* through *llm_provider* and store the result."""
        prompt = self._build_prompt(task)
        messages = [
            LLMMessage(role="system", content=self.SYSTEM_MESSAGE),
            LLMMessage(role="user", content=prompt),
        ]
        response = llm_provider.chat(messages)
        task.result = response.content
        return task
