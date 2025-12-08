# IPAM Core - User Manual

## 1. Introduction
**IPAM Core** is a lightweight, high-performance IP Address Management system designed for enterprise network environments. It simplifies the tracking of IP space (Namespaces), Subnets, and devices using a modern, automated approach.

**Key Features:**
*   **Hierarchical Management**: Namespaces (VRFs) > Subnets > IPs.
*   **Smart Provisioning**: Auto-creates Device entities during IP allocation.
*   **Visualizer**: Apple-style grid visualization for subnet utilization.
*   **Validation**: Prevents CIDR overlaps and enforces strict IP rules.

---

## 2. Getting Started

### Accessing the System
*   **Production URL**: `https://ipam-frontend.onrender.com` (or your internal deployment URL).
*   **Supported Browsers**: Chrome, Firefox, Safari, Edge (Desktop & Mobile).

### Authentication
The system handles sensitive network data and is protected by secure authentication.
1.  **Login**: You will be redirected to the login page automatically.
2.  **Credentials**: Use the credentials provided by your IT Admin.
    *   *Default (MVP)*: `admin` / `admin`
3.  **Session**: Your session is valid for 24 hours. After that, you must log in again.

---

## 3. Managing Networks (Namespaces)
A **Namespace** represents a high-level network container, often corresponding to a physical site (e.g., "NY Office") or a logical zone (e.g., "AWS Prod").

### Creating a Namespace
1.  On the Dashboard, click **"Create Namespace"**.
2.  **Name**: Enter a unique name (e.g., `Data Center A`).
3.  **Root CIDR**: Define the total scope for this namespace.
    *   *Presets*: Select standard private ranges (`10.0.0.0/8`, `192.168.0.0/16`).
    *   *Custom*: Select "Custom" and type any valid CIDR (e.g., `10.50.0.0/16`).
4.  Click **Create**.

> **Note**: You cannot create subnets outside of this Root CIDR scope.

---

## 4. Managing Subnets
Subnets are segments within a Namespace where devices live.

### Creating a Subnet
1.  Select a Namespace from the dashboard.
2.  Click **"Add Subnet"**.
3.  **CIDR**: Enter the subnet range (e.g., `10.0.1.0/24`). It must not overlap with existing subnets.
4.  **Label**: A descriptive tag (e.g., "Web Servers", "Guest WiFi").
5.  **VLAN ID**: (Optional) The VLAN tag associated with this network.
6.  **Location**: (Optional) Physical location (e.g., "Rack 2, Row 4").

### Visualizing Utilization
Click on any Subnet card to open the **IP Grid**.
*   **White Box**: Free IP.
*   **Black Box**: Active/Allocated IP.
*   **Orange Box**: Reserved IP (Gateway/Broadcast).

---

## 5. IP Allocation & Devices
IPAM Core moves beyond simple spreadsheets by linking IPs to **Device Entities**.

### Allocating an IP (Smart Provisioning)
1.  Open a Subnet's Grid View.
2.  Click **"+ Allocate New"** (or click a specific White box).
3.  **Device Prompt**: You will be asked for a "Device Name / Hostname".
    *   **New Device**: Type a new name (e.g., `new-laptop-01`). The system creates the Device record automatically and links the IP.
    *   **Existing Device**: Type an existing name. The system links this new IP to that existing device (multi-homed).
4.  The IP becomes **Active (Black)**.

### Releasing an IP
1.  Click on an **Active (Black)** IP box.
2.  A confirmation dialog will appear: *"Release IP x.x.x.x?"*.
3.  Click **OK**. The IP is freed and the link to the device is removed. (The Device entity itself remains in the database for history).

---

## 6. Search & Discovery
Use the global **Search Bar** at the top of the application to find resources instantly.
*   **Search by IP**: Type `192.168.1.5` to find exactly where it is used.
*   **Search by Hostname**: Type `printer` to see all printer devices.
*   **Search by CIDR**: Type `10.10` to filter matching subnets.

---

## 7. Troubleshooting

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| **Login Failed** | Invalid credentials | Check caps lock. Ask admin for password reset. |
| **"Subnet Full"** | No free IPs in /24 | Create a new subnet or release unused IPs. |
| **"CIDR Overlap"** | New subnet conflicts with existing | Choose a different range (e.g., increment the third octet). |
| **"Network Error"** | Backend API unreachable | Refresh page. Check if the API server is running/deployed. |

---

## 8. API Access (Advanced)
Developers can interact with the system programmatically using the REST API.
*   **Documentation**: `https://ipam-frontend.onrender.com/docs` (Swagger UI).
*   **Authentication**: Obtain a bearer token via `POST /token` before making requests.
