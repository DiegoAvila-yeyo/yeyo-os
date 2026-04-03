# Agent Quality Standards & Checklist

**Version:** 1.0  
**For:** Phase 3+ Agent Development  
**Last Updated:** 2026-04-02  

---

## 🎯 QUALITY GATES (Must Pass ALL Before Merge)

### **Gate 1: Syntax & Imports** ✅
- [ ] File compiles with `python -m py_compile`
- [ ] No undefined names or import errors
- [ ] All imports at **module level** (not inside methods)
- [ ] Imports ordered: stdlib → typing → local
- [ ] Example:
  ```python
  import re
  from typing import Any, Dict, List
  from src.agents.base import Agent, AgentInput
  ```

### **Gate 2: Type Hints** ✅
- [ ] All method signatures have type hints
- [ ] Use `List[str]` not `list[str]` (for 3.9+ compatibility)
- [ ] Use `Dict[str, Any]` for dicts
- [ ] Use `tuple[bool, str]` for tuple returns
- [ ] All parameters typed
- [ ] All returns typed
- [ ] Example:
  ```python
  def validate_input(self, agent_input: AgentInput) -> tuple[bool, str]:
  def suggest_improvements(self, response: str, input_context: Dict[str, Any]) -> List[str]:
  ```

### **Gate 3: Docstrings** ✅
- [ ] Class has docstring (one-liner)
- [ ] All public methods have docstrings
- [ ] Docstrings describe purpose, not obvious
- [ ] Docstrings in Spanish
- [ ] Example:
  ```python
  class MyAgent(Agent):
      """Agente especializado en X."""
      
      def validate_input(self, agent_input: AgentInput) -> tuple[bool, str]:
          """Valida que sea descriptor de X."""
  ```

### **Gate 4: Base Class Compliance** ✅
- [ ] Inherits from `Agent`
- [ ] Implements all 6 abstract methods:
  1. `__init__()`
  2. `get_system_prompt(context: Dict[str, Any]) -> str`
  3. `validate_input(agent_input: AgentInput) -> tuple[bool, str]`
  4. `validate_output(response: str) -> tuple[bool, str]`
  5. `calculate_confidence(response: str, input_context: Dict[str, Any]) -> float`
  6. `suggest_improvements(response: str, input_context: Dict[str, Any]) -> List[str]`
- [ ] `__init__()` calls `super().__init__(name="...", domain="...")`
- [ ] All methods return correct types

### **Gate 5: Input Validation** ✅
- [ ] `validate_input()` checks length (min 10-20 chars typically)
- [ ] `validate_input()` checks for domain-specific keywords
- [ ] `validate_input()` handles None gracefully
- [ ] `validate_input()` handles empty string
- [ ] Returns `tuple[bool, str]` always (bool is result, str is error message)
- [ ] Example:
  ```python
  def validate_input(self, agent_input: AgentInput) -> tuple[bool, str]:
      if not agent_input.content or len(agent_input.content.strip()) < 15:
          return False, "Entrada muy corta"
      
      if "keyword" not in agent_input.content.lower():
          return False, "Falta contexto (menciona 'keyword')"
      
      return True, ""
  ```

### **Gate 6: Output Validation** ✅
- [ ] `validate_output()` checks minimum length (50-100 chars)
- [ ] `validate_output()` uses regex for specific patterns (NOT generic)
- [ ] `validate_output()` checks for required sections
- [ ] NO `any(c.isdigit() for c in text)` - use `re.search(pattern, text)` instead
- [ ] Returns `tuple[bool, str]` with accurate error message
- [ ] Example:
  ```python
  def validate_output(self, response: str) -> tuple[bool, str]:
      if not response or len(response.strip()) < 50:
          return False, "Respuesta muy corta"
      
      has_rating = bool(re.search(r'\b\d+\s*[/-]\s*10\b|\[\d+/10\]|\d+%', response))
      if not has_rating:
          return False, "Falta calificación/score"
      
      has_analysis = "análisis" in response.lower() or "evaluación" in response.lower()
      if not has_analysis:
          return False, "Falta análisis profundo"
      
      return True, ""
  ```

### **Gate 7: Confidence Scoring** ✅
- [ ] Confidence is `float` between 0.0 and 1.0
- [ ] Base confidence reasonable for domain (0.6-0.7 typical)
- [ ] Bonuses are additive and documented
- [ ] Final calculation: `min(1.0, base_conf + bonuses)`
- [ ] Mathematical check: max possible = 1.0
- [ ] Example:
  ```python
  def calculate_confidence(self, response: str, input_context: Dict[str, Any]) -> float:
      base_conf = 0.65  # Domain baseline
      
      if "SECCIÓN" in response:
          base_conf += 0.15  # Now 0.80
      if "#" in response:
          base_conf += 0.1   # Now 0.90
      
      return min(1.0, base_conf)  # Clamp to 1.0
  ```

### **Gate 8: Suggestions** ✅
- [ ] Returns `List[str]` (not empty list always)
- [ ] Suggestions are actionable (not vague)
- [ ] 2-5 suggestions typically (not 10+)
- [ ] Each suggestion specific and helpful
- [ ] Example:
  ```python
  def suggest_improvements(self, response: str, input_context: Dict[str, Any]) -> List[str]:
      suggestions = []
      
      if "ANÁLISIS" not in response:
          suggestions.append("Incluye sección de ANÁLISIS")
      
      if len(response) < 200:
          suggestions.append("Expande con más detalles específicos")
      
      if "#" not in response and "color" in response.lower():
          suggestions.append("Especifica colores con hex (#RRGGBB)")
      
      return suggestions
  ```

### **Gate 9: Regex Patterns** ✅
- [ ] All regex patterns tested with unit tests
- [ ] Patterns have "should match" test cases
- [ ] Patterns have "should NOT match" false-positive cases
- [ ] Patterns use word boundaries `\b` when appropriate
- [ ] Patterns use `re.IGNORECASE` when needed
- [ ] No overly generic patterns (like `any(c.isdigit() for c in text)`)
- [ ] Tested patterns:
  ```python
  # ✅ GOOD: Specific, tested
  re.search(r'\b\d+\s*[/-]\s*10\b|\[\d+/10\]|\d+%', response)
  
  # ❌ BAD: Too generic
  any(c.isdigit() for c in response[:100])
  ```

### **Gate 10: Context Handling** ✅
- [ ] Uses `context.get("key", default)` for all dictionary access
- [ ] Never assumes dictionary keys exist
- [ ] Defaults are sensible for the domain
- [ ] Example:
  ```python
  def get_system_prompt(self, context: Dict[str, Any]) -> str:
      platform = context.get("platform", "general").lower()  # Safe!
      style = context.get("style", "professional")
      # Won't crash if keys missing
  ```

### **Gate 11: Error Messages** ✅
- [ ] Error messages accurately describe the problem
- [ ] Messages match the condition logic
- [ ] No misleading messages
- [ ] Example:
  ```python
  # ✅ Accurate
  if not (has_A or has_B):
      return False, "Falta A y/o B"
  
  # ❌ Misleading
  if not (has_A or has_B):
      return False, "Falta A o B"  # Doesn't say both missing
  ```

### **Gate 12: Consistency** ✅
- [ ] Agent follows same patterns as other agents
- [ ] Same validation approach as peers
- [ ] Error message format consistent
- [ ] Bonus calculation strategy similar
- [ ] Method ordering consistent

---

## 📋 PRE-COMMIT CHECKLIST

Before pushing any agent code:

```bash
□ Run syntax check:
  python -m py_compile src/agents/your_agent.py

□ Run type check:
  mypy src/agents/your_agent.py --ignore-missing-imports

□ Run your tests:
  pytest tests/agents/test_your_agent.py -v

□ Check linter:
  pylint src/agents/your_agent.py

□ Manual review (checklist items 1-12):
  Review all 12 gates above

□ Read through your code once more:
  Look for obvious bugs, inefficiencies, typos
```

---

## 🧪 REQUIRED TEST SUITE

Every agent MUST have comprehensive tests. Create file: `tests/agents/test_{agent_name}.py`

### **Test Structure**
```python
import pytest
from src.agents.{agent_name} import {AgentName}Agent
from src.agents.base import AgentInput

@pytest.fixture
def agent():
    return {AgentName}Agent()

class TestValidateInput:
    def test_valid_input(self, agent):
        """Debe aceptar entrada válida."""
        result, msg = agent.validate_input(AgentInput(content="contenido válido con contexto"))
        assert result is True
        assert msg == ""
    
    def test_too_short(self, agent):
        """Debe rechazar entrada muy corta."""
        result, msg = agent.validate_input(AgentInput(content="corta"))
        assert result is False
        assert "corta" in msg.lower()
    
    def test_missing_context(self, agent):
        """Debe rechazar entrada sin contexto necesario."""
        result, msg = agent.validate_input(AgentInput(content="solo texto genérico"))
        assert result is False

class TestValidateOutput:
    def test_valid_output(self, agent):
        """Debe aceptar salida válida."""
        response = "ANÁLISIS COMPLETO\n\nSección 1: Descripción\nSección 2: Evaluación"
        result, msg = agent.validate_output(response)
        assert result is True
    
    def test_too_short(self, agent):
        """Debe rechazar respuesta muy corta."""
        result, msg = agent.validate_output("corta")
        assert result is False

    def test_incomplete_structure(self, agent):
        """Debe rechazar estructura incompleta."""
        response = "Algo pero incompleto"
        result, msg = agent.validate_output(response)
        assert result is False

class TestConfidenceScoring:
    def test_confidence_range(self, agent):
        """Confianza debe estar entre 0.0 y 1.0."""
        response = "alguna respuesta"
        conf = agent.calculate_confidence(response, {})
        assert 0.0 <= conf <= 1.0
    
    def test_confidence_never_exceeds_one(self, agent):
        """Confianza nunca debe exceder 1.0."""
        # Prueba con respuesta "perfecta"
        perfect_response = "SECCIÓN " * 20 + "#FFFF00" * 20 + "✓" * 20
        conf = agent.calculate_confidence(perfect_response, {})
        assert conf <= 1.0

class TestSuggestImprovements:
    def test_returns_list(self, agent):
        """Siempre retorna List[str]."""
        suggestions = agent.suggest_improvements("respuesta", {})
        assert isinstance(suggestions, list)
        assert all(isinstance(s, str) for s in suggestions)
    
    def test_sensible_suggestions(self, agent):
        """Sugerencias son útiles y específicas."""
        incomplete_response = "algo incompleto"
        suggestions = agent.suggest_improvements(incomplete_response, {})
        # Debe sugerir algo
        assert len(suggestions) > 0
        # Sugerencias no deben ser vagas
        assert not any("mejorar" in s.lower() and len(s) < 20 for s in suggestions)

class TestRegexPatterns:
    """Pruebas específicas para patrones regex."""
    
    def test_pattern_matches_valid(self, agent):
        """Patrón debe coincidir con input válido."""
        # Ejemplo: si esperas puntuación
        response = "Puntuación: 8/10"
        # Verifica que tu regex la detecte
        import re
        assert re.search(r'\b\d+\s*[/-]\s*10\b', response)
    
    def test_pattern_no_false_positives(self, agent):
        """Patrón NO debe coincidir con falsos positivos."""
        # Ejemplo: "ejemplo" no debe coincidir con patrón que busca "x"
        import re
        assert not re.search(r'\d+\s*x\s*\d+', "esto es un ejemplo")
```

---

## 🔄 CODE REVIEW CHECKLIST

Reviewer should verify:

- [ ] All 12 gates pass
- [ ] Tests are comprehensive
- [ ] No copy-paste errors
- [ ] Docstrings clear and accurate
- [ ] No hardcoded values (use defaults)
- [ ] Error messages helpful
- [ ] Performance reasonable
- [ ] No dead code
- [ ] Follows team patterns

---

## 📊 AGENT SCORECARD

Before merge, fill out:

```
AGENT NAME: _______________
DATE: _______________
REVIEWER: _______________

SCORING (0-10):
  Completeness:      __ (All methods implemented)
  Type Safety:       __ (All type hints present)
  Validation:        __ (Input/output validation strong)
  Regex Robustness:  __ (Patterns tested, no false positives)
  Error Messages:    __ (Accurate and helpful)
  Test Coverage:     __ (Tests comprehensive)
  Documentation:     __ (Clear and complete)
  Code Quality:      __ (Clean, efficient, consistent)
  
TOTAL SCORE: __ / 80

MINIMUM REQUIRED: 70/80

BLOCKERS (must fix before merge):
  [ ] None
  [ ] List any showstoppers...

APPROVED: __ (Initial only) / __ (Reviewer sign-off)
```

---

## 🚀 DEPLOYMENT CHECKLIST

Before agent goes to production:

- [ ] All 12 quality gates passed
- [ ] Score is 70+/80
- [ ] Code reviewed by 2+ people
- [ ] Tests pass 100%
- [ ] No linter warnings
- [ ] Merged to main branch
- [ ] Documented in AGENTS.md
- [ ] Team notified

---

## 📖 DOCUMENTATION REQUIRED

Each agent must have:

### `src/agents/{name}.py`
- Class docstring
- Method docstrings
- Type hints complete
- Comments on complex logic

### `AGENTS.md` (Team Reference)
```markdown
## {AgentName}Agent

**Domain:** {domain}  
**Purpose:** {purpose}  
**Confidence Base:** {base_conf}  

### Input
- Expects: {description}
- Minimum length: {min}
- Required keywords: {keywords}

### Output
- Returns: {description}
- Validation: {checks}
- Example: {example}

### Context Parameters
- {param1}: {description}
- {param2}: {description}

### Bonus Logic
- {bonus1}: +{amount}
- {bonus2}: +{amount}

### Known Limitations
- {limitation1}
- {limitation2}
```

---

## 🎓 ANTI-PATTERNS (DON'T DO THIS)

### ❌ Generic Validation
```python
# BAD
any(c.isdigit() for c in response[:100])

# GOOD
re.search(r'\b\d+\s*[/-]\s*10\b|\[\d+/10\]', response)
```

### ❌ Lazy Imports
```python
# BAD
def calculate_confidence(self, response):
    import re
    if re.search(...):

# GOOD
import re  # At module level
def calculate_confidence(self, response):
    if re.search(...):
```

### ❌ Mixed Type Hints
```python
# BAD
-> list[str]:  # Python 3.10+ only

# GOOD
-> List[str]:  # Compatible with 3.9+
from typing import List
```

### ❌ Redundant Conditions
```python
# BAD
if "PRÓXIMO" in response or "próximo" in response.lower():

# GOOD
if "próximo" in response.lower():
```

### ❌ Tight Confidence Math
```python
# BAD - No headroom for improvements
0.6 + 0.15 + 0.15 + 0.1 = 1.0

# GOOD - Room to add more bonuses
0.6 + 0.1 + 0.08 + 0.05 = 0.83
return min(1.0, base_conf)
```

### ❌ Misleading Error Messages
```python
# BAD
if not (has_A or has_B):
    return False, "falta A o B"  # Doesn't match logic!

# GOOD
if not (has_A or has_B):
    return False, "falta A y/o B"
```

---

## ✅ QUALITY GATES SUMMARY

```
┌──────────────────────────────────────────┐
│  AGENT QUALITY GATES (Must Pass ALL)     │
├──────────────────────────────────────────┤
│ 1. Syntax & Imports                   ✓  │
│ 2. Type Hints                         ✓  │
│ 3. Docstrings                         ✓  │
│ 4. Base Class Compliance              ✓  │
│ 5. Input Validation                   ✓  │
│ 6. Output Validation                  ✓  │
│ 7. Confidence Scoring                 ✓  │
│ 8. Suggestions                        ✓  │
│ 9. Regex Patterns                     ✓  │
│ 10. Context Handling                  ✓  │
│ 11. Error Messages                    ✓  │
│ 12. Consistency                       ✓  │
├──────────────────────────────────────────┤
│ IF ALL ✓ → PRODUCTION READY             │
└──────────────────────────────────────────┘
```

---

## 📞 QUESTIONS?

Reference this checklist before coding. Follow it during development. Verify all gates before commit.

**Goal: ZERO bugs in Phase 3 agents.**

**Previous stats:** 37 bugs in Phase 2 (all preventable)  
**Target:** 0-1 bugs in Phase 3 (with this checklist)
