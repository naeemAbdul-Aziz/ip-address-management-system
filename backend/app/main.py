from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlmodel import Session, select, create_engine, SQLModel
from typing import List
import os
import ipaddress
from .models import Namespace, Subnet, IPAddress, IPStatus, SubnetBase
from .logic import (
    validate_overlap, 
    get_next_available_ip, 
    calculate_utilization, 
    find_next_free_subnet
)

app = FastAPI(title="IPAM Core", version="1.0.0")

# Database Setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
# Add retry/wait logic in real prod, but docker healthchecks handle this mostly
engine = create_engine(DATABASE_URL)

def get_session():
    with Session(engine) as session:
        yield session

from sqlalchemy import text

@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    
    # Auto-migration for 'cidr' column to fix production DB
    with Session(engine) as session:
        try:
            # Check if column exists by trying to read it
            session.exec(text("SELECT cidr FROM namespace LIMIT 1"))
        except Exception:
            print("⚠️ Migration: Column 'cidr' missing. Attempting to add it...")
            try:
                # Add column with default
                session.connection().execute(text("ALTER TABLE namespace ADD COLUMN cidr VARCHAR DEFAULT '10.0.0.0/8'"))
                session.commit()
                print("✅ Migration: Successfully added 'cidr' column.")
            except Exception as e:
                print(f"❌ Migration failed: {e}")
                
    yield

app = FastAPI(title="IPAM Core", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
engine = create_engine(DATABASE_URL)

def get_session():
    with Session(engine) as session:
        yield session

# --- Namespaces ---

@app.get("/namespaces", response_model=List[Namespace])
def list_namespaces(session: Session = Depends(get_session)):
    return session.exec(select(Namespace)).all()

@app.post("/namespaces", response_model=Namespace, status_code=201)
def create_namespace(namespace: Namespace, session: Session = Depends(get_session)):
    # Validate CIDR
    try:
        ipaddress.ip_network(namespace.cidr, strict=False)
    except ValueError:
         raise HTTPException(status_code=400, detail="Invalid Root CIDR format")

    existing = session.exec(select(Namespace).where(Namespace.name == namespace.name)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Namespace already exists")
    session.add(namespace)
    session.commit()
    session.refresh(namespace)
    return namespace

@app.get("/namespaces/{id}/suggest-cidr")
def suggest_cidr(id: int, prefix: int = 24, session: Session = Depends(get_session)):
    namespace = session.get(Namespace, id)
    if not namespace:
        raise HTTPException(status_code=404, detail="Namespace not found")
        
    existing_subnets = session.exec(select(Subnet).where(Subnet.namespace_id == id)).all()
    
    # Use namespace.cidr as root
    suggestion = find_next_free_subnet(existing_subnets, prefix, root_cidr=namespace.cidr)
    if not suggestion:
        raise HTTPException(status_code=400, detail="No available space in this namespace scope")
        
    return {"cidr": suggestion}

# --- Subnets ---

class SubnetCreate(SQLModel):
    namespace_id: int
    cidr: str
    label: str

class SubnetRead(SubnetBase):
    id: int
    utilization: float

@app.post("/subnets", response_model=Subnet, status_code=201)
def create_subnet(subnet_data: SubnetCreate, session: Session = Depends(get_session)):
    # 1. Check Namespace exists
    namespace = session.get(Namespace, subnet_data.namespace_id)
    if not namespace:
        raise HTTPException(status_code=404, detail="Namespace not found")

    # 2. Overlap Check
    existing_subnets = session.exec(select(Subnet).where(Subnet.namespace_id == subnet_data.namespace_id)).all()
    
    try:
        if validate_overlap(subnet_data.cidr, existing_subnets):
            raise HTTPException(status_code=409, detail="CIDR overlaps with an existing subnet in this namespace")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 3. Create
    subnet = Subnet.model_validate(subnet_data)
    session.add(subnet)
    session.commit()
    session.refresh(subnet)
    return subnet

@app.get("/subnets/{subnet_id}", response_model=SubnetRead)
def get_subnet(subnet_id: int, session: Session = Depends(get_session)):
    subnet = session.get(Subnet, subnet_id)
    if not subnet:
        raise HTTPException(status_code=404, detail="Subnet not found")
    
    # Calculate utilization
    allocated_count = session.query(IPAddress).filter(IPAddress.subnet_id == subnet.id, IPAddress.status == IPStatus.ACTIVE).count()
    util = calculate_utilization(allocated_count, subnet.cidr)
    
    # Create SubnetRead object manually
    result = SubnetRead(
        id=subnet.id,
        namespace_id=subnet.namespace_id,
        cidr=subnet.cidr,
        label=subnet.label,
        vlan_id=subnet.vlan_id,
        location=subnet.location,
        utilization=util
    )
    return result

@app.get("/subnets", response_model=List[SubnetRead])
def list_subnets(namespace_id: int = None, session: Session = Depends(get_session)):
    query = select(Subnet)
    if namespace_id:
        query = query.where(Subnet.namespace_id == namespace_id)
    subnets = session.exec(query).all()
    
    results = []
    for s in subnets:
        count = session.query(IPAddress).filter(IPAddress.subnet_id == s.id, IPAddress.status == IPStatus.ACTIVE).count()
        util = calculate_utilization(count, s.cidr)
        # Create SubnetRead object manually to include calculated field
        res = SubnetRead(
            id=s.id,
            namespace_id=s.namespace_id,
            cidr=s.cidr,
            label=s.label,
            vlan_id=s.vlan_id,
            location=s.location,
            utilization=util
        )
        results.append(res)
    return results

# --- IPs ---

@app.post("/subnets/{subnet_id}/allocate", response_model=IPAddress, status_code=201)
def allocate_ip(subnet_id: int, session: Session = Depends(get_session)):
    subnet = session.get(Subnet, subnet_id)
    if not subnet:
        raise HTTPException(status_code=404, detail="Subnet not found")
        
    # Get all currently allocated IPs
    allocated_ips = session.exec(select(IPAddress.address).where(IPAddress.subnet_id == subnet_id)).all()
    
    next_ip = get_next_available_ip(subnet.cidr, allocated_ips)
    if not next_ip:
        raise HTTPException(status_code=507, detail="Subnet is full")
        
    new_ip = IPAddress(subnet_id=subnet.id, address=next_ip, status=IPStatus.ACTIVE)
    session.add(new_ip)
    session.commit()
    session.refresh(new_ip)
    return new_ip

@app.get("/subnets/{subnet_id}/ips", response_model=List[IPAddress])
def list_subnet_ips(subnet_id: int, session: Session = Depends(get_session)):
    return session.exec(select(IPAddress).where(IPAddress.subnet_id == subnet_id)).all()
