from sqlmodel import Session, create_engine, select, SQLModel
import os
from app.models import Namespace, Subnet, IPAddress, IPStatus
from app.logic import get_next_available_ip

# Setup DB connection
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
# For local running without docker env, might need to adjust or pass explicitly
if "postgres" in DATABASE_URL:
    # If running inside docker container
    pass
else:
    # If running locally, you might want to point to localhost if port exposed
    # For now default to sqlite or assume env var is set
    pass

engine = create_engine(DATABASE_URL)
SQLModel.metadata.create_all(engine)

def seed():
    with Session(engine) as session:
        # 1. Namespaces
        ns_prod = session.exec(select(Namespace).where(Namespace.name == "Prod")).first()
        if not ns_prod:
            ns_prod = Namespace(name="Prod")
            session.add(ns_prod)
        
        ns_dev = session.exec(select(Namespace).where(Namespace.name == "Dev")).first()
        if not ns_dev:
            ns_dev = Namespace(name="Dev")
            session.add(ns_dev)
        
        session.commit()
        session.refresh(ns_prod)
        session.refresh(ns_dev)
        print(f"Namespaces seeded: {ns_prod.id}, {ns_dev.id}")

        # 2. Subnets
        # Prod Web
        s_web = session.exec(select(Subnet).where(Subnet.cidr == "192.168.1.0/24")).first()
        if not s_web:
            s_web = Subnet(namespace_id=ns_prod.id, cidr="192.168.1.0/24", label="Web Tier")
            session.add(s_web)
        
        # Dev Test
        s_test = session.exec(select(Subnet).where(Subnet.cidr == "10.0.0.0/24")).first()
        if not s_test:
            s_test = Subnet(namespace_id=ns_dev.id, cidr="10.0.0.0/24", label="Test Sandbox")
            session.add(s_test)
            
        session.commit()
        session.refresh(s_web)
        print("Subnets seeded")

        # 3. Allocations
        # Reserve first few in Web
        existing_ips = session.exec(select(IPAddress).where(IPAddress.subnet_id == s_web.id)).all()
        if not existing_ips:
            # Manually add Gateway
            gw = IPAddress(subnet_id=s_web.id, address="192.168.1.1", status=IPStatus.RESERVED, hostname="gateway")
            session.add(gw)
            
            # Allocate 5 dynamic
            for i in range(5):
                # Need to refresh allocated list logic or just hardcode for seed
                ip_addr = f"192.168.1.{10+i}"
                ip = IPAddress(subnet_id=s_web.id, address=ip_addr, status=IPStatus.ACTIVE, hostname=f"web-{i}")
                session.add(ip)
            
            session.commit()
            print("IPs seeded")

if __name__ == "__main__":
    seed()
