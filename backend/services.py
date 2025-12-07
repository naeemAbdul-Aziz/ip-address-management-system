"""
Business logic services for IPAM Core
Handles validation, allocation, and core IP management
"""
from ipaddress import ip_network, ip_address
from sqlmodel import Session, select
from models import IPAddress


def validate_overlap(new_cidr: str, existing_cidrs: list[str]) -> bool:
    """
    Validate that new_cidr does not overlap with any existing_cidrs.
    FR-03: Strict consistency - reject overlapping CIDR blocks in same namespace.
    
    Uses RFC 4632 (ipaddress library) for precise CIDR calculations.
    Handles edge cases: /24 inside existing /16, etc.
    
    Args:
        new_cidr: New CIDR block to validate (e.g., "192.168.1.0/24")
        existing_cidrs: List of existing CIDR blocks to check against
    
    Returns:
        True if valid (no overlaps)
    
    Raises:
        ValueError: If overlap detected or invalid CIDR format
    """
    try:
        new_network = ip_network(new_cidr, strict=False)
    except ValueError as e:
        raise ValueError(f"Invalid CIDR format: {new_cidr}") from e
    
    for existing_cidr in existing_cidrs:
        try:
            existing_network = ip_network(existing_cidr, strict=False)
        except ValueError as e:
            raise ValueError(f"Invalid CIDR format: {existing_cidr}") from e
        
        # Check if networks overlap
        if new_network.overlaps(existing_network):
            raise ValueError(
                f"CIDR {new_cidr} overlaps with existing {existing_cidr}"
            )
    
    return True


def allocate_next_ip(subnet, hostname: str = None, session: Session = None) -> IPAddress:
    """
    Allocate the next available IP from a subnet.
    FR-05: Atomic allocation - finds next available, marks as Active.
    FR-07: Never allocates network or broadcast addresses.
    
    Algorithm: Find first "Deprecated" IP, mark as "Active", return it.
    
    Args:
        subnet: Subnet model instance
        hostname: Optional hostname for the allocated IP
        session: Database session
    
    Returns:
        Allocated IPAddress object
    
    Raises:
        ValueError: If no IPs available or allocation fails
    """
    if not session:
        raise ValueError("Database session required")
    
    # Find first deprecated (available) IP
    available_ip = session.exec(
        select(IPAddress)
        .where(IPAddress.subnet_id == subnet.id)
        .where(IPAddress.status == "Deprecated")
        .order_by(IPAddress.address)
    ).first()
    
    if not available_ip:
        raise ValueError(f"No available IPs in subnet {subnet.cidr}")
    
    # Mark as Active
    available_ip.status = "Active"
    if hostname:
        available_ip.hostname = hostname
    
    session.add(available_ip)
    
    return available_ip


def get_subnet_utilization(subnet, session: Session = None) -> dict:
    """
    Calculate detailed subnet utilization metrics.
    FR-04: Compute utilization: (Allocated IPs / Total Usable) * 100.
    
    Args:
        subnet: Subnet model instance
        session: Database session (optional)
    
    Returns:
        dict with utilization stats
    """
    total = len(subnet.ip_addresses)
    allocated = sum(1 for ip in subnet.ip_addresses if ip.status in ("Active", "Reserved"))
    available = total - allocated
    
    utilization_percent = (allocated / total * 100) if total > 0 else 0.0
    
    return {
        "total_usable_hosts": total,
        "allocated": allocated,
        "available": available,
        "utilization_percent": round(utilization_percent, 2),
    }
