# IPAM Core System

**Enterprise-Grade IP Address Management (MVP) with Strict Consistency.**

## Overview

IPAM Core is a specialized tool designed to manage IPv4 address allocations with mathematical precision. Unlike spreadsheet tracking, it strictly enforces non-overlapping constraints and provides automated provisioning tools to prevent network fragmentation.

## Architecture

- **Backend**: Python 3.10 + FastAPI + SQLModel (Centralized Logic Layer)
- **Database**: PostgreSQL 16 (Production) / SQLite (Local Dev)
- **Frontend**: Next.js 16 + TailwindCSS + Lucide Icons (Visualizer)
- **Infrastructure**: Docker Compose

## Features

- **Strict Consistency**: Mathematical validation prevents overlapping subnets.
- **VRF Support**: Isolated Namespaces (Prod, Dev, etc.).
- **Smart Provisioning**: "Magic Wand" automation to find free IP blocks.
- **Visualizer**: Real-time Interactive Grid for subnet utilization.
- **Metadata**: VLAN ID and Location tracking.

## Getting Started

### Option A: Local Development (Recommended)

Run the system natively using the included orchestration script. This mode uses **SQLite** and requires Python/Node.js installed.

1.  **Launch the Stack:**
    ```powershell
    .\start-dev.ps1
    ```
    *This will launch the Backend API.*

2.  **Launch Frontend:**
    Open a new terminal window:
    ```bash
    cd frontend
    npm run dev
    ```

3.  **Access:**
    - Dashboard: [http://localhost:3000](http://localhost:3000)
    - API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)

### Option B: Docker Containers

For a full containerized deployment using PostgreSQL.

1.  **Build and Run:**
    ```bash
    docker compose up --build
    ```

2.  **Access Services:**
    - Frontend: [http://localhost:3000](http://localhost:3000)
    - Backend: [http://localhost:8000/docs](http://localhost:8000/docs)

## API Endpoints

- `GET /namespaces`: List all environments.
- `POST /subnets`: Create subnet (Validates Overlap, VLAN, Location).
- `GET /namespaces/{id}/suggest-cidr`: Automated next-free-block calculation.
- `POST /subnets/{id}/allocate`: IP Reservation.

## License

Proprietary Software - Draka Labs.
