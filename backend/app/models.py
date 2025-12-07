from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from enum import Enum

class IPStatus(str, Enum):
    ACTIVE = "active"
    RESERVED = "reserved"
    DEPRECATED = "deprecated"

# --- Namespace ---
class NamespaceBase(SQLModel):
    name: str = Field(index=True, unique=True)
    cidr: str = Field(default="10.0.0.0/8", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Namespace(NamespaceBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    subnets: List["Subnet"] = Relationship(back_populates="namespace")

# --- Subnet ---
class SubnetBase(SQLModel):
    namespace_id: int = Field(foreign_key="namespace.id")
    cidr: str = Field(index=True)
    label: str
    vlan_id: Optional[int] = Field(default=None)
    location: Optional[str] = Field(default=None)

class Subnet(SubnetBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    namespace: Namespace = Relationship(back_populates="subnets")
    ips: List["IPAddress"] = Relationship(back_populates="subnet")

# --- IP ---
class IPAddressBase(SQLModel):
    subnet_id: int = Field(foreign_key="subnet.id")
    address: str = Field(index=True)
    status: IPStatus = Field(default=IPStatus.ACTIVE)
    hostname: Optional[str] = None
    description: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class IPAddress(IPAddressBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    subnet: Subnet = Relationship(back_populates="ips")
