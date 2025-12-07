import ipaddress
import sys
import os

# Mock classes to avoid SQLModel dependency if not installed locally
class MockSubnet:
    def __init__(self, cidr, namespace_id):
        self.cidr = cidr
        self.namespace_id = namespace_id

sys.path.append(os.getcwd() + '/backend')
try:
    from app.logic import validate_overlap, get_next_available_ip, calculate_utilization
except ImportError:
    # Need to setup path or mock logic if imports fail due to directory structure
    pass

# Copy logic here if import fails or just run this inside backend/
# Let's try to act as if we are in backend/
# We will write this file to backend/test_logic.py

def test():
    print("Testing IPAM Logic...")
    
    # 1. Overlap Check
    s1 = MockSubnet("192.168.1.0/24", 1)
    existing = [s1]
    
    # Validation Case A: Intersection /24 overlap
    try:
        assert validate_overlap("192.168.1.0/25", existing) == True
        print("[Pass] Detects subset overlap")
    except AssertionError:
        print("[FAIL] Failed to detect subset overlap")

    try:
        assert validate_overlap("192.168.0.0/16", existing) == True
        print("[Pass] Detects superset overlap")
    except AssertionError:
        print("[FAIL] Failed to detect superset overlap")

    try:
        assert validate_overlap("10.0.0.0/24", existing) == False
        print("[Pass] Allows non-overlapping")
    except AssertionError:
        print("[FAIL] False positive on non-overlap")

    # 2. Allocation
    allocated = ["192.168.1.1", "192.168.1.2"]
    next_ip = get_next_available_ip("192.168.1.0/24", allocated)
    if next_ip == "192.168.1.3":
        print(f"[Pass] Allocation correct: {next_ip}")
    else:
        print(f"[FAIL] Allocation got {next_ip}, expected 192.168.1.3")

    # 3. Utilization
    # /24 = 254 usable. 2 Allocated. Util = 2/254 * 100
    util = calculate_utilization(2, "192.168.1.0/24")
    expected = (2/254)*100
    if abs(util - expected) < 0.01:
        print(f"[Pass] Utilization: {util:.2f}%")
    else:
        print(f"[FAIL] Utilization: {util}, expected {expected}")

if __name__ == "__main__":
    test()
