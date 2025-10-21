#!/usr/bin/env python3
"""
Simple import test to verify all modules load correctly
"""

import sys
import traceback

def test_import(module_name):
    """Test importing a module"""
    try:
        __import__(module_name)
        print(f"✅ {module_name}")
        return True
    except Exception as e:
        print(f"❌ {module_name}: {e}")
        traceback.print_exc()
        return False

def main():
    """Test all main modules"""
    print("=" * 60)
    print("TESTING MODULE IMPORTS")
    print("=" * 60)
    print()
    
    modules = [
        'pdf_parser',
        'vector_store',
        'llm_client',
        'handlers',
        'bot',
    ]
    
    results = []
    for module in modules:
        result = test_import(module)
        results.append((module, result))
        print()
    
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"Imports successful: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 All modules imported successfully!")
        return 0
    else:
        print("\n⚠️ Some modules failed to import")
        print("Note: This may be due to missing dependencies")
        return 1

if __name__ == "__main__":
    sys.exit(main())
