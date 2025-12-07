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

def find_next_free_subnet(existing_subnets: List[Subnet], prefix_length: int = 24, root_cidr: str = "10.0.0.0/8") -> Optional[str]:
    """
    Automates finding the next available CIDR block in the namespace.
    Uses the Namespace's Root CIDR as the strict scope.
    """
    try:
        scope = ipaddress.ip_network(root_cidr, strict=False)
    except ValueError:
        return None

    # Sort existing subnets by numeric network address
    networks = []
    for s in existing_subnets:
        try:
            # Only include subnets effectively inside the root scope to avoid weirdness
            net = ipaddress.ip_network(s.cidr, strict=False)
            if net.overlaps(scope): 
                 networks.append(net)
        except ValueError:
            continue
    
    networks.sort(key=lambda x: x.network_address)

    # Iterative Gap Search
    # Start checking from the beginning of the scope
    cursor = int(scope.network_address)
    limit = int(scope.broadcast_address)
    step = 2 ** (32 - prefix_length) # Number of IPs in the new subnet
    
    while cursor <= limit:
        candidate_addr = ipaddress.IPv4Address(cursor)
        try:
            candidate_net = ipaddress.ip_network(f"{candidate_addr}/{prefix_length}")
        except ValueError:
             # Alignment issue, bump cursor
             cursor += 1
             continue
        
        # Check if candidate is strictly within scope (should be given loop, but strictness check)
        if not candidate_net.subnet_of(scope):
             cursor += step
             continue

        # Check overlap against existing networks
        overlap = False
        next_jump = cursor + step # Default jump
        
        for n in networks:
            # Optimization: If candidate is past this network, ignore
            if int(candidate_net.network_address) >= int(n.broadcast_address):
                continue
            
            # If candidate overlaps this existing network
            if candidate_net.overlaps(n):
                overlap = True
                # Jump to the end of this existing network + 1 (aligned)
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
