"""Test prompt validation"""
from src.filter import FilterManager

def test_validation():
    print("=" * 60)
    print("Testing Prompt Validation")
    print("=" * 60)

    # Test 1: Valid prompt
    print("\n1. Testing VALID prompt:")
    try:
        fm = FilterManager('("AI" OR "ML") AND ("safety")')
        print("   [PASS] Valid prompt accepted")
    except ValueError as e:
        print(f"   [FAIL] {e}")

    # Test 2: Unbalanced parentheses
    print("\n2. Testing UNBALANCED PARENTHESES:")
    try:
        fm = FilterManager('("AI" OR "ML") AND ("safety"')
        print("   [FAIL] Should have rejected unbalanced parens")
    except ValueError as e:
        print(f"   [PASS] Caught error: {str(e).splitlines()[1]}")

    # Test 3: Unbalanced quotes
    print("\n3. Testing UNBALANCED QUOTES:")
    try:
        fm = FilterManager('("AI OR "ML") AND ("safety")')
        print("   [FAIL] Should have rejected unbalanced quotes")
    except ValueError as e:
        print(f"   [PASS] Caught error: {str(e).splitlines()[1]}")

    # Test 4: Empty groups
    print("\n4. Testing EMPTY GROUPS:")
    try:
        fm = FilterManager('() AND ("safety")')
        print("   [FAIL] Should have rejected empty groups")
    except ValueError as e:
        print(f"   [PASS] Caught error: {str(e).splitlines()[1]}")

    # Test 5: Unsupported operator
    print("\n5. Testing UNSUPPORTED OPERATOR (XOR):")
    try:
        fm = FilterManager('("AI" XOR "ML")')
        print("   [FAIL] Should have rejected XOR operator")
    except ValueError as e:
        print(f"   [PASS] Caught error: {str(e).splitlines()[1]}")

    # Test 6: No quoted terms
    print("\n6. Testing NO QUOTED TERMS:")
    try:
        fm = FilterManager('AI safety')
        print("   [FAIL] Should have rejected non-quoted terms")
    except ValueError as e:
        print(f"   [PASS] Caught error: {str(e).splitlines()[1]}")

    # Test 7: ANDNOT without inclusions
    print("\n7. Testing ANDNOT WITHOUT INCLUSIONS:")
    try:
        fm = FilterManager('ANDNOT ("medical")')
        print("   [FAIL] Should have rejected ANDNOT-only query")
    except ValueError as e:
        print(f"   [PASS] Caught error: {str(e).splitlines()[1]}")

    # Test 8: Empty prompt
    print("\n8. Testing EMPTY PROMPT:")
    try:
        fm = FilterManager('')
        print("   [FAIL] Should have rejected empty prompt")
    except ValueError as e:
        print(f"   [PASS] Caught error: {str(e).splitlines()[1]}")

    print("\n" + "=" * 60)
    print("Validation Testing Complete")
    print("=" * 60)

if __name__ == "__main__":
    test_validation()
