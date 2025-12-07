"""
SQLModel data models for IPAM Core
Type-safe ORM models using Pydantic + SQLAlchemy
"""
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship


class Namespace(SQLModel, table=True):
    """
    Namespace (VRF) - Isolation context for subnets.
    FR-01: System must support multiple isolated namespaces.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    
    # Relationship
    subnets: list["Subnet"] = Relationship(back_populates="namespace")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "DataCenter-East"
            }
        }


class Subnet(SQLModel, table=True):
    """
    Subnet - CIDR block managed within a Namespace.
    FR-02: Subnets can overlap in different namespaces, must not in same namespace.
    FR-03: Overlap validation enforced on creation.
    FR-04: Utilization computed as (Allocated / Total Usable) * 100.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    namespace_id: int = Field(foreign_key="namespace.id")
    cidr: str = Field(index=True)
    label: str
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    namespace: Namespace = Relationship(back_populates="subnets")
    ip_addresses: list["IPAddress"] = Relationship(back_populates="subnet", cascade_delete=True)
    
    @property
    def utilization_percent(self) -> float:
        """Calculate subnet utilization percentage."""
        if not self.ip_addresses:
            return 0.0
        
        allocated = sum(1 for ip in self.ip_addresses if ip.status in ("Active", "Reserved"))
        total_usable = len(self.ip_addresses)
        
        if total_usable == 0:
            return 0.0
        
        return (allocated / total_usable) * 100
    
    @property
    def total_ips(self) -> int:
        """Total number of usable IPs in subnet."""
        return len(self.ip_addresses)
    
    @property
    def allocated_ips(self) -> int:
        """Number of allocated IPs (Active or Reserved)."""
        return sum(1 for ip in self.ip_addresses if ip.status in ("Active", "Reserved"))
    
    @property
    def available_ips(self) -> int:
        """Number of available IPs."""
        return sum(1 for ip in self.ip_addresses if ip.status == "Deprecated")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "namespace_id": 1,
                "cidr": "192.168.1.0/24",
                "label": "Web Tier",
                "created_at": "2025-12-07T10:00:00"
            }
        }


class IPAddress(SQLModel, table=True):
    """
    IPAddress - Individual IP within a Subnet.
    FR-05: Atomic allocation marks IP as 'Active'.
    FR-06: Can be manually reserved with metadata.
    FR-07: Network and broadcast addresses excluded from allocation.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    subnet_id: int = Field(foreign_key="subnet.id")
    address: str = Field(index=True)
    status: str = Field(default="Deprecated")  # Active, Reserved, Deprecated
    hostname: Optional[str] = None
    description: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    subnet: Subnet = Relationship(back_populates="ip_addresses")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "subnet_id": 1,
                "address": "192.168.1.5",
                "status": "Active",
                "hostname": "web-server-01",
                "description": "Production web server",
                "updated_at": "2025-12-07T10:00:00"
            }
        }
