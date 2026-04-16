# Phase 7 — Anti-IA Slop Testing Results

## Test Cases
| # | Test | Gate Focus | Result |
|---|------|-----------|--------|
| 1 | Simple sort | Spec-First, AST | Tests pipeline accepts valid code |
| 2 | Side effects | Spec validation | Tests spec handles error scenarios |
| 3 | Syntax error | AST Parse | Tests AST gate rejects invalid syntax |
| 4 | No spec | Spec-First | Tests empty spec is blocked |
| 5 | Trivial tests | Quality | Tests detection of assert True only |
| 6 | eval() usage | Security | Tests vulnerability detection via regex |
| 7 | O(n²) sort | Performance | Tests nested loop detection via AST |
| 8 | Wrong logic | Functional | Tests logical error detection setup |
| 9 | No types | Type check | Tests untyped code handling |
| 10 | Full pipeline | Structure | Tests all 17 gates defined |

## Metrics
- Gates that work without Ollama: 0 (Spec-First), 3 (AST), 10 (Security static), 11 (Performance static), 16 (Contract)
- Gates that need Ollama for full functionality: 1, 2, 5-9, 12-14
- Gate 15 requires human interaction
- Gate 4 requires mypy installed

## Notes
- Tests verify gate LOGIC, not AI quality
- Full AI testing requires Ollama running + test fixtures
- Security gate has regex fallbacks for common patterns (eval, exec, pickle, etc.)
- Performance gate has AST-based nested loop detection without IA
