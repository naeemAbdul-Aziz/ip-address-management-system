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

from .models import Namespace, Subnet, IPAddress, IPStatus, SubnetBase
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
                try:
                    session.connection().execute(text("ALTER TABLE namespace ADD COLUMN cidr VARCHAR DEFAULT '10.0.0.0/8'"))
                    session.commit()
                    logger.info("✅ Successfully added 'cidr' column")
                except Exception as migration_error:
                    logger.error(f"❌ Migration failed: {str(migration_error)}")
                    
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

@app.post("/subnets/{subnet_id}/allocate", response_model=IPAddress, status_code=201)
def allocate_ip(subnet_id: int, session: Session = Depends(get_session)):
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

        # Create and store IP
        new_ip = IPAddress(
            subnet_id=subnet.id,
            address=next_ip,
            status=IPStatus.ACTIVE
        )
        session.add(new_ip)
        session.commit()
        session.refresh(new_ip)

        log_database_operation("CREATE", "IPAddress", "success", details={"address": next_ip})
        log_operation("allocate_ip", "success", {"address": next_ip, "subnet_id": subnet_id})
        
        return new_ip

    except (ResourceNotFoundError, SubnetFullError) as e:
        raise e.to_http_exception()
    except Exception as e:
        log_error(e, "allocate_ip", {"subnet_id": subnet_id})
        raise HTTPException(status_code=500, detail="Failed to allocate IP address")


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
