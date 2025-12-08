"""
IPAM Core FastAPI Application with comprehensive logging and error handling.
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlmodel import Session, select, create_engine, SQLModel
from typing import List, Optional
import os
import ipaddress
import time
import logging

from .models import Namespace, Subnet, IPAddress, IPStatus, SubnetBase, Device, DeviceBase
from .logic import (
    validate_overlap, 
    get_next_available_ip, 
    calculate_utilization, 
    find_next_free_subnet
)
from .logger import logger, log_operation, log_request, log_error, log_database_operation
from .exceptions import (
    ValidationError,
    ResourceNotFoundError,
    DuplicateResourceError,
    CIDROverlapError,
    SubnetFullError,
    InvalidCIDRError,
    DatabaseError,
)

# Database Setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
engine = create_engine(DATABASE_URL, echo=False)


def get_session():
    """Dependency to get database session with error handling."""
    with Session(engine) as session:
        yield session


from sqlalchemy import text

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    logger.info("🚀 IPAM Core starting up...")
    
    try:
        # Create database schema
        SQLModel.metadata.create_all(engine)
        logger.info("✅ Database schema created/verified")
        
        # Auto-migration for 'cidr' column to fix production DB
        with Session(engine) as session:
            try:
                session.exec(text("SELECT cidr FROM namespace LIMIT 1"))
                logger.info("✅ Database schema validation passed")
            except Exception as e:
                logger.warning(f"⚠️ Schema migration needed: {str(e)}")
                session.rollback() # Fix: Rollback the failed transaction (SELECT) before starting a new one (ALTER)
                try:
                    session.connection().execute(text("ALTER TABLE namespace ADD COLUMN cidr VARCHAR DEFAULT '10.0.0.0/8'"))
                    session.commit()
                    logger.info("✅ Successfully added 'cidr' column")
                except Exception as migration_error:
                    logger.error(f"❌ Migration failed: {str(migration_error)}")
                    
        # Auto-migration for 'device_id' column
        with Session(engine) as session:
            try:
                session.exec(text("SELECT device_id FROM ipaddress LIMIT 1"))
                logger.info("✅ Database schema (devices) validation passed")
            except Exception as e:
                logger.warning(f"⚠️ Device schema migration needed: {str(e)}")
                session.rollback()
                try:
                    # SQLite and Postgres handle adding FKs differently, keeping it simple for now (no constraint enforcement in raw SQL to avoid dialect issues)
                    session.connection().execute(text("ALTER TABLE ipaddress ADD COLUMN device_id INTEGER")) 
                    session.commit()
                    logger.info("✅ Successfully added 'device_id' column")
                except Exception as migration_error:
                    logger.error(f"❌ Device Migration failed: {str(migration_error)}")
                    
    except Exception as e:
        logger.error(f"❌ Startup failed: {str(e)}", exc_info=True)
        raise
    
    yield
    
    logger.info("🛑 IPAM Core shutting down...")


app = FastAPI(
    title="IPAM Core",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    openapi_url="/openapi.json",
)

# CORS configuration - allow both localhost (dev) and container network (docker)
allowed_origins = [
    "http://localhost:3000",      # Local development
    "http://localhost:8000",      # Local backend
    "http://ipam_frontend:3000",  # Docker container
    "http://127.0.0.1:3000",      # Localhost alias
    "https://ipam-frontend.onrender.com", # Production Frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_logging(request, call_next):
    """Middleware to log all HTTP requests with timing."""
    start_time = time.time()
    path = request.url.path
    method = request.method
    
    try:
        response = await call_next(request)
        duration = (time.time() - start_time) * 1000
        log_request(method, path, response.status_code, duration)
        return response
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.error(f"Request failed: {method} {path}", exc_info=True)
        raise


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with proper logging."""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail}")
    return {"error_code": "HTTP_ERROR", "message": exc.detail}


from fastapi.security import OAuth2PasswordRequestForm
from .auth import create_access_token, get_current_user, verify_password, get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES, timedelta

# ... (Database Setup code remains) ...

# Hardcoded Admin User for MVP
FAKE_USERS_DB = {
    "admin": {
        "username": "admin",
        "full_name": "System Administrator",
        "hashed_password": get_password_hash("admin") # In production use env var!
    }
}

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = FAKE_USERS_DB.get(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


# ============================================================================
# SEARCH ENDPOINTS
# ============================================================================

@app.get("/search")
def search(q: str, session: Session = Depends(get_session)):
    """Search for IPs or Subnets."""
    if len(q) < 2:
        return {"results": []}
    
    results = []
    
    # Search IPs
    ips = session.exec(
        select(IPAddress)
        .where(
            (IPAddress.address.contains(q)) | 
            (IPAddress.hostname.contains(q))
        )
        .limit(10)
    ).all()
    
    for ip in ips:
        results.append({
            "type": "ip",
            "id": ip.id,
            "title": ip.address,
            "subtitle": ip.hostname or "No Hostname",
            "link": "#" # Frontend will handle navigation
        })

    # Search Subnets
    subnets = session.exec(
        select(Subnet)
        .where(
            (Subnet.cidr.contains(q)) | 
            (Subnet.label.contains(q))
        )
        .limit(5)
    ).all()
    
    for subnet in subnets:
        results.append({
            "type": "subnet",
            "id": subnet.id,
            "title": subnet.cidr,
            "subtitle": subnet.label,
            "link": "#"
        })
        
    return {"results": results}


# ============================================================================
# NAMESPACE ENDPOINTS
# ============================================================================

@app.get("/namespaces", response_model=List[Namespace])
def list_namespaces(session: Session = Depends(get_session)):
    """List all namespaces."""
    try:
        namespaces = session.exec(select(Namespace)).all()
        log_database_operation("READ", "Namespace", "success", count=len(namespaces))
        return namespaces
    except Exception as e:
        log_error(e, "list_namespaces")
        raise HTTPException(status_code=500, detail="Failed to fetch namespaces")


@app.post("/namespaces", response_model=Namespace, status_code=201)
def create_namespace(namespace: Namespace, session: Session = Depends(get_session)):
    """Create a new namespace with validation and error handling."""
    try:
        # Validate CIDR format
        try:
            ipaddress.ip_network(namespace.cidr, strict=False)
        except ValueError as e:
            log_operation("create_namespace", "failed", {"reason": "invalid_cidr", "cidr": namespace.cidr})
            raise InvalidCIDRError(namespace.cidr)

        # Check for duplicates
        existing = session.exec(
            select(Namespace).where(Namespace.name == namespace.name)
        ).first()
        if existing:
            log_operation("create_namespace", "failed", {"reason": "duplicate", "name": namespace.name})
            raise DuplicateResourceError("Namespace", namespace.name)

        # Create namespace
        session.add(namespace)
        session.commit()
        session.refresh(namespace)
        
        log_database_operation("CREATE", "Namespace", "success", details={"id": namespace.id, "name": namespace.name})
        log_operation("create_namespace", "success", {"id": namespace.id, "name": namespace.name})
        
        return namespace
        
    except (ValidationError, DuplicateResourceError, InvalidCIDRError) as e:
        raise e.to_http_exception()
    except Exception as e:
        log_error(e, "create_namespace", {"namespace": namespace.name})
        raise HTTPException(status_code=500, detail="Failed to create namespace")


@app.get("/namespaces/{namespace_id}", response_model=Namespace)
def get_namespace(namespace_id: int, session: Session = Depends(get_session)):
    """Retrieve a specific namespace by ID."""
    try:
        namespace = session.get(Namespace, namespace_id)
        if not namespace:
            log_operation("get_namespace", "failed", {"namespace_id": namespace_id, "reason": "not_found"})
            raise ResourceNotFoundError("Namespace", namespace_id)
        
        log_database_operation("READ", "Namespace", "success")
        return namespace
        
    except ResourceNotFoundError as e:
        raise e.to_http_exception()
    except Exception as e:
        log_error(e, "get_namespace", {"namespace_id": namespace_id})
        raise HTTPException(status_code=500, detail="Failed to fetch namespace")


@app.get("/namespaces/{namespace_id}/suggest-cidr")
def suggest_cidr(namespace_id: int, prefix: int = 24, session: Session = Depends(get_session)):
    """Suggest the next available CIDR block for a namespace."""
    try:
        namespace = session.get(Namespace, namespace_id)
        if not namespace:
            raise ResourceNotFoundError("Namespace", namespace_id)

        existing_subnets = session.exec(
            select(Subnet).where(Subnet.namespace_id == namespace_id)
        ).all()

        suggestion = find_next_free_subnet(
            existing_subnets,
            prefix,
            root_cidr=namespace.cidr
        )
        
        if not suggestion:
            log_operation("suggest_cidr", "failed", {"namespace_id": namespace_id, "reason": "no_space"})
            raise ValidationError(
                "No available space in this namespace scope",
                {"namespace_id": namespace_id, "prefix": prefix}
            )

        log_operation("suggest_cidr", "success", {"suggestion": suggestion})
        return {"cidr": suggestion}
        
    except (ResourceNotFoundError, ValidationError) as e:
        raise e.to_http_exception()
    except Exception as e:
        log_error(e, "suggest_cidr", {"namespace_id": namespace_id})
        raise HTTPException(status_code=500, detail="Failed to suggest CIDR")


# ============================================================================
# SUBNET ENDPOINTS
# ============================================================================

class SubnetCreate(SQLModel):
    """Model for creating a new subnet."""
    namespace_id: int
    cidr: str
    label: str
    vlan_id: Optional[int] = None
    location: Optional[str] = None


class SubnetRead(SubnetBase):
    """Model for reading subnet with calculated fields."""
    id: int
    utilization: float


@app.post("/subnets", response_model=Subnet, status_code=201)
def create_subnet(subnet_data: SubnetCreate, session: Session = Depends(get_session)):
    """Create a new subnet with CIDR overlap validation."""
    try:
        # 1. Validate namespace exists
        namespace = session.get(Namespace, subnet_data.namespace_id)
        if not namespace:
            raise ResourceNotFoundError("Namespace", subnet_data.namespace_id)

        # 2. Check for CIDR overlaps
        existing_subnets = session.exec(
            select(Subnet).where(Subnet.namespace_id == subnet_data.namespace_id)
        ).all()

        try:
            if existing_subnets:
                existing_cidrs = [s.cidr for s in existing_subnets]
                if validate_overlap(subnet_data.cidr, existing_subnets):
                    raise CIDROverlapError(subnet_data.cidr, existing_cidrs)
        except ValueError as e:
            raise InvalidCIDRError(subnet_data.cidr, {"error": str(e)})

        # 3. Create subnet
        subnet = Subnet.model_validate(subnet_data)
        session.add(subnet)
        session.commit()
        session.refresh(subnet)

        log_database_operation("CREATE", "Subnet", "success", details={"id": subnet.id, "cidr": subnet.cidr})
        log_operation("create_subnet", "success", {"id": subnet.id, "cidr": subnet.cidr})
        
        return subnet

    except (ResourceNotFoundError, CIDROverlapError, InvalidCIDRError) as e:
        raise e.to_http_exception()
    except Exception as e:
        log_error(e, "create_subnet", {"namespace_id": subnet_data.namespace_id})
        raise HTTPException(status_code=500, detail="Failed to create subnet")


@app.get("/subnets", response_model=List[SubnetRead])
def list_subnets(namespace_id: Optional[int] = None, session: Session = Depends(get_session)):
    """List all subnets, optionally filtered by namespace."""
    try:
        query = select(Subnet)
        if namespace_id:
            query = query.where(Subnet.namespace_id == namespace_id)
        
        subnets = session.exec(query).all()
        
        results = []
        for subnet in subnets:
            try:
                allocated_count = session.query(IPAddress).filter(
                    IPAddress.subnet_id == subnet.id,
                    IPAddress.status == IPStatus.ACTIVE
                ).count()
                utilization = calculate_utilization(allocated_count, subnet.cidr)
            except Exception as e:
                logger.warning(f"Failed to calculate utilization for subnet {subnet.id}: {str(e)}")
                utilization = 0.0

            result = SubnetRead(
                id=subnet.id,
                namespace_id=subnet.namespace_id,
                cidr=subnet.cidr,
                label=subnet.label,
                vlan_id=subnet.vlan_id,
                location=subnet.location,
                utilization=utilization
            )
            results.append(result)

        log_database_operation("READ", "Subnet", "success", count=len(results))
        return results

    except Exception as e:
        log_error(e, "list_subnets", {"namespace_id": namespace_id})
        raise HTTPException(status_code=500, detail="Failed to fetch subnets")


@app.get("/subnets/{subnet_id}", response_model=SubnetRead)
def get_subnet(subnet_id: int, session: Session = Depends(get_session)):
    """Get subnet details with utilization percentage."""
    try:
        subnet = session.get(Subnet, subnet_id)
        if not subnet:
            raise ResourceNotFoundError("Subnet", subnet_id)

        allocated_count = session.query(IPAddress).filter(
            IPAddress.subnet_id == subnet.id,
            IPAddress.status == IPStatus.ACTIVE
        ).count()
        utilization = calculate_utilization(allocated_count, subnet.cidr)

        result = SubnetRead(
            id=subnet.id,
            namespace_id=subnet.namespace_id,
            cidr=subnet.cidr,
            label=subnet.label,
            vlan_id=subnet.vlan_id,
            location=subnet.location,
            utilization=utilization
        )
        
        log_database_operation("READ", "Subnet", "success")
        return result

    except ResourceNotFoundError as e:
        raise e.to_http_exception()
    except Exception as e:
        log_error(e, "get_subnet", {"subnet_id": subnet_id})
        raise HTTPException(status_code=500, detail="Failed to fetch subnet")


# ============================================================================
# IP ADDRESS ENDPOINTS
# ============================================================================

# ============================================================================
# DEVICE ENDPOINTS
# ============================================================================

@app.get("/devices", response_model=List[Device])
def list_devices(session: Session = Depends(get_session)):
    """List all devices."""
    return session.exec(select(Device)).all()

@app.post("/devices", response_model=Device, status_code=201)
def create_device(device: DeviceBase, session: Session = Depends(get_session)):
    """Create a new device manually."""
    try:
        db_device = Device.model_validate(device)
        session.add(db_device)
        session.commit()
        session.refresh(db_device)
        return db_device
    except Exception as e:
        log_error(e, "create_device")
        raise HTTPException(status_code=500, detail="Failed to create device")


# ============================================================================
# IP ADDRESS ENDPOINTS
# ============================================================================

class IPAllocationRequest(SQLModel):
    hostname: Optional[str] = None # Treat as Device Name

@app.post("/subnets/{subnet_id}/allocate", response_model=IPAddress, status_code=201)
def allocate_ip(
    subnet_id: int, 
    request: Optional[IPAllocationRequest] = None,
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user) # Protected
):
    """Allocate the next available IP address from a subnet."""
    try:
        subnet = session.get(Subnet, subnet_id)
        if not subnet:
            raise ResourceNotFoundError("Subnet", subnet_id)

        # Get currently allocated IPs
        allocated_ips = session.exec(
            select(IPAddress.address).where(IPAddress.subnet_id == subnet_id)
        ).all()

        # Find next available IP
        next_ip = get_next_available_ip(subnet.cidr, allocated_ips)
        if not next_ip:
            raise SubnetFullError(subnet_id, subnet.cidr)

        # Smart Provisioning: Handle Device
        device_id = None
        hostname = None
        
        if request and request.hostname:
            hostname = request.hostname
            # Check if device exists
            device = session.exec(select(Device).where(Device.name == request.hostname)).first()
            if not device:
                # Auto-create device
                device = Device(name=request.hostname, type="auto-created")
                session.add(device)
                session.commit()
                session.refresh(device)
                log_operation("allocate_ip", "device_created", {"device_name": device.name})
            
            device_id = device.id

        # Create and store IP
        new_ip = IPAddress(
            subnet_id=subnet.id,
            address=next_ip,
            status=IPStatus.ACTIVE,
            hostname=hostname, # Keep legacy field populated for now
            device_id=device_id
        )
        session.add(new_ip)
        session.commit()
        session.refresh(new_ip)

        log_database_operation("CREATE", "IPAddress", "success", details={"address": next_ip, "device": hostname})
        log_operation("allocate_ip", "success", {"address": next_ip, "subnet_id": subnet_id})
        
        return new_ip

    except (ResourceNotFoundError, SubnetFullError) as e:
        raise e.to_http_exception()
    except Exception as e:
        log_error(e, "allocate_ip", {"subnet_id": subnet_id})
        raise HTTPException(status_code=500, detail="Failed to allocate IP address")


class IPReservationRequest(SQLModel):
    address: Optional[str] = None # If None, next available
    description: Optional[str] = "Reserved manually"

@app.post("/subnets/{subnet_id}/reserve", response_model=IPAddress, status_code=201)
def reserve_ip(
    subnet_id: int, 
    request: IPReservationRequest,
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user)
):
    """Manually reserve an IP address (Mark as Reserved)."""
    try:
        subnet = session.get(Subnet, subnet_id)
        if not subnet:
            raise ResourceNotFoundError("Subnet", subnet_id)

        target_ip = request.address
        
        # If no specific IP, find next free
        if not target_ip:
            allocated_ips = session.exec(select(IPAddress.address).where(IPAddress.subnet_id == subnet_id)).all()
            target_ip = get_next_available_ip(subnet.cidr, allocated_ips)
            if not target_ip:
                raise SubnetFullError(subnet_id, subnet.cidr)

        # Check if already taken
        existing = session.exec(
            select(IPAddress).where(IPAddress.subnet_id == subnet_id, IPAddress.address == target_ip)
        ).first()
        
        if existing:
            # If it exists, we can force update or error. Error is safer for now.
            raise DuplicateResourceError("IPAddress", target_ip)

        # Create Reserved IP
        new_ip = IPAddress(
            subnet_id=subnet.id,
            address=target_ip,
            status=IPStatus.RESERVED,
            description=request.description
        )
        session.add(new_ip)
        session.commit()
        session.refresh(new_ip)
        
        log_database_operation("CREATE", "IPAddress", "success", details={"address": target_ip, "status": "reserved"})
        return new_ip

    except (ResourceNotFoundError, DuplicateResourceError, SubnetFullError) as e:
        raise e.to_http_exception()
    except Exception as e:
        log_error(e, "reserve_ip", {"subnet_id": subnet_id})
        raise HTTPException(status_code=500, detail="Failed to reserve IP")


@app.get("/subnets/{subnet_id}/ips", response_model=List[IPAddress])
def list_subnet_ips(subnet_id: int, status_filter: Optional[str] = None, session: Session = Depends(get_session)):
    """List all IPs in a subnet, optionally filtered by status."""
    try:
        # Verify subnet exists
        subnet = session.get(Subnet, subnet_id)
        if not subnet:
            raise ResourceNotFoundError("Subnet", subnet_id)

        query = select(IPAddress).where(IPAddress.subnet_id == subnet_id)
        if status_filter:
            query = query.where(IPAddress.status == status_filter)

        ips = session.exec(query).all()
        
        log_database_operation("READ", "IPAddress", "success", count=len(ips))
        return ips

    except ResourceNotFoundError as e:
        raise e.to_http_exception()
    except Exception as e:
        log_error(e, "list_subnet_ips", {"subnet_id": subnet_id})
        raise HTTPException(status_code=500, detail="Failed to fetch IP addresses")


@app.delete("/ips/{ip_id}", status_code=204)
def release_ip(
    ip_id: int, 
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user) # Protected
):
    """Release (delete) an allocated IP address."""
    try:
        ip = session.get(IPAddress, ip_id)
        if not ip:
            raise ResourceNotFoundError("IPAddress", ip_id)

        session.delete(ip)
        session.commit()
        
        log_database_operation("DELETE", "IPAddress", "success", details={"id": ip_id, "address": ip.address})
        log_operation("release_ip", "success", {"id": ip_id, "address": ip.address})
        return None

    except ResourceNotFoundError as e:
        raise e.to_http_exception()
    except Exception as e:
        log_error(e, "release_ip", {"ip_id": ip_id})
        raise HTTPException(status_code=500, detail="Failed to release IP address")


# ============================================================================
# HEALTH & STATUS ENDPOINTS
# ============================================================================

@app.get("/health")
def health_check():
    """Health check endpoint for monitoring."""
    try:
        # Test database connection
        with Session(engine) as session:
            session.exec(text("SELECT 1"))
        return {
            "status": "healthy",
            "version": "1.0.0",
            "database": "connected"
        }
    except Exception as e:
        logger.error("Health check failed", exc_info=True)
        return {
            "status": "unhealthy",
            "version": "1.0.0",
            "database": "disconnected",
            "error": str(e)
        }, 503


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "name": "IPAM Core",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }
