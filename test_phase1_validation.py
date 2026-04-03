#!/usr/bin/env python3
"""PHASE 1 VALIDATION - Syntax and Structure Check"""

import sys
import os
import ast
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

files_to_check = [
    'src/investigador/buscador_externo.py',
    'src/investigador/pipeline.py',
    'src/investigador/modelos.py',
    'src/investigador/evaluador.py',
    'src/investigador/ensamblador.py',
    'src/ia/rag.py',
    'src/security/hack/red_team.py',
    'src/orquestador/orquestador.py',
    'src/memory/flash_memory.py',
]

def check_syntax(filepath):
    """Check if file has valid Python syntax"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        ast.parse(code)
        return True, "OK"
    except SyntaxError as e:
        return False, f"Syntax error at line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, str(e)

def check_critical_fixes(filepath):
    """Check for critical fixes in specific files"""
    checks = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'pipeline.py' in filepath:
        # Check for evaluados guard
        checks.append(('evaluados guard', 'len(evaluados) == 0' in content))
        checks.append(('error logging', 'logger.warning' in content and 'evaluacion' in content))
    
    if 'orquestador.py' in filepath:
        # Check for JSON error logging
        checks.append(('JSON error log', 'JSONDecodeError' in content and 'logger.error' in content))
        # Check for response extraction try/except
        checks.append(('Response extraction guard', 'except (AttributeError, TypeError)' in content))
    
    if 'flash_memory.py' in filepath:
        # Check for recall_by_type error handling
        checks.append(('recall_by_type try/except', 'async def recall_by_type' in content and 'try:' in content.split('recall_by_type')[1][:500]))
        # Check for get_stats error handling
        checks.append(('get_stats try/except', 'async def get_stats' in content and 'except Exception' in content.split('get_stats')[1][:500]))
    
    return checks

def main():
    logger.info("="*70)
    logger.info("PHASE 1 INTEGRATION VALIDATION")
    logger.info("="*70)
    
    total = 0
    passed = 0
    failed_files = []
    
    # Check each file
    for filepath in files_to_check:
        if not os.path.exists(filepath):
            logger.error(f"❌ {filepath}: FILE NOT FOUND")
            failed_files.append(filepath)
            total += 1
            continue
        
        # Syntax check
        ok, msg = check_syntax(filepath)
        total += 1
        
        if ok:
            logger.info(f"✅ {filepath}: {msg}")
            passed += 1
            
            # Additional checks for critical files
            checks = check_critical_fixes(filepath)
            for check_name, check_result in checks:
                if check_result:
                    logger.info(f"   ✓ {check_name}")
                else:
                    logger.warning(f"   ⚠ {check_name} - may not be fully implemented")
        else:
            logger.error(f"❌ {filepath}: {msg}")
            failed_files.append(filepath)
    
    # Summary
    logger.info("\n" + "="*70)
    logger.info(f"SYNTAX CHECK: {passed}/{total} files valid")
    logger.info("="*70)
    
    if failed_files:
        logger.error("\nFailed files:")
        for f in failed_files:
            logger.error(f"  - {f}")
        return 1
    
    logger.info("\n🎉 ALL FILES HAVE VALID SYNTAX ✅")
    
    # Check for critical fixes
    logger.info("\n" + "="*70)
    logger.info("CRITICAL FIXES VERIFICATION")
    logger.info("="*70)
    
    critical_files = {
        'src/investigador/pipeline.py': 'Pipeline empty results (CRITICAL)',
        'src/orquestador/orquestador.py': 'Orquestador validation (CRITICAL)',
        'src/memory/flash_memory.py': 'FlashMemory error handling (CRITICAL)',
    }
    
    for filepath, desc in critical_files.items():
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            checks = check_critical_fixes(filepath)
            all_ok = all(result for _, result in checks)
            
            if all_ok:
                logger.info(f"✅ {desc}: VERIFIED")
            else:
                logger.warning(f"⚠️  {desc}: Some checks failed")
                for name, result in checks:
                    if not result:
                        logger.warning(f"   - {name}")
    
    logger.info("\n" + "="*70)
    return 0

if __name__ == "__main__":
    sys.exit(main())
