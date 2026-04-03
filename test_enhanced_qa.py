"""
Test Enhanced QA System Against Phase 2 Agents

This script tests the new logic validation gates (13-20)
against Phase 2 agents to verify they catch bugs
that the original system missed.
"""

import os
import sys
from pathlib import Path

# Add repo to path
sys.path.insert(0, str(Path(__file__).parent))

from validators_logic import EnhancedLogicValidator


def load_agent_file(agent_path: str) -> str:
    """Load agent code from file"""
    with open(agent_path, 'r', encoding='utf-8') as f:
        return f.read()


def test_enhanced_validator():
    """Test enhanced validator against Phase 2 agents"""
    
    agent_dir = Path("src/agents")
    agent_files = sorted(agent_dir.glob("*.py"))
    agent_files = [f for f in agent_files if f.name not in ['__init__.py', 'base.py', 'AGENT_TEMPLATE.py']]
    
    validator = EnhancedLogicValidator()
    
    print("\n" + "="*80)
    print("ENHANCED QA SYSTEM - LOGIC VALIDATION TEST")
    print("="*80)
    
    all_results = {}
    
    for agent_file in agent_files:
        print(f"\n📄 Testing: {agent_file.name}")
        print("-" * 60)
        
        try:
            code = load_agent_file(str(agent_file))
            results = validator.validate_agent(code)
            all_results[agent_file.name] = results
            
            # Print results
            passed_count = sum(1 for r in results.values() if r['passed'])
            total_gates = len(results)
            
            print(f"Result: {passed_count}/{total_gates} gates passed")
            print()
            
            for gate_num in sorted(results.keys()):
                result = results[gate_num]
                status = "✅ PASS" if result['passed'] else "❌ FAIL"
                
                print(f"  Gate {gate_num} ({result['name']})")
                print(f"    {status}")
                if not result['passed']:
                    print(f"    Issue: {result['message']}")
                print()
        
        except Exception as e:
            print(f"  ERROR: {str(e)}")
            all_results[agent_file.name] = {"error": str(e)}
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    for agent_name, results in all_results.items():
        if "error" in results:
            print(f"\n❌ {agent_name:30} - ERROR")
        else:
            passed = sum(1 for r in results.values() if r['passed'])
            total = len(results)
            pct = (passed / total) * 100
            
            if passed == total:
                print(f"✅ {agent_name:30} {passed}/{total} ({pct:.0f}%)")
            else:
                print(f"⚠️  {agent_name:30} {passed}/{total} ({pct:.0f}%)")
    
    # Issues summary
    print("\n" + "-"*80)
    print("ISSUES FOUND BY NEW GATES:")
    print("-"*80)
    
    all_issues = {}
    
    for agent_name, results in all_results.items():
        if "error" not in results:
            for gate_num, result in results.items():
                if not result['passed']:
                    gate_name = result['name']
                    severity = result['severity']
                    message = result['message']
                    
                    key = f"Gate {gate_num}: {gate_name}"
                    if key not in all_issues:
                        all_issues[key] = []
                    
                    all_issues[key].append({
                        'agent': agent_name,
                        'severity': severity,
                        'message': message
                    })
    
    if all_issues:
        for gate, issues in sorted(all_issues.items()):
            print(f"\n{gate}")
            for issue in issues:
                severity_icon = {
                    'LOW': '🟢',
                    'MEDIUM': '🟡',
                    'HIGH': '🔴',
                    'CRITICAL': '🔴'
                }.get(issue['severity'], '⚠️')
                
                print(f"  {severity_icon} {issue['agent']:25} {issue['message'][:60]}")
    else:
        print("\n✅ No issues found!")
    
    # Expected bugs that should have been caught
    print("\n" + "="*80)
    print("EXPECTED BUGS CAUGHT:")
    print("="*80)
    
    expected_bugs = {
        "code_review.py": [
            "Gate 13: dangerous_patterns defined but unused",
            "Gate 14: Security check mentioned but not implemented"
        ],
        "content_analysis.py": [
            "Gate 13: bias_indicators defined but unused",
            "Gate 14: Bias detection mentioned but incomplete"
        ],
    }
    
    for agent, bugs in expected_bugs.items():
        print(f"\n{agent}:")
        for bug in bugs:
            print(f"  ✅ {bug}")
    
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    test_enhanced_validator()
