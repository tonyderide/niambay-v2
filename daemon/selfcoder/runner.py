"""SelfCoder runner — the daemon that codes itself.

Assembles all modules into a single orchestration loop:
scan → plan → code → validate → review → publish/suggest.
"""

import logging
import time
from datetime import datetime
from pathlib import Path

from daemon.llm import create_provider
from daemon.selfcoder.coder import Coder
from daemon.selfcoder.config import SelfCoderConfig
from daemon.selfcoder.mailer import Mailer
from daemon.selfcoder.planner import Planner
from daemon.selfcoder.publisher import Publisher
from daemon.selfcoder.reviewer import Reviewer
from daemon.selfcoder.scanner import Scanner
from daemon.selfcoder.state import SelfCoderState
from daemon.selfcoder.validator import Validator

logger = logging.getLogger(__name__)


class SelfCoder:
    """The main orchestrator — one class to run them all."""

    def __init__(self, config=None):
        self.config = config or SelfCoderConfig()
        self.state = (
            SelfCoderState.load(self.config.state_path)
            if Path(self.config.state_path).exists()
            else SelfCoderState(max_attempts=self.config.max_attempts_per_task)
        )
        self.scanner = Scanner(self.config.project_root, self.config)
        self.planner = Planner(self.config)
        self.coder = Coder(self.config)
        self.validator = Validator(self.config)
        self.reviewer = Reviewer(
            provider=create_provider("sambanova", model=self.config.reviewer_model),
            model=self.config.reviewer_model,
        )
        self.publisher = Publisher(self.config.project_root)
        self.mailer = Mailer(self.config.email_from, self.config.smtp_server, self.config.smtp_port)
        self.daily_results = {"completed": [], "failed": [], "suggestions": []}

    def run_cycle(self) -> dict:
        """One cycle: scan -> plan -> code -> validate -> review -> publish/suggest."""
        # 1. Get tasks, filter already-skipped ones
        tasks = self.scanner.get_all_tasks()
        tasks = [t for t in tasks if not self.state.should_skip(t["description"][:50])]
        if not tasks:
            return {"status": "no_tasks"}

        # 2. Plan (LLM chooses the best task)
        try:
            plan = self.planner.plan_task(tasks)
        except Exception as e:
            logger.error("Planner failed: %s", e)
            return {"status": "plan_failed", "error": str(e)}

        task_name = plan.get("task_name", plan.get("task_id", tasks[0]["description"][:50]))

        # 3. Read current file content
        target_file = plan.get("file", plan.get("file_path", ""))
        current_code = ""
        full_path = Path(self.config.project_root) / target_file
        if target_file and full_path.exists():
            current_code = full_path.read_text(encoding="utf-8")

        # 4. Code (LLM writes the fix)
        try:
            new_code = self.coder.generate_code(plan, current_code)
        except Exception as e:
            self.state.record_failure(task_name, str(e))
            self.daily_results["failed"].append({
                "name": task_name, "error": str(e), "attempts": self.state.tasks_failed.get(task_name, 1),
            })
            return {"status": "code_failed", "error": str(e)}

        # 5. Extract and validate
        code_to_check = self.coder.extract_code(new_code) if "```" in new_code else new_code
        ok, errors = self.validator.validate_all(
            code_to_check,
            lines=len(code_to_check.splitlines()),
            files=1,
            paths=[target_file] if target_file else [],
        )
        if not ok:
            self.state.record_failure(task_name, "; ".join(errors))
            self.daily_results["failed"].append({
                "name": task_name, "error": "; ".join(errors),
                "attempts": self.state.tasks_failed.get(task_name, 1),
            })
            return {"status": "validation_failed", "errors": errors}

        # 6. Suggest mode — stop here, record the suggestion
        if self.config.mode == "suggest":
            approach = plan.get("approach", plan.get("description", ""))
            self.daily_results["suggestions"].append(f"{task_name}: {approach}")
            self.state.record_success(task_name, "suggest-only", len(code_to_check.splitlines()))
            self.state.total_cycles += 1
            self.state.save(self.config.state_path)
            return {"status": "suggested", "task": task_name}

        # 7. Auto mode — apply, test, review, commit, push
        branch_name = self.publisher.make_branch_name(task_name)
        try:
            self.publisher.create_branch(branch_name)
            full_path.write_text(code_to_check, encoding="utf-8")

            # Run tests
            passed, test_output = self.validator.run_tests(self.config.project_root)
            if not passed:
                # Revert: checkout master, delete branch
                self.publisher.back_to_master()
                self.publisher.cleanup(branch_name)
                self.state.record_failure(task_name, f"Tests failed: {test_output[:200]}")
                self.daily_results["failed"].append({
                    "name": task_name, "error": "Tests failed", "attempts": self.state.tasks_failed.get(task_name, 1),
                })
                return {"status": "tests_failed", "task": task_name}

            # Review the diff
            import subprocess
            diff_result = subprocess.run(
                ["git", "diff", "--cached"], capture_output=True, text=True,
                cwd=self.config.project_root,
            )
            approved, review_text = self.reviewer.review_diff(diff_result.stdout or "(no diff)")
            if not approved:
                self.publisher.back_to_master()
                self.publisher.cleanup(branch_name)
                self.state.record_failure(task_name, f"Review rejected: {review_text[:200]}")
                self.daily_results["failed"].append({
                    "name": task_name, "error": "Review rejected", "attempts": self.state.tasks_failed.get(task_name, 1),
                })
                return {"status": "review_rejected", "task": task_name}

            # Commit and push
            self.publisher.commit(f"auto: {task_name}", [target_file])
            self.publisher.push(branch_name)
            self.publisher.back_to_master()

            lines_changed = len(code_to_check.splitlines())
            self.state.record_success(task_name, branch_name, lines_changed)
            self.daily_results["completed"].append({
                "name": task_name, "branch": branch_name, "lines": lines_changed, "tests": "passed",
            })

        except Exception as e:
            logger.error("Auto-apply failed for %s: %s", task_name, e)
            # Try to get back to master
            try:
                self.publisher.back_to_master()
            except Exception:
                pass
            self.state.record_failure(task_name, str(e))
            self.daily_results["failed"].append({
                "name": task_name, "error": str(e), "attempts": self.state.tasks_failed.get(task_name, 1),
            })
            return {"status": "auto_failed", "error": str(e)}

        # 8. Record cycle
        self.state.total_cycles += 1
        self.state.save(self.config.state_path)
        return {"status": "completed", "task": task_name}

    def send_daily_report(self):
        """Send email summary of the day's work."""
        report = self.mailer.format_report(**self.daily_results)
        subject = f"[Niam-Bay Auto] {datetime.now().strftime('%d %B')} — {len(self.daily_results['completed'])} tâches"
        self.mailer.send(subject, report)
        self.daily_results = {"completed": [], "failed": [], "suggestions": []}

    def run_forever(self):
        """Main loop — run cycles until stopped."""
        logger.info("Self-Coder started in '%s' mode", self.config.mode)
        last_report = datetime.now()
        while True:
            try:
                result = self.run_cycle()
                logger.info("Cycle result: %s", result.get("status"))
            except Exception as e:
                logger.error("Cycle error: %s", e)

            self.state.save(self.config.state_path)

            # Daily report at 18:00
            now = datetime.now()
            if now.hour >= 18 and (now - last_report).total_seconds() > 3600:
                self.send_daily_report()
                last_report = now

            time.sleep(self.config.cooldown_minutes * 60)
