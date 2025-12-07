"""
IPAM Core API - FastAPI Application
Steel Thread MVP for IPv4 Address Management
"""
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, create_engine, SQLModel, select
from sqlalchemy.pool import StaticPool
import os
from contextlib import asynccontextmanager

from models import Namespace, Subnet, IPAddress
from services import validate_overlap, allocate_next_ip

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///ipam.db")

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        future=True,
    )


def create_db_and_tables():
    """Create database tables on startup."""
    SQLModel.metadata.create_all(engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context for startup/shutdown events."""
    create_db_and_tables()
    yield


app = FastAPI(
    title="IPAM Core API",
    description="High-integrity IPv4 address management system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_session():
    """Dependency to get database session."""
    with Session(engine) as session:
        yield session


# ============================================================================
# NAMESPACE ENDPOINTS
# ============================================================================

@app.post("/namespaces", response_model=Namespace, status_code=status.HTTP_201_CREATED)
def create_namespace(namespace: Namespace, session: Session = None):
    """Create a new namespace (VRF)."""
    if session is None:
        session = Session(engine)
    
    # Check for existing namespace
    existing = session.exec(select(Namespace).where(Namespace.name == namespace.name)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Namespace '{namespace.name}' already exists"
        )
    
    session.add(namespace)
    session.commit()
    session.refresh(namespace)
    return namespace


@app.get("/namespaces", response_model=list[Namespace])
def list_namespaces(session: Session = None):
    """List all namespaces."""
    if session is None:
        session = Session(engine)
    
    namespaces = session.exec(select(Namespace)).all()
    return namespaces


@app.get("/namespaces/{namespace_id}", response_model=Namespace)
def get_namespace(namespace_id: int, session: Session = None):
    """Get a specific namespace by ID."""
    if session is None:
        session = Session(engine)
    
    namespace = session.get(Namespace, namespace_id)
    if not namespace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Namespace {namespace_id} not found"
        )
    return namespace


# ============================================================================
# SUBNET ENDPOINTS
# ============================================================================

@app.post("/subnets", response_model=Subnet, status_code=status.HTTP_201_CREATED)
def create_subnet(subnet: Subnet, session: Session = None):
    """
    Create a new subnet with overlap validation.
    FR-03: Rejects overlapping CIDR blocks in the same Namespace.
    """
    if session is None:
        session = Session(engine)
    
    # Verify namespace exists
    namespace = session.get(Namespace, subnet.namespace_id)
    if not namespace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Namespace {subnet.namespace_id} not found"
        )
    
    # Get all existing subnets in this namespace
    existing_subnets = session.exec(
        select(Subnet).where(Subnet.namespace_id == subnet.namespace_id)
    ).all()
    
    # Check for overlaps
    try:
        if existing_subnets:
            existing_cidrs = [s.cidr for s in existing_subnets]
            validate_overlap(subnet.cidr, existing_cidrs)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    
    session.add(subnet)
    session.commit()
    session.refresh(subnet)
    
    # Populate all IP addresses for the subnet
    _populate_ips_for_subnet(subnet, session)
    
    return subnet


@app.get("/subnets", response_model=list[Subnet])
def list_subnets(namespace_id: int = None, session: Session = None):
    """List all subnets, optionally filtered by namespace."""
    if session is None:
        session = Session(engine)
    
    query = select(Subnet)
    if namespace_id:
        query = query.where(Subnet.namespace_id == namespace_id)
    
    subnets = session.exec(query).all()
    return subnets


@app.get("/subnets/{subnet_id}", response_model=Subnet)
def get_subnet(subnet_id: int, session: Session = None):
    """Get subnet details including utilization percentage."""
    if session is None:
        session = Session(engine)
    
    subnet = session.get(Subnet, subnet_id)
    if not subnet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subnet {subnet_id} not found"
        )
    return subnet


# ============================================================================
# IP ADDRESS ENDPOINTS
# ============================================================================

@app.post("/subnets/{subnet_id}/allocate", response_model=IPAddress, status_code=status.HTTP_201_CREATED)
def allocate_ip(subnet_id: int, hostname: str = None, session: Session = None):
    """
    Allocate the next available IP from a subnet.
    FR-05: Atomic allocation of next available IP.
    FR-07: Never allocates network or broadcast addresses.
    """
    if session is None:
        session = Session(engine)
    
    subnet = session.get(Subnet, subnet_id)
    if not subnet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subnet {subnet_id} not found"
        )
    
    try:
        ip_address = allocate_next_ip(subnet, hostname, session)
        session.commit()
        session.refresh(ip_address)
        return ip_address
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


@app.post("/ips/{ip_id}/reserve", response_model=IPAddress)
def reserve_ip(ip_id: int, hostname: str = None, description: str = None, session: Session = None):
    """
    Reserve a specific IP address.
    FR-06: Manual IP reservation with metadata.
    """
    if session is None:
        session = Session(engine)
    
    ip_address = session.get(IPAddress, ip_id)
    if not ip_address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IP {ip_id} not found"
        )
    
    ip_address.status = "Reserved"
    if hostname:
        ip_address.hostname = hostname
    
    session.add(ip_address)
    session.commit()
    session.refresh(ip_address)
    return ip_address


@app.post("/ips/{ip_id}/release", status_code=status.HTTP_204_NO_CONTENT)
def release_ip(ip_id: int, session: Session = None):
    """
    Release an IP address back to the pool.
    Sets status to 'Deprecated'.
    """
    if session is None:
        session = Session(engine)
    
    ip_address = session.get(IPAddress, ip_id)
    if not ip_address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IP {ip_id} not found"
        )
    
    ip_address.status = "Deprecated"
    ip_address.hostname = None
    session.add(ip_address)
    session.commit()


@app.get("/subnets/{subnet_id}/ips", response_model=list[IPAddress])
def list_subnet_ips(subnet_id: int, status_filter: str = None, session: Session = None):
    """List all IPs in a subnet, optionally filtered by status."""
    if session is None:
        session = Session(engine)
    
    query = select(IPAddress).where(IPAddress.subnet_id == subnet_id)
    if status_filter:
        query = query.where(IPAddress.status == status_filter)
    
    ips = session.exec(query).all()
    return ips


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _populate_ips_for_subnet(subnet: Subnet, session: Session):
    """Populate all usable IPs for a newly created subnet."""
    from ipaddress import ip_network
    
    network = ip_network(subnet.cidr, strict=False)
    usable_hosts = list(network.hosts())
    
    for host in usable_hosts:
        ip_obj = IPAddress(
            subnet_id=subnet.id,
            address=str(host),
            status="Deprecated"
        )
        session.add(ip_obj)
    
    session.commit()


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
