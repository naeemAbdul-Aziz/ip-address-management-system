# System Design Document: IPAM Core

**Version:** 1.0 (Enterprise MVP)
**Date:** December 07, 2025
**Status:** Production Ready
**Objective:** Deploy a mission-critical, high-integrity IPv4 address management system with strict consistency guarantees, automated provisioning, and enterprise-grade visualization.

---

## 1. High-Level Architecture

The system adheres to a **Modular Monolith** architecture, ensuring centralized logic and a Single Source of Truth for network data.

- **Backend:** Python 3.10+ with **FastAPI**.
- **Data Layer:** **SQLModel** (SQLAlchemy + Pydantic) supporting both **PostgreSQL** (Production) and **SQLite** (Edge/Local).
- **Frontend:** **Next.js 16** (React) with **Tailwind CSS**.
- **Orchestration:** Hybrid support for **Docker Compose** (Cloud Native) and **PowerShell** (Local Dev).

---

## 2. Functional Requirements (FR)

### 2.1 Namespace Isolation & Security
- **FR-01 (Multi-Tenancy):** System supports isolated "Namespaces" (e.g., Prod, Dev, DMZ) acting as logical VRF containers.
- **FR-02 (Overlap Enforcement):**
  - **Inter-Namespace:** Overlap is permitted (e.g., `10.0.0.1` can exist in both Prod and Dev).
  - **Intra-Namespace:** Overlap is strictly prohibited. The system enforces mathematical uniqueness for all CIDR blocks within a namespace.

### 2.2 Subnet Management & Automation
- **FR-03 (Strict Consistency):** All write operations pass through RFC 4632 validation to reject invalid or overlapping CIDR blocks.
- **FR-04 (Smart Provisioning):** Automated "Next Free Block" detection algorithm that analyzes existing subnets and suggests non-fragmented CIDR ranges based on requested prefix size (e.g., /24, /26).
- **FR-05 (Metadata):** Support for extended attributes including **VLAN ID** and **Physical Location**.

### 2.3 IP Lifecycle
- **FR-06 (Atomic Allocation):** Concurrency-safe IP reservation that guarantees uniqueness.
- **FR-07 (Utilization Tracking):** Real-time calculation of subnet density: `(Allocated IPs / Total Usable Hosts) * 100`.
- **FR-08 (Boundary Protection):** Automatic exclusion of Network and Broadcast addresses from the usable pool.

---

## 3. Data Model

| Entity | Field | Type | Constraint | Description |
|--------|-------|------|-----------|-------------|
| **Namespace** | id | Integer | PK | Unique identifier |
| | name | String | Unique | VRF/Environment Name |
| **Subnet** | id | Integer | PK | |
| | namespace_id | Integer | FK | Parent Namespace |
| | cidr | String | Index | e.g. 192.168.1.0/24 |
| | vlan_id | Integer | Optional | VLAN Tag (1-4094) |
| | location | String | Optional | Physical Site |
| **IPAddress** | id | Integer | PK | |
| | subnet_id | Integer | FK | Parent Subnet |
| | address | String | Index | IPv4 String |
| | status | Enum | | Active, Reserved, Deprecated |

---

## 4. Deployment Strategy

The system supports two primary deployment modes:

1.  **Local Development (SQLite):** Zero-dependency mode using a file-based database for rapid iteration and offline capability.
2.  **Containerized (Docker):** Full production stack with PostgreSQL, suitable for Kubernetes or Cloud deployment.
