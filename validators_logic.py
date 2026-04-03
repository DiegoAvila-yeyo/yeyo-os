"""
Enhanced QA System - Logic Bug Validators
Gates 13-20: Logic, Design, and Completeness Validation

These validators detect bugs that the original 12 gates cannot:
- Unused code
- Incomplete features
- Logic inconsistencies
- Design violations
- Poor error messages
- Incomplete validation
"""

import re
import ast
from typing import Tuple, List, Dict, Set
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of a validation check"""
    passed: bool
    message: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL


# ============================================================================
# GATE 13: Unused Code Detection
# ============================================================================

def validate_unused_code(agent_code: str) -> ValidationResult:
    """
    Detect patterns, indicators, or configs defined but never used.
    
    Example:
        self.dangerous_patterns = [...]  # Defined
        # Never referenced anywhere else
    """
    
    try:
        tree = ast.parse(agent_code)
    except SyntaxError:
        return ValidationResult(False, "Syntax error", "HIGH")
    
    unused_vars = []
    
    # Find all self.X assignments in __init__
    defined_vars = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Attribute):
                    if isinstance(target.value, ast.Name) and target.value.id == "self":
                        defined_vars.add(target.attr)
    
    # Find all self.X references in other methods
    used_vars = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id == "self":
                used_vars.add(node.attr)
    
    # Check for unused (defined but not used)
    unused = defined_vars - used_vars
    
    # Filter out common okay vars
    ignored = {"name", "domain", "_enabled"}
    unused = unused - ignored
    
    if unused:
        return ValidationResult(
            False,
            f"Unused instance variables: {', '.join(sorted(unused))}. "
            f"These are defined but never used: {', '.join(sorted(unused))}",
            "HIGH"
        )
    
    return ValidationResult(True, "No unused code detected", "LOW")


# ============================================================================
# GATE 14: Feature Completeness
# ============================================================================

def validate_feature_completeness(agent_code: str) -> ValidationResult:
    """
    Ensure all features mentioned in docstring are actually implemented.
    
    Example:
        '''Detects bias indicators'''
        
        self.bias_indicators = {...}  # Defined but...
        # Never validated anywhere in the code
    """
    
    # Extract docstring
    docstring = ""
    tree = ast.parse(agent_code)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if node.name.endswith("Agent"):
                docstring = ast.get_docstring(node) or ""
                break
    
    if not docstring:
        return ValidationResult(True, "No docstring to validate against", "LOW")
    
    # Extract features mentioned
    features = []
    
    # Pattern: "- [feature]" or "* [feature]" or "[Feature]:"
    feature_patterns = [
        r"[-*]\s+([A-Z][^:\n]*?)(?:\s*:|$)",
        r"([A-Z][a-z]+\s+[a-z]+(?:\s+[a-z]+)?)",
        r"(?:detect|check|validate|implement)(?:s)?\s+([^:\n]+)",
    ]
    
    for pattern in feature_patterns:
        features.extend(re.findall(pattern, docstring, re.IGNORECASE))
    
    features = list(set(features))
    
    # Check each feature is implemented
    incomplete_features = []
    
    for feature in features:
        feature_lower = feature.lower().strip()
        
        # Skip generic words
        if feature_lower in ["objetivo", "tarea", "propósito", "análisis"]:
            continue
        
        # Check if validated
        if not any(word in agent_code.lower() for word in feature_lower.split()):
            incomplete_features.append(feature)
    
    if incomplete_features:
        return ValidationResult(
            False,
            f"Incomplete features (mentioned but not validated): "
            f"{', '.join(incomplete_features[:3])}",
            "MEDIUM"
        )
    
    return ValidationResult(True, "All documented features implemented", "LOW")


# ============================================================================
# GATE 15: Logic Consistency
# ============================================================================

def validate_logic_consistency(agent_code: str) -> ValidationResult:
    """
    Detect contradictory conditions, redundant checks, logical errors.
    
    Example:
        if "PRÓXIMO" not in response and "PRÓXIMO" not in response.lower():
            # Redundant! lowercase doesn't add value
    """
    
    issues = []
    
    # Check for redundant conditions with .lower()
    redundant_patterns = [
        r'if\s+"([^"]+)"\s+(?:in|not in)\s+(\w+)\s+(?:and|or)\s+"([^"]+)"\s+(?:in|not in)\s+\2\.lower\(\)',
    ]
    
    for pattern in redundant_patterns:
        matches = re.finditer(pattern, agent_code)
        for match in matches:
            str1, var, str2 = match.groups()
            # Check if str2 is lowercase of str1
            if str2.lower() == str1.lower():
                issues.append(
                    f"Redundant condition: checking '{str1}' and '{str2}' "
                    f"against {var}.lower() - first check already covers both"
                )
    
    # Check for AND instead of OR errors
    if re.search(r'if\s+\w+.*?and\s+not\s+\w+.*?and\s+\w+', agent_code):
        issues.append("Potentially incorrect AND chaining - review logic")
    
    # Check for contradictory conditions in same scope
    lines = agent_code.split('\n')
    for i, line in enumerate(lines):
        if 'if' in line and i + 1 < len(lines):
            next_line = lines[i + 1]
            # Simple check: both check same thing but opposite
            if_condition = re.search(r'if\s+(.+?):', line)
            if_next = re.search(r'(?:elif|if)\s+(.+?):', next_line)
            
            if if_condition and if_next:
                cond1 = if_condition.group(1).strip()
                cond2 = if_next.group(1).strip()
                
                # Check if complete opposites
                if f"not {cond1}" == cond2 or f"not {cond2}" == cond1:
                    issues.append(f"Possible logic redundancy: {cond1} vs {cond2}")
    
    if issues:
        return ValidationResult(
            False,
            "; ".join(issues[:2]),  # Show first 2 issues
            "MEDIUM"
        )
    
    return ValidationResult(True, "Logic is consistent", "LOW")


# ============================================================================
# GATE 16: Design Pattern Adherence
# ============================================================================

def validate_design_patterns(agent_code: str) -> ValidationResult:
    """
    Ensure agent follows the Agent base class pattern.
    
    Required:
    - Inherits from Agent
    - Has all 6 required methods
    - Correct method signatures
    - Calls super().__init__()
    """
    
    issues = []
    
    # Check inheritance
    if "class" not in agent_code or "Agent" not in agent_code:
        return ValidationResult(False, "Must inherit from Agent", "CRITICAL")
    
    if not re.search(r'class\s+\w+Agent\(Agent\)', agent_code):
        return ValidationResult(False, "Must inherit directly from Agent", "CRITICAL")
    
    # Check super().__init__()
    if "super().__init__(" not in agent_code and "Agent.__init__" not in agent_code:
        issues.append("Missing super().__init__() call")
    
    # Check required methods
    required_methods = [
        ("__init__", r"def __init__\(self\)"),
        ("get_system_prompt", r"def get_system_prompt\(self.*?context.*?\)"),
        ("validate_input", r"def validate_input\(self.*?agent_input.*?\)"),
        ("validate_output", r"def validate_output\(self.*?response.*?\)"),
        ("calculate_confidence", r"def calculate_confidence\(self.*?response.*?\)"),
        ("suggest_improvements", r"def suggest_improvements\(self.*?response.*?\)"),
    ]
    
    for method_name, pattern in required_methods:
        if not re.search(pattern, agent_code, re.DOTALL):
            issues.append(f"Missing required method: {method_name}")
    
    # Check return types
    if "-> tuple[bool, str]" not in agent_code and "-> Tuple[bool, str]" not in agent_code:
        if "validate_input" in agent_code or "validate_output" in agent_code:
            issues.append("validate_* methods should return Tuple[bool, str]")
    
    if "-> List[str]" not in agent_code and "-> list[str]" not in agent_code:
        if "suggest_improvements" in agent_code:
            issues.append("suggest_improvements should return List[str]")
    
    if issues:
        return ValidationResult(False, "; ".join(issues[:2]), "HIGH")
    
    return ValidationResult(True, "Design pattern adhered to", "LOW")


# ============================================================================
# GATE 17: Error Message Accuracy
# ============================================================================

def validate_error_accuracy(agent_code: str) -> ValidationResult:
    """
    Ensure error messages match the conditions that trigger them.
    
    Example:
        if len(response) < 100:
            return False, "Falta evaluaciones"  # Bad! Wrong message
    """
    
    issues = []
    
    # Find all error returns
    error_returns = re.finditer(
        r'if\s+(.+?):\s*\n\s*return\s+False,\s*"([^"]+)"',
        agent_code,
        re.DOTALL
    )
    
    for match in error_returns:
        condition = match.group(1).strip()[:50]  # First 50 chars
        message = match.group(2)
        
        # Check if message is generic/unhelpful
        generic_words = ["error", "invalid", "bad", "wrong", "fail"]
        if all(word not in message.lower() for word in ["muy", "corto", "largo", "falta", "error"]):
            if len(message) < 10:
                issues.append(f"Vague error message: '{message}'")
        
        # Check if message describes the condition
        if "longitud" in condition.lower() and "corto" not in message.lower():
            issues.append(f"Message doesn't describe condition: '{message}'")
        
        if "len(" in condition and not any(word in message.lower() for word in ["corto", "largo", "longitud"]):
            issues.append(f"Length check but message doesn't mention: '{message}'")
    
    if issues:
        return ValidationResult(
            False,
            "; ".join(issues[:2]),
            "MEDIUM"
        )
    
    return ValidationResult(True, "Error messages are accurate", "LOW")


# ============================================================================
# GATE 18: Validation Coverage
# ============================================================================

def validate_coverage(agent_code: str) -> ValidationResult:
    """
    Ensure all validation types are covered:
    - Null/empty checks
    - Length checks
    - Type checks
    - Business logic checks
    """
    
    coverage = {}
    
    # Check for null/empty
    coverage["null"] = bool(re.search(
        r'if\s+(?:not\s+)?\w+(?:\s+or\s+len\(|or\s+.*?==\s*0)',
        agent_code
    ))
    
    # Check for length
    coverage["length"] = bool(re.search(
        r'len\(.*?\)\s*[<>=]',
        agent_code
    ))
    
    # Check for content keywords
    coverage["content"] = bool(re.search(
        r'(?:in|not in)\s+\w+\.(?:lower|upper|strip)',
        agent_code
    ))
    
    # Check for type-specific validation
    coverage["structure"] = bool(re.search(
        r'(?:\[|{|"|\bor\b).*?in',
        agent_code
    ))
    
    uncovered = [k for k, v in coverage.items() if not v]
    
    if len(uncovered) > 2:
        return ValidationResult(
            False,
            f"Validation coverage gaps: missing {', '.join(uncovered)}",
            "MEDIUM"
        )
    
    return ValidationResult(True, f"Validation coverage: {len(coverage) - len(uncovered)}/{len(coverage)}", "LOW")


# ============================================================================
# GATE 19: State Management
# ============================================================================

def validate_state_management(agent_code: str) -> ValidationResult:
    """
    Check proper state initialization and no shared mutable defaults.
    
    Issues:
    - Mutable defaults (lists/dicts) not in __init__
    - State accessed before initialization
    - Confidence not clamped
    """
    
    issues = []
    
    # Check for shared mutable state
    if re.search(r'self\.\w+\s*=\s*\[\]', agent_code) or \
       re.search(r'self\.\w+\s*=\s*{}', agent_code):
        # These might be OK in __init__, check location
        for match in re.finditer(r'(def\s+\w+.*?)(?=\n\s*def|\Z)', agent_code, re.DOTALL):
            method = match.group(1)
            if "def __init__" not in method:
                if re.search(r'self\.\w+\s*=\s*[\[{}]', method):
                    issues.append("Mutable state created outside __init__")
    
    # Check confidence clamping
    has_clamp = "min(1.0" in agent_code or "max(0.0" in agent_code
    if "calculate_confidence" in agent_code and not has_clamp:
        issues.append("Confidence not clamped to [0.0-1.0]")
    
    # Check for __post_init__ on dataclasses
    if "@dataclass" in agent_code:
        if "confidence" not in agent_code or "self.confidence = max" not in agent_code:
            if not re.search(r'def __post_init__.*?self\.confidence\s*=\s*max', agent_code, re.DOTALL):
                issues.append("Dataclass confidence not clamped in __post_init__")
    
    if issues:
        return ValidationResult(False, "; ".join(issues), "MEDIUM")
    
    return ValidationResult(True, "State properly managed", "LOW")


# ============================================================================
# GATE 20: Integration Readiness
# ============================================================================

def validate_integration_readiness(agent_code: str) -> ValidationResult:
    """
    Ensure agent can integrate with Ollama backend:
    - Accepts Dict[str, Any] context
    - Returns proper types
    - Async compatible
    - Handles streaming
    """
    
    issues = []
    
    # Check get_system_prompt signature
    if "def get_system_prompt" in agent_code:
        if "context:" not in agent_code or "Dict" not in agent_code:
            issues.append("get_system_prompt should accept context: Dict[str, Any]")
    
    # Check AgentOutput usage
    if "AgentOutput" not in agent_code:
        issues.append("Should return AgentOutput with confidence field")
    
    # Check confidence field
    if "confidence" not in agent_code:
        issues.append("Missing confidence scoring for Ollama routing")
    
    # Check suggestions field
    if "suggestions" not in agent_code:
        issues.append("Missing suggestions for Ollama improvement prompts")
    
    # Check for proper imports
    required_imports = [
        ("Agent", "from src.agents.base import Agent"),
        ("AgentInput", "from src.agents.base import AgentInput"),
        ("Dict", "from typing import Dict"),
        ("Any", "from typing import Any"),
    ]
    
    for name, import_line in required_imports:
        if name not in agent_code:
            issues.append(f"Missing import: {import_line}")
    
    if issues:
        return ValidationResult(
            False,
            "; ".join(issues[:3]),
            "HIGH"
        )
    
    return ValidationResult(True, "Integration ready", "LOW")


# ============================================================================
# Main Validator
# ============================================================================

class EnhancedLogicValidator:
    """Runs all 8 new logic validation gates"""
    
    def __init__(self):
        self.gates = {
            13: ("Unused Code Detection", validate_unused_code),
            14: ("Feature Completeness", validate_feature_completeness),
            15: ("Logic Consistency", validate_logic_consistency),
            16: ("Design Pattern Adherence", validate_design_patterns),
            17: ("Error Message Accuracy", validate_error_accuracy),
            18: ("Validation Coverage", validate_coverage),
            19: ("State Management", validate_state_management),
            20: ("Integration Readiness", validate_integration_readiness),
        }
    
    def validate_agent(self, agent_code: str) -> Dict:
        """Run all gates and return results"""
        results = {}
        
        for gate_num, (gate_name, gate_func) in self.gates.items():
            try:
                result = gate_func(agent_code)
                results[gate_num] = {
                    "name": gate_name,
                    "passed": result.passed,
                    "message": result.message,
                    "severity": result.severity
                }
            except Exception as e:
                results[gate_num] = {
                    "name": gate_name,
                    "passed": False,
                    "message": f"Validation error: {str(e)}",
                    "severity": "HIGH"
                }
        
        return results


if __name__ == "__main__":
    # Test
    validator = EnhancedLogicValidator()
    print("Enhanced Logic Validator ready")
    print(f"Gates: {list(validator.gates.keys())}")
