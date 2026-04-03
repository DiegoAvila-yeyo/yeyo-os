# Phase 3.1.1: ChatNode → ConversationAgent Integration

## 📋 DESIGN DOCUMENT

**Objetivo:** Wire ChatNode al ConversationAgent de forma robusta

---

## 🏗️ ARQUITECTURA

### Current State
```
ChatNode (Capa 5)
├─ Tiene conversaciones
├─ Tiene mensajes
└─ Llama ContextualChatService (Capa 2)
  └─ [BLACK BOX - no integrado con agentes]

ConversationAgent (Capa 3)
├─ Tiene lógica especializada
├─ Genera system prompts
├─ Valida input/output
└─ Calcula confidence
  └─ [NO CONECTADO A NADA]
```

### After Integration
```
ChatNode (Capa 5)
├─ Recibe input del usuario
├─ Llama ChatNodeService.process()
│   └─ Valida input (robustamente)
│   └─ Inyecta contexto de memoria
│   └─ Llama ConversationAgent.get_system_prompt()
│   └─ Llama OllamaService.generate(system_prompt, user_input)
│   └─ Valida output con ConversationAgent.validate_output()
│   └─ Calcula confidence
│   └─ Guarda en memoria
│   └─ Retorna respuesta + metadata
└─ Usuario recibe respuesta con confianza y sugerencias
```

---

## 📝 INTERFACE

### Input
```python
{
    "message": "str",                    # required, non-empty, <= 10000 chars
    "conversation_id": "str",            # optional, existing conv
    "tone": "professional|casual|...",   # optional, default="professional"
    "conversation_type": "support|info|...",  # optional
}
```

### Output (Success)
```python
{
    "response": "str",                   # LLM response
    "confidence": float,                 # 0.0-1.0
    "reasoning": "str",                  # why this confidence
    "suggestions": List[str],            # improvements for user
    "tokens_used": int,                  # for monitoring
    "conversation_id": "str",            # the conversation
    "message_id": "str",                 # new message ID
}
```

### Output (Error)
```python
{
    "error": "str",                      # error message
    "error_code": "str",                 # error_invalid_input, error_timeout, etc
    "conversation_id": "str",            # context for debugging
}
```

---

## 🛡️ VALIDATION LAYERS

### Layer 1: Input Validation
```python
✓ message non-empty
✓ message <= 10000 chars (prevent DoS)
✓ message valid UTF-8
✓ no null bytes
✓ conversation_id exists (if provided)
✓ tone valid enum
✓ conversation_type valid enum
```

### Layer 2: Context Injection
```python
✓ Load conversation history (last 20 messages)
✓ Load user profile/preferences from memory
✓ Load conversation tone/type
✓ Calculate conversation statistics
  ├─ message count
  ├─ duration
  ├─ average response time
  └─ previous confidence scores
```

### Layer 3: Agent Validation
```python
✓ ConversationAgent.validate_input() passed
✓ System prompt generated successfully
✓ Return type is string
```

### Layer 4: Ollama Call
```python
✓ Timeout: 30 seconds
✓ Retry: 3 attempts with exponential backoff
✓ Resource check: memory available
✓ Connection: verify Ollama is running
```

### Layer 5: Output Validation
```python
✓ Response non-empty
✓ Response valid UTF-8
✓ ConversationAgent.validate_output() passed
✓ Confidence in [0.0, 1.0]
```

### Layer 6: Error Handling
```python
✓ Try/catch with specific exceptions
✓ Log all errors (without secrets)
✓ Return user-friendly error message
✓ Include error_code for debugging
✓ No stack traces exposed to user
```

---

## 📊 TESTING STRATEGY

### Unit Tests (50+ test cases)

**Input Validation**
- [ ] Valid message
- [ ] Empty message → error
- [ ] Very long message (10000+ chars) → error
- [ ] Unicode characters (emoji, CJK) → valid
- [ ] Null bytes → error
- [ ] Invalid conversation_id → error
- [ ] Invalid tone → error
- [ ] Missing required fields → error
- [ ] Extra fields (should be ignored)

**Agent Integration**
- [ ] System prompt generation correct
- [ ] Agent.validate_input() called
- [ ] Agent.validate_output() called
- [ ] Confidence calculation correct
- [ ] Suggestions generated

**Ollama Integration**
- [ ] Ollama responds
- [ ] Timeout handled (30s)
- [ ] Retry works (3x)
- [ ] Connection error handled
- [ ] Resource exhaustion handled

**Output Formatting**
- [ ] Response JSON valid
- [ ] All required fields present
- [ ] Confidence in valid range
- [ ] No secrets in response

### Integration Tests (20+ test cases)

**End-to-End Flow**
- [ ] User message → Response (happy path)
- [ ] Conversation context preserved
- [ ] Message history updated
- [ ] Memory injection works
- [ ] Multiple conversations isolated

**Error Scenarios**
- [ ] Ollama timeout → graceful error
- [ ] Invalid input → 400 error
- [ ] Agent validation fails → error
- [ ] GPU out of memory → error
- [ ] Database error → error

**Concurrency**
- [ ] 10 concurrent messages same conversation
- [ ] 10 concurrent conversations
- [ ] Message ordering preserved
- [ ] No race conditions

### Stress Tests (5+ scenarios)

- [ ] 1000 messages in single conversation
- [ ] 100 conversations simultaneously
- [ ] Very long messages (5000+ chars)
- [ ] Very short messages (1 char)
- [ ] Rapid-fire messages (100/sec)

### Security Tests (15+ attack scenarios)

- [ ] SQL injection in message
- [ ] XSS payload in message
- [ ] Command injection
- [ ] Path traversal
- [ ] Resource exhaustion (memory bomb)
- [ ] Token stuffing
- [ ] Large Unicode exploit
- [ ] Malformed JSON

---

## 📈 PERFORMANCE TARGETS

```
Latency:
├─ p50: < 500ms
├─ p95: < 2s
└─ p99: < 5s

Throughput:
├─ 100 req/sec minimum
└─ No degradation with 1000 concurrent

Memory:
├─ Per-request: < 50MB
├─ Memory leak tests: stable after 1000 requests
└─ No unbounded growth

Error Rate:
├─ < 0.1% (1 in 1000)
└─ All errors properly logged
```

---

## 🔐 SECURITY CHECKLIST

- [ ] Input sanitized (no injection vectors)
- [ ] Output encoded (no XSS)
- [ ] CSRF tokens (if applicable)
- [ ] Rate limiting (100 req/min per user)
- [ ] Error messages don't leak system info
- [ ] No secrets in logs
- [ ] Timeout enforced (prevent DoS)
- [ ] Resource limits enforced
- [ ] Authentication verified
- [ ] Authorization verified

---

## 📚 DOCUMENTATION

### Code Documentation
- [ ] Module docstring
- [ ] Class docstring (ChatNodeService)
- [ ] Method docstrings (with examples)
- [ ] Parameter type hints
- [ ] Return type hints
- [ ] Exception documentation
- [ ] Inline comments for complex logic

### User Documentation
- [ ] API endpoint description
- [ ] Request/response examples
- [ ] Error codes and meanings
- [ ] Rate limits
- [ ] Common mistakes
- [ ] Troubleshooting guide
- [ ] Performance tips

### Architecture Documentation
- [ ] Design decisions recorded
- [ ] Why ConversationAgent is used
- [ ] Integration flow diagram
- [ ] Memory injection explained
- [ ] Timeout/retry strategy explained
- [ ] Edge cases documented

---

## ✅ APPROVAL CRITERIA

Before moving to next node (CodeNode):

1. **Tests**
   - [x] 100% test coverage
   - [x] All 50+ unit tests GREEN
   - [x] All 20+ integration tests GREEN
   - [x] All 5+ stress tests GREEN
   - [x] All 15+ security tests GREEN

2. **Code Quality**
   - [x] All Gates 1-20 PASS
   - [x] No unused variables
   - [x] No logic errors
   - [x] Type hints complete
   - [x] Docstrings complete

3. **Security**
   - [x] Security audit PASSED
   - [x] No injection vectors
   - [x] Error handling complete
   - [x] No secrets leaked
   - [x] Resource limits enforced

4. **Performance**
   - [x] Latency < 5s (p99)
   - [x] Throughput > 100 req/sec
   - [x] Memory stable (no leaks)
   - [x] Baseline established

5. **Documentation**
   - [x] Code documented
   - [x] API documented
   - [x] Examples provided
   - [x] Troubleshooting guide
   - [x] Architecture decisions recorded

6. **Code Review**
   - [x] Reviewed by 2+ developers
   - [x] All comments resolved
   - [x] Approved by maintainer

---

## 🚀 IMPLEMENTATION PLAN

### Step 1: ChatNodeService Implementation
- Create `src/nodes/chat/service_integration.py`
- Implement ChatNodeService class
- Input validation
- Agent integration
- Error handling

### Step 2: Unit Tests
- Create `tests/nodes/chat/test_service_integration.py`
- 50+ test cases
- 100% coverage

### Step 3: Integration Tests
- Create `tests/nodes/chat/test_integration_e2e.py`
- End-to-end flows
- Concurrency tests
- Error scenarios

### Step 4: Security Tests
- Create `tests/security/test_chat_injection.py`
- 15+ attack scenarios
- Validation tests

### Step 5: Performance Tests
- Create `tests/performance/test_chat_latency.py`
- Latency benchmarks
- Throughput tests
- Memory profiling

### Step 6: Documentation
- Docstrings in code
- API docs (OpenAPI spec)
- Troubleshooting guide
- Examples

### Step 7: Code Review
- Self-review + Gates 1-20
- Peer review (2+ developers)
- Feedback incorporation

### Step 8: Approval
- All criteria met
- Ready for CodeNode integration

---

## 📊 DELIVERABLES

```
src/nodes/chat/
├─ service_integration.py         (ChatNodeService - 200-300 lines)
├─ types.py                       (Input/output types)
└─ exceptions.py                  (Custom exceptions)

tests/nodes/chat/
├─ test_service_integration.py    (Unit tests - 500+ lines)
├─ test_integration_e2e.py        (E2E tests - 300+ lines)
└─ test_security.py               (Security tests - 200+ lines)

tests/performance/
└─ test_chat_latency.py          (Performance tests - 150+ lines)

docs/
├─ api_chat_integration.md        (API docs)
├─ chat_architecture.md           (Architecture)
└─ chat_troubleshooting.md        (Troubleshooting)
```

---

## ⏱️ TIMELINE (Complexity-based, not time-based)

This is "robusto" work:
- Implementation: Simple (AI can do)
- Testing: Hard (need to think of all cases)
- Documentation: Medium (need clarity)
- Code Review: Medium (need thoroughness)

**Total effort:** Until it passes all criteria (quality > speed)
