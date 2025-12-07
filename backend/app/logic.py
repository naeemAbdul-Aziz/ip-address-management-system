import ipaddress
from typing import List, Optional
from .models import Subnet, IPAddress

def validate_overlap(new_cidr: str, existing_subnets: List[Subnet]) -> bool:
    """
    Checks if new_cidr overlaps with any existing subnets in the SAME namespace.
    Returns True if overlap exists, False otherwise.
    """
    try:
        new_net = ipaddress.ip_network(new_cidr, strict=False)
    except ValueError:
        raise ValueError(f"Invalid CIDR: {new_cidr}")

    for subnet in existing_subnets:
        existing_net = ipaddress.ip_network(subnet.cidr, strict=False)
        if new_net.overlaps(existing_net):
            return True
            
    return False

def get_next_available_ip(subnet_cidr: str, allocated_ips: List[str]) -> Optional[str]:
    """
    Finds the first available IP in the subnet, excluding Network and Broadcast addresses.
    allocated_ips: List of IP strings already in use.
    """
    network = ipaddress.ip_network(subnet_cidr, strict=False)
    # hosts() iterator excludes network and broadcast addresses
    # But for large subnets, converting to list is expensive. 
    # For /24 it's fine (254 hosts). For /16 it might be slow (65k).
    # MVP constraint: We'll assume /24 mostly, but we should be smart.
    
    allocated_set = set(allocated_ips)
    
    for ip in network.hosts():
        ip_str = str(ip)
        if ip_str not in allocated_set:
            return ip_str
            
    return None

def calculate_utilization(allocated_count: int, cidr: str) -> float:
    """
    Returns utilization percentage (0.0 to 100.0).
    """
    network = ipaddress.ip_network(cidr, strict=False)
    # num_addresses includes network and broadcast
    # Usable hosts = num_addresses - 2 (usually)
    # If /31 or /32, rules differ, but for standard subnets:
    total_usable = network.num_addresses - 2
    
    if total_usable <= 0:
        return 100.0 if allocated_count > 0 else 0.0
        
    return (allocated_count / total_usable) * 100.0

def find_next_free_subnet(existing_subnets: List[Subnet], prefix_length: int = 24) -> Optional[str]:
    """
    Automates finding the next available CIDR block in the namespace.
    Strategy: 
    1. Sort existing subnets by numeric network address.
    2. Check gap between 10.0.0.0 (or first subnet) and start.
    3. Check gaps between subnets.
    4. Return first fit.
    """
    # Simply assume private 10.x.x.x block or 192.168.x.x based on existing data context?
    # For MVP Steel Thread, let's assume we are operating in 192.168.0.0/16 or 10.0.0.0/8
    # A smart system detects the "Supernet" context. 
    # Heuristic: Look at the first subnet. If 10.x, stay in 10.x. 
    
    if not existing_subnets:
        return "10.0.0.0/{}".format(prefix_length)

    networks = []
    for s in existing_subnets:
        try:
            networks.append(ipaddress.ip_network(s.cidr, strict=False))
        except ValueError:
            continue
    
    networks.sort(key=lambda x: x.network_address)
    
    # Heuristic: Define the "Scope" based on the first network found
    # If first is 192.168.x.x, we scan 192.168.0.0/16
    first_net = networks[0]
    if first_net.network_address.is_private:
        if str(first_net).startswith("10."):
            scope = ipaddress.ip_network("10.0.0.0/8")
        elif str(first_net).startswith("172."):
             scope = ipaddress.ip_network("172.16.0.0/12")
        else:
            scope = ipaddress.ip_network("192.168.0.0/16")
    else:
        scope = ipaddress.ip_network("10.0.0.0/8") # Fallback

    # Simple gap search
    # Check start of scope
    candidate_start = scope.network_address
    
    # Create a candidate network
    try:
        candidate = ipaddress.ip_network((candidate_start, prefix_length))
    except (ValueError, TypeError):
        return None

    # Iterative check against sorted networks
    # This is O(N^2) worst case if we just increment, but we can jump.
    # Optimization: "Gap Hopping"
    
    # Current candidate cursor
    cursor = int(scope.network_address)
    limit = int(scope.broadcast_address)
    step = 2 ** (32 - prefix_length) # Number of IPs in the new subnet
    
    # We need to construct network from int
    while cursor <= limit:
        candidate_addr = ipaddress.IPv4Address(cursor)
        try:
            candidate_net = ipaddress.ip_network(f"{candidate_addr}/{prefix_length}")
        except ValueError:
             cursor += step
             continue

        # Check overlap
        overlap = False
        next_jump = cursor + step # Default jump if no overlap
        
        for n in networks:
            # If candidate is effectively AFTER this network, continue
            if int(candidate_net.network_address) >= int(n.broadcast_address):
                continue
            
            # If candidate overlaps
            if candidate_net.overlaps(n):
                overlap = True
                # Optimization: Jump to end of overlapping network + 1 boundary
                # Align to next valid block
                jump_target = int(n.broadcast_address) + 1
                # Ensure alignment to prefix size
                remainder = jump_target % step
                if remainder != 0:
                    jump_target += (step - remainder)
                
                next_jump = max(next_jump, jump_target)
                break
        
        if not overlap:
            return str(candidate_net)
            
        cursor = next_jump

    return None
