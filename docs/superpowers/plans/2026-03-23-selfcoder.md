# Self-Coding Daemon — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un daemon qui analyse, code, valide et publie des améliorations à son propre code, avec multi-validation et notification par mail.

**Architecture:** Pipeline séquentiel (scan→plan→code→validate→review→publish→notify) avec persistance d'état JSON, allowlists en code, et validation multi-stage (AST, imports, pytest, diff size, LLM review). Réutilise daemon/llm/ pour les appels LLM (SambaNova, Mistral).

**Tech Stack:** Python 3.13, pytest, ast (stdlib), smtplib (stdlib), subprocess (git), daemon/llm/ existant.

---

## File Structure

```
C:/niambay-v2/daemon/selfcoder/
├── __init__.py
├── config.py       # Allowlists, limites, paramètres
├── state.py        # Persistance état JSON
├── scanner.py      # Trouve tâches
├── planner.py      # LLM choisit la tâche
├── coder.py        # LLM écrit le code
├── validator.py    # Multi-validation
├── reviewer.py     # LLM review
├── publisher.py    # Git branch + commit
├── mailer.py       # SMTP email
└── runner.py       # Boucle principale
tests/
└── test_selfcoder.py
```

---

### Task 1: Config + Allowlists

**Files:**
- Create: `daemon/selfcoder/__init__.py`
- Create: `daemon/selfcoder/config.py`
- Create: `tests/test_selfcoder.py`

- [ ] **Step 1: Write tests**

```python
# tests/test_selfcoder.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from daemon.selfcoder.config import SelfCoderConfig

def test_config_defaults():
    cfg = SelfCoderConfig()
    assert cfg.max_lines_per_cycle == 30
    assert cfg.max_files_per_cycle == 3
    assert cfg.cooldown_minutes == 30
    assert cfg.max_attempts_per_task == 2
    assert cfg.mode == "suggest"

def test_config_is_path_allowed():
    cfg = SelfCoderConfig()
    assert cfg.is_path_allowed("daemon/collectors/window.py") == True
    assert cfg.is_path_allowed("daemon/selfcoder/config.py") == True
    assert cfg.is_path_allowed("tests/test_config.py") == True

def test_config_is_path_forbidden():
    cfg = SelfCoderConfig()
    assert cfg.is_path_allowed("GridTradingService.java") == False
    assert cfg.is_path_allowed("ScalpingBotService.java") == False
    assert cfg.is_path_allowed(".env") == False
    assert cfg.is_path_allowed("config.json") == False
```

- [ ] **Step 2: Run test, verify fail**
- [ ] **Step 3: Write config.py**

```python
# daemon/selfcoder/config.py
from dataclasses import dataclass, field
from pathlib import Path
import fnmatch

@dataclass
class SelfCoderConfig:
    # Limits
    max_lines_per_cycle: int = 30
    max_files_per_cycle: int = 3
    cooldown_minutes: int = 30
    max_attempts_per_task: int = 2
    mode: str = "suggest"  # "suggest" or "auto"

    # Paths
    project_root: str = str(Path(__file__).parent.parent.parent)
    state_path: str = str(Path.home() / ".niambay" / "selfcoder_state.json")

    # LLM
    planner_model: str = "DeepSeek-R1-0528"
    coder_model: str = "DeepSeek-V3.2"
    reviewer_model: str = "mistral-small-latest"
    planner_provider: str = "sambanova"
    coder_provider: str = "sambanova"
    reviewer_provider: str = "mistral"

    # Email
    email_from: str = "niam-bay@hotmail.com"
    email_to: str = "niam-bay@hotmail.com"
    smtp_server: str = "smtp-mail.outlook.com"
    smtp_port: int = 587

    # Allowlists
    allowed_patterns: list = field(default_factory=lambda: [
        "daemon/**/*.py",
        "frontend/**/*",
        "tests/**/*.py",
        "*.md",
    ])

    forbidden_patterns: list = field(default_factory=lambda: [
        "**/GridTradingService*",
        "**/ScalpingBotService*",
        "**/kraken/**",
        "**/*.env",
        "**/config.json",
        "**/secrets*",
        "**/*key*",
        "**/backend.jar",
    ])

    forbidden_code_patterns: list = field(default_factory=lambda: [
        "os.system(",
        "subprocess.run(",
        "subprocess.Popen(",
        "shutil.rmtree(",
        "os.remove(",
        "eval(",
        "exec(",
        "__import__(",
    ])

    def is_path_allowed(self, path: str) -> bool:
        path = path.replace("\\", "/")
        for pattern in self.forbidden_patterns:
            if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(Path(path).name, pattern.split("/")[-1]):
                return False
        for pattern in self.allowed_patterns:
            if fnmatch.fnmatch(path, pattern):
                return True
        return False
```

- [ ] **Step 4: Run tests, verify pass**
- [ ] **Step 5: Commit**

---

### Task 2: State Persistence

**Files:**
- Create: `daemon/selfcoder/state.py`
- Modify: `tests/test_selfcoder.py`

- [ ] **Step 1: Write tests**

```python
from daemon.selfcoder.state import SelfCoderState

def test_state_creation():
    s = SelfCoderState()
    assert s.tasks_completed == []
    assert s.tasks_failed == {}
    assert s.total_cycles == 0

def test_state_record_success():
    s = SelfCoderState()
    s.record_success("fix-window", "auto/2026-03-23-fix", 12)
    assert "fix-window" in s.tasks_completed
    assert s.total_lines_written == 12
    assert s.total_cycles == 1

def test_state_record_failure():
    s = SelfCoderState()
    s.record_failure("refactor-llm", "test failure")
    assert s.tasks_failed["refactor-llm"]["attempts"] == 1
    s.record_failure("refactor-llm", "still failing")
    assert s.tasks_failed["refactor-llm"]["attempts"] == 2

def test_state_should_skip():
    s = SelfCoderState(max_attempts=2)
    s.record_failure("bad-task", "err")
    assert s.should_skip("bad-task") == False
    s.record_failure("bad-task", "err")
    assert s.should_skip("bad-task") == True

def test_state_save_load(tmp_path):
    s = SelfCoderState()
    s.record_success("task1", "branch1", 10)
    path = str(tmp_path / "state.json")
    s.save(path)
    s2 = SelfCoderState.load(path)
    assert "task1" in s2.tasks_completed
```

- [ ] **Step 2: Write state.py**
- [ ] **Step 3: Run tests, commit**

---

### Task 3: Validator (the most critical piece)

**Files:**
- Create: `daemon/selfcoder/validator.py`
- Modify: `tests/test_selfcoder.py`

- [ ] **Step 1: Write tests**

```python
from daemon.selfcoder.validator import Validator

def test_validator_ast_valid():
    v = Validator()
    assert v.check_syntax("x = 1\nprint(x)") == True

def test_validator_ast_invalid():
    v = Validator()
    assert v.check_syntax("def foo(:\n  pass") == False

def test_validator_forbidden_patterns():
    v = Validator()
    assert v.check_forbidden("x = os.system('rm -rf /')") == False
    assert v.check_forbidden("x = eval(user_input)") == False
    assert v.check_forbidden("x = 1 + 2") == True

def test_validator_diff_size():
    v = Validator(max_lines=30, max_files=3)
    assert v.check_diff_size(lines_changed=20, files_changed=2) == True
    assert v.check_diff_size(lines_changed=50, files_changed=2) == False
    assert v.check_diff_size(lines_changed=10, files_changed=5) == False

def test_validator_paths():
    v = Validator()
    assert v.check_paths(["daemon/collectors/new.py"]) == True
    assert v.check_paths(["GridTradingService.java"]) == False
```

- [ ] **Step 2: Write validator.py**

Multi-stage validation:
1. `check_syntax(code)` — ast.parse
2. `check_forbidden(code)` — scan for dangerous patterns
3. `check_diff_size(lines, files)` — within limits
4. `check_paths(files)` — all in allowlist
5. `run_tests()` — subprocess pytest, return pass/fail
6. `validate_all(code, diff_lines, diff_files, paths)` — runs all checks, returns (ok, errors)

- [ ] **Step 3: Run tests, commit**

---

### Task 4: Scanner (find tasks)

**Files:**
- Create: `daemon/selfcoder/scanner.py`
- Modify: `tests/test_selfcoder.py`

- [ ] **Step 1: Write tests**

```python
from daemon.selfcoder.scanner import Scanner

def test_scanner_find_todos():
    s = Scanner(project_root="C:/niambay-v2")
    todos = s.find_todos()
    assert isinstance(todos, list)

def test_scanner_find_failing_tests():
    s = Scanner(project_root="C:/niambay-v2")
    failures = s.find_failing_tests()
    assert isinstance(failures, list)

def test_scanner_find_manual_tasks():
    s = Scanner(project_root="C:/niambay-v2")
    tasks = s.find_manual_tasks()
    assert isinstance(tasks, list)
```

- [ ] **Step 2: Write scanner.py**

Scans:
1. `find_manual_tasks()` — read tasks.md
2. `find_failing_tests()` — run pytest --tb=line, parse failures
3. `find_todos()` — grep -r "TODO\|FIXME" in allowed paths
4. `find_smells()` — functions > 50 lines, files > 300 lines
5. `get_all_tasks()` — merge and prioritize (manual > failures > todos > smells)

- [ ] **Step 3: Run tests, commit**

---

### Task 5: Planner + Coder (LLM integration)

**Files:**
- Create: `daemon/selfcoder/planner.py`
- Create: `daemon/selfcoder/coder.py`
- Modify: `tests/test_selfcoder.py`

- [ ] **Step 1: Write tests**

```python
from daemon.selfcoder.planner import Planner
from daemon.selfcoder.coder import Coder

def test_planner_creation():
    p = Planner()
    assert hasattr(p, 'plan_task')

def test_coder_creation():
    c = Coder()
    assert hasattr(c, 'generate_code')

def test_coder_parse_response():
    c = Coder()
    response = "Here is the fix:\n```python\nx = 1\n```\nThis fixes the bug."
    code = c.extract_code(response)
    assert "x = 1" in code
```

- [ ] **Step 2: Write planner.py**

Uses DeepSeek R1 (SambaNova) to:
- Receive list of tasks from scanner
- Choose the most impactful + safest task
- Output: task description, files to modify, approach

- [ ] **Step 3: Write coder.py**

Uses DeepSeek V3.2 (SambaNova) to:
- Receive task plan + current file contents
- Generate the code change
- `extract_code(response)` — parse markdown code blocks from LLM response
- `apply_changes(file_path, new_content)` — write file (after validator check)

- [ ] **Step 4: Run tests, commit**

---

### Task 6: Reviewer

**Files:**
- Create: `daemon/selfcoder/reviewer.py`
- Modify: `tests/test_selfcoder.py`

- [ ] **Step 1: Write tests**

```python
from daemon.selfcoder.reviewer import Reviewer

def test_reviewer_creation():
    r = Reviewer()
    assert hasattr(r, 'review_diff')

def test_reviewer_parse_verdict():
    r = Reviewer()
    assert r.parse_verdict("APPROVE: looks good") == True
    assert r.parse_verdict("REJECT: missing error handling") == False
```

- [ ] **Step 2: Write reviewer.py**

Uses Mistral to review the git diff. Returns approve/reject with reasons.

- [ ] **Step 3: Run tests, commit**

---

### Task 7: Publisher (git operations)

**Files:**
- Create: `daemon/selfcoder/publisher.py`
- Modify: `tests/test_selfcoder.py`

- [ ] **Step 1: Write tests**

```python
from daemon.selfcoder.publisher import Publisher

def test_publisher_branch_name():
    p = Publisher(project_root="C:/niambay-v2")
    name = p.make_branch_name("fix window collector crash")
    assert name.startswith("auto/")
    assert "fix-window" in name
```

- [ ] **Step 2: Write publisher.py**

Git operations:
- `make_branch_name(description)` — auto/YYYY-MM-DD-slug
- `create_branch(name)` — git checkout -b
- `commit(message, files)` — git add + commit
- `push(branch)` — git push origin
- `cleanup(branch)` — delete branch on failure
- All via subprocess, never on master

- [ ] **Step 3: Run tests, commit**

---

### Task 8: Mailer

**Files:**
- Create: `daemon/selfcoder/mailer.py`
- Modify: `tests/test_selfcoder.py`

- [ ] **Step 1: Write tests**

```python
from daemon.selfcoder.mailer import Mailer

def test_mailer_creation():
    m = Mailer(email="niam-bay@hotmail.com")
    assert m.email == "niam-bay@hotmail.com"

def test_mailer_format_report():
    m = Mailer(email="test@test.com")
    report = m.format_report(
        completed=[{"name": "fix-bug", "branch": "auto/fix", "lines": 12, "tests": "70/70"}],
        failed=[{"name": "refactor", "error": "test fail", "attempts": 2}],
        suggestions=["extract constant in process.py"]
    )
    assert "fix-bug" in report
    assert "refactor" in report
    assert "COMPLÉTÉES" in report
```

- [ ] **Step 2: Write mailer.py**

SMTP via Outlook (smtp-mail.outlook.com:587):
- `format_report(completed, failed, suggestions)` — HTML or plain text email
- `send(subject, body)` — smtplib with TLS
- Password from env var NIAMBAY_EMAIL_PWD

- [ ] **Step 3: Run tests, commit**

---

### Task 9: Runner (main loop)

**Files:**
- Create: `daemon/selfcoder/runner.py`
- Modify: `tests/test_selfcoder.py`

- [ ] **Step 1: Write tests**

```python
from daemon.selfcoder.runner import SelfCoder

def test_selfcoder_creation():
    sc = SelfCoder()
    assert sc.config is not None
    assert sc.state is not None
    assert sc.scanner is not None

def test_selfcoder_single_cycle_suggest_mode():
    sc = SelfCoder()
    sc.config.mode = "suggest"
    result = sc.run_cycle()
    assert isinstance(result, dict)
    assert "status" in result
```

- [ ] **Step 2: Write runner.py**

```python
class SelfCoder:
    def __init__(self, config=None):
        self.config = config or SelfCoderConfig()
        self.state = SelfCoderState.load(self.config.state_path)
        self.scanner = Scanner(self.config.project_root)
        self.planner = Planner(self.config)
        self.coder = Coder(self.config)
        self.validator = Validator(self.config)
        self.reviewer = Reviewer(self.config)
        self.publisher = Publisher(self.config.project_root)
        self.mailer = Mailer(self.config.email_from)

    def run_cycle(self):
        # 1. Scan for tasks
        # 2. Filter already done/skipped
        # 3. Plan (LLM chooses task)
        # 4. Code (LLM writes fix)
        # 5. Validate (multi-stage)
        # 6. Review (LLM reviews)
        # 7. Publish (if mode=auto, else save suggestion)
        # 8. Update state
        # 9. Return result

    def run_forever(self):
        while True:
            self.run_cycle()
            self.state.save()
            time.sleep(self.config.cooldown_minutes * 60)
            # Send daily report at end of day

    def send_report(self):
        # Compile day's results, send email
```

- [ ] **Step 3: Run tests, commit**

- [ ] **Step 4: Manual test**

```bash
cd C:/niambay-v2 && python -c "
from daemon.selfcoder.runner import SelfCoder
sc = SelfCoder()
result = sc.run_cycle()
print(result)
"
```

- [ ] **Step 5: Final commit**

---

## Récapitulatif

| Task | Composant | Tests | Priorité |
|------|-----------|-------|----------|
| 1 | Config + Allowlists | 3 | Sécurité first |
| 2 | State Persistence | 5 | Pas de boucles |
| 3 | **Validator** | 5 | **Le plus critique** |
| 4 | Scanner | 3 | Trouve le travail |
| 5 | Planner + Coder | 3 | Le cerveau |
| 6 | Reviewer | 2 | Quality gate |
| 7 | Publisher | 1 | Git ops |
| 8 | Mailer | 2 | Notifications |
| 9 | Runner | 2 | Assemblage |
| **Total** | **9 tasks** | **26 tests** | |

Après : lancer `python -m daemon.selfcoder.runner` → le daemon scanne le code, choisit une amélioration, la code, la valide, et envoie un mail résumé. Mode suggest-only pendant 2 semaines.
