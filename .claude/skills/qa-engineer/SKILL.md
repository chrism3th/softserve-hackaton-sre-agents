---
name: qa-engineer
description: Use when writing or reviewing tests, designing test strategies, debugging flaky tests, or assessing test coverage and quality. Covers unit, integration, e2e, and agent/LLM evaluations.
---

# QA Engineer Skill

Tests exist to give you the courage to change code. If they don't, they're wrong.

## The Test Pyramid (still valid)

```
        /\       e2e (few, slow, high value)
       /  \
      /----\     integration (some)
     /      \
    /--------\   unit (many, fast)
```

- **Unit**: one function/class, no I/O, <100ms each, milliseconds total.
- **Integration**: real DB, real HTTP, real queue — but mocked external APIs.
- **End-to-end**: full stack via the UI or the top-level API. Use sparingly.

Invert this and your suite becomes slow, flaky, and feared.

## What Makes a Good Test

- **Fast.** Slow tests get skipped.
- **Isolated.** No dependency on order, no shared state.
- **Repeatable.** Same result in CI and locally, today and next month.
- **Self-validating.** Pass or fail, no human inspection of output.
- **Timely.** Written with the code, not "added later".

(FIRST: Fast, Isolated, Repeatable, Self-validating, Timely)

## Test Naming

```python
def test_<subject>_<scenario>_<expected_result>():
    ...

def test_parse_date_invalid_format_raises_valueerror():
    ...
```

A failing test name should explain the bug.

## Arrange / Act / Assert

```python
def test_transfer_moves_funds():
    # Arrange
    sender = Account(balance=100)
    receiver = Account(balance=0)

    # Act
    transfer(sender, receiver, amount=30)

    # Assert
    assert sender.balance == 70
    assert receiver.balance == 30
```

One "act" per test. Multiple asserts are fine if they verify the same action.

## Fixtures & Factories

- Shared setup → `pytest` fixtures.
- Test data → factory functions (`make_user()`) or libraries like `factory-boy`, `Faker`.
- Never reuse DB state between tests. Use transactions that roll back, or truncate tables.

## Mocking

- Mock at the **boundary** of your system, not deep internals.
- Prefer **fakes** (working in-memory implementations) over mocks.
- Mock HTTP with `respx`/`responses`, not by patching `requests` internals.
- If a test has 5+ mocks, the code under test is doing too much.

## Property-Based Testing

For pure functions and parsers, add `hypothesis`:

```python
from hypothesis import given, strategies as st

@given(st.text())
def test_roundtrip(s):
    assert decode(encode(s)) == s
```

Finds edge cases humans miss: empty strings, unicode, large inputs.

## Integration Tests

- Run against real services in Docker (the same `docker-compose` used for dev).
- Use `testcontainers` for ephemeral DB/queue/cache per test session.
- Reset state per test (transaction rollback for SQL, flushall for Redis).
- Assert on observable behavior, not internal state.

## End-to-End

- Playwright > Cypress > Selenium (2026 consensus).
- Test **critical user journeys**, not every page.
- Deterministic: no real dates, no flaky selectors. Prefer `data-testid` attributes.
- Run against a seeded, reproducible backend.

## Testing LLM / Agent Code

- **Deterministic tests**: mock the LLM, assert on tool calls, routing, error handling.
- **Eval suite** (separate from unit tests): golden dataset + LLM-as-judge. Run nightly, not on every commit.
- **Smoke test**: one real API call to catch model/endpoint breakage.
- **Replay tests**: record real transcripts, replay them to verify logic hasn't regressed.
- Track **cost and latency** as test outputs.

## Coverage

- Coverage is a **floor indicator**, not a goal. 100% of trivial getters is worthless.
- 80% line coverage with meaningful assertions > 100% with `assert result is not None`.
- Focus coverage on branches and business logic, not trivial code.
- **Branch coverage** matters more than line coverage.

## Flaky Tests

- **Never** retry a flaky test to make CI green. Root cause or delete.
- Common causes: real time (`time.sleep`, `now()`), order dependency, shared state, network, random seeds.
- Freeze time (`freezegun`). Fix seeds. Isolate state. Remove network from unit tests.
- Quarantine flaky tests in a separate job; don't let them block the pipeline; fix them within a week.

## Test Review Checklist

- [ ] Does the test fail if I break the code? (Mutation testing is gold.)
- [ ] Is it testing behavior or implementation?
- [ ] Would a new hire understand what's being verified?
- [ ] No sleeps, no real network, no real clock?
- [ ] Fixtures not reused beyond their purpose?
- [ ] Assert messages are meaningful?

## Anti-Patterns

- Asserting on log messages (brittle).
- Tests that mirror the implementation line-for-line (test and code change together).
- `assert True` placeholders committed.
- Giant `conftest.py` no one understands.
- Running the whole suite serially because "parallel causes issues".
- `sleep(5)` waiting for an async operation.
- "This test is flaky, just rerun it".
