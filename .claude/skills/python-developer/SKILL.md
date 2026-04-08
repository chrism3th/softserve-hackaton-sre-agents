---
name: python-developer
description: Use when writing, refactoring, debugging, or reviewing Python code. Covers packaging, type hints, testing, async, and the modern Python toolchain (uv/ruff/mypy/pytest).
---

# Python Developer Skill

Write modern, idiomatic Python 3.11+. Prefer standard library when it's sufficient.

## Project Layout (src-layout)

```
pkg/
├── pyproject.toml
├── src/
│   └── my_package/
│       ├── __init__.py
│       └── module.py
└── tests/
    └── test_module.py
```

Always use `src-layout`. It prevents accidental imports from the project root and forces tests to use the installed package.

## Toolchain (prefer in this order)

- **Package manager**: `uv` (fast) > `pip` + `pip-tools`.
- **Linter + formatter**: `ruff` (replaces black, isort, flake8, pyupgrade).
- **Type checker**: `mypy` in strict mode, or `pyright`.
- **Test runner**: `pytest` + `pytest-asyncio` + `pytest-cov`.
- **Task runner**: `make` or `just`.

## Style Rules

- **Type hints everywhere.** Use `from __future__ import annotations` at top of files.
- **f-strings** for formatting. Never `%` or `.format()`.
- **`pathlib.Path`** not `os.path`.
- **`dataclasses`** or **`pydantic`** for structured data, not dicts.
- **`enum.Enum`** for fixed sets of values.
- **Context managers** for resources (`with open(...)`, `with Session() as s`).
- **Generators / iterators** for large data, never materialize a million-row list.

## Error Handling

```python
# Good
try:
    result = risky_call()
except SpecificError as e:
    logger.exception("risky_call failed for %s", context)
    raise DomainError("user-friendly message") from e

# Bad
try:
    result = risky_call()
except Exception:  # too broad
    pass  # silent failure
```

- Catch the narrowest exception that makes sense.
- Always `raise ... from e` to preserve chain.
- Never `except: pass`.

## Async

- Don't mix sync and async in the same function. If you need sync inside async, use `asyncio.to_thread()` or `run_in_executor`.
- For HTTP: `httpx.AsyncClient` with a reused client, not `requests`.
- Use `asyncio.TaskGroup` (3.11+) for structured concurrency.
- Avoid `asyncio.gather` without `return_exceptions=True` unless you want fail-fast.

## Testing

- **Arrange / Act / Assert** structure.
- One logical assertion per test (multiple `assert` lines OK if related).
- Use `pytest` fixtures for setup; avoid `setUp`/`tearDown` unittest style.
- Use `pytest.mark.parametrize` for table-driven tests.
- Mock at the boundary, not deep internals. Prefer `respx` or `responses` for HTTP.
- Target meaningful coverage (~80%) — don't chase 100% by testing trivia.

## Logging

```python
import logging
logger = logging.getLogger(__name__)

# lazy format, no f-string inside log call
logger.info("processed user=%s items=%d", user_id, count)
```

- Configure once in `main.py` / entrypoint, never in library code.
- Use `logger.exception(...)` inside `except` to capture traceback.
- Never log secrets, tokens, passwords, or full auth headers.

## Performance / Pitfalls

- Avoid mutable default arguments: `def f(x=[])` → `def f(x=None): x = x or []`.
- Beware late-binding in lambdas inside loops: use `lambda i=i: ...`.
- Avoid `==` on floats; use `math.isclose`.
- Prefer `in` for membership on sets/dicts (O(1)), not lists (O(n)).

## Anti-Patterns

- `from module import *`
- Monkey-patching in production code
- `eval`/`exec` on untrusted input
- Mixing tabs and spaces (ruff will catch this)
- `time.sleep` in tests (use `freezegun` or fake clocks)
