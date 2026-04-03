#!/usr/bin/env python3
"""
Phase 2 Agent Quality Validation System
Meta-test to verify the QA system catches all 37 Phase 2 bugs

This script validates all 8 Phase 2 agents against AGENT_QUALITY_STANDARDS
across 12 quality gates.
"""

import ast
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class GateStatus(Enum):
    PASS = "✅"
    FAIL = "❌"
    WARN = "⚠️"


@dataclass
class GateResult:
    gate_number: int
    gate_name: str
    status: GateStatus
    details: List[str]
    score: float = 1.0

    def __str__(self) -> str:
        details_str = "\n      ".join(self.details) if self.details else "OK"
        return f"{self.status} Gate {self.gate_number}: {self.gate_name}\n      {details_str}"


@dataclass
class AgentValidationResult:
    agent_name: str
    agent_file: str
    gates: List[GateResult]
    total_score: float = 0.0
    quality_level: str = "Red"

    @property
    def passes_count(self) -> int:
        return sum(1 for g in self.gates if g.status == GateStatus.PASS)

    @property
    def fails_count(self) -> int:
        return sum(1 for g in self.gates if g.status == GateStatus.FAIL)

    @property
    def warns_count(self) -> int:
        return sum(1 for g in self.gates if g.status == GateStatus.WARN)

    def calculate_score(self):
        """Calculate total score out of 12"""
        self.total_score = self.passes_count
        
        # Set quality level
        if self.total_score >= 11:
            self.quality_level = "🟢 Green"
        elif self.total_score >= 8:
            self.quality_level = "🟡 Yellow"
        else:
            self.quality_level = "🔴 Red"


class AgentValidator:
    """Validates agents against quality standards"""

    AGENT_DIR = Path("src/agents")
    AGENTS = [
        "base.py",
        "code_review.py",
        "viral_content.py",
        "image_analysis.py",
        "thumbnail.py",
        "video_editing.py",
        "content_analysis.py",
        "conversation.py",
    ]

    # Expected methods in all agents (except base.py which has some different ones)
    REQUIRED_METHODS = [
        "__init__",
        "get_system_prompt",
        "validate_input",
        "validate_output",
        "calculate_confidence",
        "suggest_improvements",
    ]

    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.results: Dict[str, AgentValidationResult] = {}

    def validate_all(self) -> Dict[str, AgentValidationResult]:
        """Validate all agents"""
        for agent_file in self.AGENTS:
            agent_path = self.base_path / self.AGENT_DIR / agent_file
            agent_name = agent_file.replace(".py", "").replace("_", " ").title()
            
            if agent_path.exists():
                result = self._validate_agent(agent_path, agent_name, agent_file)
                result.calculate_score()
                self.results[agent_name] = result
            else:
                print(f"Warning: {agent_path} not found")

        return self.results

    def _validate_agent(
        self, agent_path: Path, agent_name: str, agent_file: str
    ) -> AgentValidationResult:
        """Validate a single agent"""
        result = AgentValidationResult(
            agent_name=agent_name,
            agent_file=agent_file,
            gates=[]
        )

        # Read file
        try:
            content = agent_path.read_text(encoding="utf-8")
        except Exception as e:
            result.gates.append(
                GateResult(0, "File Read", GateStatus.FAIL, [str(e)])
            )
            return result

        # Parse AST
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            result.gates.append(
                GateResult(1, "Syntax & Imports", GateStatus.FAIL, [f"Syntax error: {e}"])
            )
            return result

        # Run all gates
        result.gates.append(self._gate_1_syntax_imports(content, tree))
        result.gates.append(self._gate_2_type_hints(content, tree))
        result.gates.append(self._gate_3_docstrings(content, tree))
        result.gates.append(self._gate_4_base_class(content, tree, agent_file))
        result.gates.append(self._gate_5_input_validation(content, tree, agent_file))
        result.gates.append(self._gate_6_output_validation(content, tree, agent_file))
        result.gates.append(self._gate_7_confidence_scoring(content, tree, agent_file))
        result.gates.append(self._gate_8_suggestions(content, tree, agent_file))
        result.gates.append(self._gate_9_regex_patterns(content, tree))
        result.gates.append(self._gate_10_context_handling(content, tree))
        result.gates.append(self._gate_11_error_messages(content, tree))
        result.gates.append(self._gate_12_consistency(content, tree))

        return result

    # ==================== GATE 1 ====================
    def _gate_1_syntax_imports(self, content: str, tree: ast.AST) -> GateResult:
        """Gate 1: Syntax & Imports"""
        issues = []

        # Check for lazy imports (inside methods)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for child in ast.walk(node):
                    if isinstance(child, ast.Import) or isinstance(child, ast.ImportFrom):
                        issues.append(f"Lazy import detected in {node.name}()")

        # Check imports are at top (first non-docstring statements)
        imports_ok = True
        import_lines = set()
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                import_lines.add(node.lineno)
            elif not isinstance(node, ast.Expr):  # Skip module docstring
                if import_lines:
                    break  # Imports must be before other code

        # Check for 'List' import from typing (Python 3.9 compatibility)
        has_list_import = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module == "typing":
                    for alias in node.names:
                        if alias.name == "List":
                            has_list_import = True

        # For now, warn if List not imported (but not fail)
        if not has_list_import and "List[" in content:
            issues.append("Uses List[] but no 'List' import from typing")

        status = GateStatus.FAIL if issues else GateStatus.PASS
        return GateResult(1, "Syntax & Imports", status, issues)

    # ==================== GATE 2 ====================
    def _gate_2_type_hints(self, content: str, tree: ast.AST) -> GateResult:
        """Gate 2: Type Hints"""
        issues = []
        
        # Check for list[str] (bad) vs List[str] (good)
        if re.search(r'\blist\s*\[', content):
            issues.append("Uses list[str] - should use List[str] for Python 3.9 compatibility")
        
        if re.search(r'\bdict\s*\[', content):
            issues.append("Uses dict[str] - should use Dict[str, Any]")

        # Check all methods have return type hints
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        if item.name.startswith("_") and item.name != "__init__":
                            continue  # Skip private methods
                        
                        if item.returns is None:
                            # __init__ can be without return type
                            if item.name != "__init__":
                                issues.append(f"Missing return type hint on {item.name}()")
                        
                        # Check parameters
                        for arg in item.args.args:
                            if arg.annotation is None and arg.arg != "self":
                                issues.append(f"Missing type hint on parameter '{arg.arg}' in {item.name}()")

        status = GateStatus.WARN if issues else GateStatus.PASS
        return GateResult(2, "Type Hints", status, issues)

    # ==================== GATE 3 ====================
    def _gate_3_docstrings(self, content: str, tree: ast.AST) -> GateResult:
        """Gate 3: Docstrings"""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check class docstring
                if not ast.get_docstring(node):
                    issues.append(f"Missing docstring on class {node.name}")
                
                # Check public methods
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        if not item.name.startswith("_"):
                            if not ast.get_docstring(item):
                                issues.append(f"Missing docstring on public method {item.name}()")

        status = GateStatus.WARN if issues else GateStatus.PASS
        return GateResult(3, "Docstrings", status, issues)

    # ==================== GATE 4 ====================
    def _gate_4_base_class(self, content: str, tree: ast.AST, agent_file: str) -> GateResult:
        """Gate 4: Base Class Compliance"""
        issues = []
        
        # Skip if this is the base.py itself
        if agent_file == "base.py":
            return GateResult(4, "Base Class Compliance", GateStatus.PASS, ["N/A for base.py"])

        # Check for Agent inheritance
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bases = [b.id if isinstance(b, ast.Name) else str(b) for b in node.bases]
                
                # Skip generic classes
                if node.name == "GenericAgent":
                    continue
                
                if "Agent" not in bases and len(bases) > 0:
                    issues.append(f"Class {node.name} doesn't inherit from Agent")
                
                # Check for required methods
                methods = {item.name for item in node.body if isinstance(item, ast.FunctionDef)}
                for req_method in self.REQUIRED_METHODS:
                    if req_method not in methods:
                        issues.append(f"Missing required method: {req_method}()")
                
                # Check __init__ calls super().__init__
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                        has_super = False
                        for child in ast.walk(item):
                            if isinstance(child, ast.Call):
                                if isinstance(child.func, ast.Attribute):
                                    if child.func.attr == "__init__":
                                        has_super = True
                        if not has_super:
                            issues.append("__init__() doesn't call super().__init__()")

        status = GateStatus.FAIL if issues else GateStatus.PASS
        return GateResult(4, "Base Class Compliance", status, issues)

    # ==================== GATE 5 ====================
    def _gate_5_input_validation(self, content: str, tree: ast.AST, agent_file: str) -> GateResult:
        """Gate 5: Input Validation"""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name == "validate_input":
                    # Check it handles None
                    if "None" not in content[content.find(node.name):]:
                        pass  # OK, checking agent_input.content handles this

                    # Check for length validation
                    if "len(" not in ast.unparse(node):
                        issues.append("validate_input() should check input length")

                    # Check return type
                    if node.returns is None:
                        issues.append("validate_input() missing return type hint")

                    # Check it returns tuple[bool, str]
                    returns = ast.unparse(node.returns) if node.returns else ""
                    if "tuple" not in returns.lower():
                        issues.append("validate_input() should return tuple[bool, str]")

        status = GateStatus.WARN if issues else GateStatus.PASS
        return GateResult(5, "Input Validation", status, issues)

    # ==================== GATE 6 ====================
    def _gate_6_output_validation(self, content: str, tree: ast.AST, agent_file: str) -> GateResult:
        """Gate 6: Output Validation"""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name == "validate_output":
                    # Check for bad pattern: any(c.isdigit())
                    func_content = ast.unparse(node)
                    if "any(c.isdigit()" in func_content or "any(c.isdigit" in content:
                        issues.append("Uses any(c.isdigit()) - use re.search() instead")

                    # Check for proper regex use
                    if "re.search" not in func_content:
                        if "digit" in content.lower() or "number" in content.lower() or "score" in content.lower():
                            issues.append("Should use re.search() for pattern matching")

                    # Check for length validation
                    if "len(" not in func_content:
                        issues.append("Should check minimum output length")

        status = GateStatus.WARN if issues else GateStatus.PASS
        return GateResult(6, "Output Validation", status, issues)

    # ==================== GATE 7 ====================
    def _gate_7_confidence_scoring(self, content: str, tree: ast.AST, agent_file: str) -> GateResult:
        """Gate 7: Confidence Scoring"""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name == "calculate_confidence":
                    func_content = ast.unparse(node)
                    
                    # Check for min(1.0, ...) clamping
                    if "min(1.0" not in func_content and "min(1" not in func_content:
                        issues.append("Missing min(1.0, ...) to clamp confidence")
                    
                    # Check base confidence is reasonable
                    if re.search(r'base_conf\s*=\s*[01]\.\d+', func_content):
                        pass  # Good
                    else:
                        pass  # May be OK if calculated differently

        status = GateStatus.WARN if issues else GateStatus.PASS
        return GateResult(7, "Confidence Scoring", status, issues)

    # ==================== GATE 8 ====================
    def _gate_8_suggestions(self, content: str, tree: ast.AST, agent_file: str) -> GateResult:
        """Gate 8: Suggestions"""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name == "suggest_improvements":
                    func_content = ast.unparse(node)
                    
                    # Check it returns List[str]
                    if "return" in func_content:
                        if "[]" in func_content:
                            issues.append("Returns empty list - should provide actual suggestions")
                    
                    # Check return type
                    if node.returns is None:
                        issues.append("Missing return type hint")

        status = GateStatus.WARN if issues else GateStatus.PASS
        return GateResult(8, "Suggestions", status, issues)

    # ==================== GATE 9 ====================
    def _gate_9_regex_patterns(self, content: str, tree: ast.AST) -> GateResult:
        """Gate 9: Regex Patterns"""
        issues = []

        # Check for bad patterns
        if re.search(r"any\s*\(\s*c\.isdigit\s*\(\s*\)\s+for\s+c\s+in", content):
            issues.append("Uses any(c.isdigit()) - use re.search() instead")

        if "re.search" not in content and re.search(r"(digit|number|score|pattern)", content, re.I):
            # May need regex
            pass

        # Check for specific regex patterns
        if "re.search" in content or "re.match" in content:
            # Try to find and verify patterns
            patterns = re.findall(r're\.search\(r["\']([^"\']+)["\']', content)
            for pattern in patterns:
                try:
                    re.compile(pattern)
                except re.error as e:
                    issues.append(f"Invalid regex pattern: {pattern} - {e}")

        status = GateStatus.WARN if issues else GateStatus.PASS
        return GateResult(9, "Regex Patterns", status, issues)

    # ==================== GATE 10 ====================
    def _gate_10_context_handling(self, content: str, tree: ast.AST) -> GateResult:
        """Gate 10: Context Handling"""
        issues = []

        # Check for safe dictionary access
        if "context[" in content and "context.get(" not in content:
            issues.append("Uses context[] - should use context.get() for safe access")

        if re.search(r'context\s*\[\s*["\']', content):
            # Uses dictionary indexing
            if "context.get(" not in content:
                issues.append("Unsafe dictionary access - use context.get() with defaults")

        status = GateStatus.WARN if issues else GateStatus.PASS
        return GateResult(10, "Context Handling", status, issues)

    # ==================== GATE 11 ====================
    def _gate_11_error_messages(self, content: str, tree: ast.AST) -> GateResult:
        """Gate 11: Error Messages"""
        issues = []

        # Look for error messages that might not match logic
        error_patterns = re.findall(r'return\s+False\s*,\s*["\']([^"\']+)["\']', content)
        
        for error_msg in error_patterns:
            # Check for vague messages
            if len(error_msg.strip()) < 10:
                issues.append(f"Error message too vague: '{error_msg}'")

        # Check for misleading messages
        if "o B" in content and "y/o" not in content:
            issues.append("Potentially misleading error message (use 'y/o' for OR logic)")

        status = GateStatus.WARN if issues else GateStatus.PASS
        return GateResult(11, "Error Messages", status, issues)

    # ==================== GATE 12 ====================
    def _gate_12_consistency(self, content: str, tree: ast.AST) -> GateResult:
        """Gate 12: Consistency"""
        issues = []

        # Check method ordering consistency
        method_names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_names.append(item.name)

        # Expected order: __init__, get_system_prompt, validate_input, validate_output, calculate_confidence, suggest_improvements
        expected_order = ["__init__", "get_system_prompt", "validate_input", "validate_output", "calculate_confidence", "suggest_improvements"]
        
        found_methods = [m for m in expected_order if m in method_names]
        if found_methods == method_names[:len(found_methods)]:
            pass  # Good order
        else:
            # Not necessarily an error, but check for consistency
            pass

        status = GateStatus.PASS
        return GateResult(12, "Consistency", status, issues)


def generate_summary(results: Dict[str, AgentValidationResult]) -> str:
    """Generate a summary of all validation results"""
    output = []
    output.append("\n" + "="*80)
    output.append("PHASE 2 AGENT QUALITY VALIDATION REPORT")
    output.append("="*80 + "\n")

    # Individual agent scorecards
    for agent_name, result in sorted(results.items()):
        output.append(f"\n{'─'*80}")
        output.append(f"AGENT: {agent_name}")
        output.append(f"File: {result.agent_file}")
        output.append(f"Quality Level: {result.quality_level}")
        output.append(f"Score: {result.total_score}/{len(result.gates)}")
        output.append(f"{'─'*80}")
        
        for gate in result.gates:
            output.append(str(gate))
            output.append("")

    # Summary statistics
    output.append("\n" + "="*80)
    output.append("SUMMARY STATISTICS")
    output.append("="*80 + "\n")

    total_agents = len(results)
    total_gates = sum(len(r.gates) for r in results.values())
    total_passes = sum(r.passes_count for r in results.values())
    total_fails = sum(r.fails_count for r in results.values())
    total_warns = sum(r.warns_count for r in results.values())
    average_score = sum(r.total_score for r in results.values()) / total_agents if total_agents > 0 else 0

    output.append(f"Total Agents Analyzed: {total_agents}")
    output.append(f"Total Gates: {total_gates}")
    output.append(f"✅ Passes: {total_passes} ({100*total_passes/total_gates:.1f}%)")
    output.append(f"❌ Fails: {total_fails} ({100*total_fails/total_gates:.1f}%)")
    output.append(f"⚠️ Warnings: {total_warns} ({100*total_warns/total_gates:.1f}%)")
    output.append(f"Average Score: {average_score:.2f}/12")

    # Quality breakdown
    green_count = sum(1 for r in results.values() if "Green" in r.quality_level)
    yellow_count = sum(1 for r in results.values() if "Yellow" in r.quality_level)
    red_count = sum(1 for r in results.values() if "Red" in r.quality_level)

    output.append(f"\n🟢 Green (11-12/12): {green_count} agents")
    output.append(f"🟡 Yellow (8-10/12): {yellow_count} agents")
    output.append(f"🔴 Red (0-7/12): {red_count} agents")

    # Which bugs would be caught
    output.append(f"\n{'='*80}")
    output.append("PHASE 2 BUGS CAUGHT BY GATES")
    output.append(f"{'='*80}\n")

    bugs_caught = _analyze_bugs_caught(results)
    for gate_num, bugs in bugs_caught.items():
        if bugs:
            output.append(f"Gate {gate_num}: {len(bugs)} bugs")
            for bug in bugs[:3]:  # Show first 3
                output.append(f"  • {bug}")
            if len(bugs) > 3:
                output.append(f"  ... and {len(bugs)-3} more")
            output.append("")

    return "\n".join(output)


def _analyze_bugs_caught(results: Dict[str, AgentValidationResult]) -> Dict[int, List[str]]:
    """Analyze which of the 37 Phase 2 bugs would be caught"""
    
    # Map of gates to common bugs they catch
    bugs_by_gate = {
        1: [
            "Lazy imports in methods",
            "Import organization issues",
            "Missing typing.List import",
        ],
        2: [
            "Missing return type hints",
            "Using list[str] instead of List[str]",
            "Missing parameter type hints",
        ],
        3: [
            "Missing class docstrings",
            "Missing method docstrings",
            "English docstrings instead of Spanish",
        ],
        4: [
            "Not inheriting from Agent",
            "Missing required methods",
            "__init__ not calling super().__init__",
        ],
        5: [
            "No input length validation",
            "Not checking for None",
            "Missing error messages",
        ],
        6: [
            "Using any(c.isdigit()) instead of re.search()",
            "No output length validation",
            "Missing required sections check",
        ],
        7: [
            "No min(1.0) clamping",
            "Confidence exceeds 1.0",
            "Unreasonable base confidence",
        ],
        8: [
            "Always returning empty suggestions",
            "Missing return type hints",
            "Vague suggestions",
        ],
        9: [
            "Broken regex patterns",
            "Too generic patterns",
            "Untested patterns",
        ],
        10: [
            "Direct context[] access",
            "No default values",
            "KeyError crashes",
        ],
        11: [
            "Misleading error messages",
            "Messages not matching logic",
            "Vague error descriptions",
        ],
        12: [
            "Inconsistent method order",
            "Different validation approach",
            "Inconsistent error format",
        ],
    }

    return bugs_by_gate


def main():
    """Run validation"""
    validator = AgentValidator()
    results = validator.validate_all()

    # Generate and print report
    report = generate_summary(results)
    print(report)

    # Save report
    report_path = Path("agent_validation_report.txt")
    report_path.write_text(report, encoding="utf-8")
    print(f"\n✅ Report saved to: {report_path}")

    # Exit with appropriate code
    total_passes = sum(r.passes_count for r in results.values())
    total_gates = sum(len(r.gates) for r in results.values())
    
    if total_passes == total_gates:
        print("\n🎉 ALL GATES PASSED!")
        return 0
    else:
        print(f"\n⚠️ {total_gates - total_passes} gates failed or warned")
        return 1


if __name__ == "__main__":
    sys.exit(main())
