# Anukram (अनुक्रम) | Enterprise Workflow Management System

<div align="center">

![Anukram Banner](https://img.shields.io/badge/Anukram-Enterprise%20Workflow%20Engine-4F46E5?style=for-the-badge&logo=django&logoColor=white)

[![Django](https://img.shields.io/badge/Django-6.0-092E20?style=flat-square&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)
[![Status](https://img.shields.io/badge/Build-Passing-brightgreen?style=flat-square)](#)

**Anukram** *(Sanskrit: अनुक्रम: "Sequence, Order, Process")* is a modern, multi-tenant enterprise workflow and permission management engine. It eliminates email chaos by transforming complex organizational requests into deterministic, automated multi-tier approval pipelines with digital signatures and QR-verifiable physical permission slips.

[Key Features](#-key-features) • [Architecture](#-system-architecture) • [Tech Stack](#-technology-stack) • [Quick Start](#-quick-start) • [Deployment](#-deployment-guide)

</div>

---

## 🌟 Why Anukram?

Enterprise approval chains often get stuck in fragmented email threads, spreadsheets, and manual follow-ups. **Anukram** provides a unified, auditable, and automated workflow orchestrator designed specifically for modern organizations.

* ⏱️ **Zero Bottlenecks:** Auto-routes submissions directly to the authorized department head or hierarchical manager.
* 🛡️ **Complete Audit Trail:** Every state change, rejection reason, approval timestamp, and step transition is cryptographically logged.
* 📄 **Digital-to-Physical Bridge:** Generates tamper-proof PDF permission passes with embedded dynamic QR verification codes for physical gate security.
* 🏢 **True Multi-Tenancy:** Complete data isolation per organization with scoped tenant querysets and role hierarchies.

---

## 🚀 Key Features

### 1. 🔄 Deterministic Workflow Engine
- **Configurable Multi-Tier Approval Chains:** Define sequential, parallel, or hierarchical approval steps per request type.
- **Dynamic State Machine:** Handles `DRAFT`, `SUBMITTED`, `IN_PROGRESS`, `APPROVED`, `REJECTED`, and `CANCELLED` transitions.
- **Automated Routing:** Submissions automatically find their target approvers based on employee hierarchy and organizational role definitions.

### 2. 📝 Dynamic Forms & Schema Engine
- **Custom Request Type Builder:** Admins can construct custom forms (e.g. *Laptop Request, Travel Requisition, Budget Allocation, Gate Pass*) with custom fields (Text, Number, Date, File Attachments, Dropdowns).
- **Field Validation & Schema Serialization:** Built-in JSON field mapping ensuring data consistency across all submissions.

### 3. 🏢 Multi-Tenant SaaS Architecture
- **Tenant Isolation:** Automatic tenant filtering on database queries via custom `TenantManager` and tenant resolution middleware.
- **Organization Onboarding:** Self-serve organization creation with automatic administrator provisioning and role initialization.

### 4. 👥 Enterprise RBAC (Role-Based Access Control)
- **Role Hierarchy:** System identities, Organization Admins, HR Heads, Unit Heads, IT Heads, Managers, and Employees.
- **Permission Matrix:** Granular view, create, edit, approve, and revoke capabilities scoped to department and hierarchy levels.

### 5. 🔒 Tamper-Proof QR & PDF Generation
- **ReportLab PDF Engine:** Automated generation of official approval certificates with enterprise styling.
- **Live QR Verification:** Security guards or external auditors can scan document QR codes to verify permission validity in real-time against the live system (`VALID`, `EXPIRED`, or `REVOKED`).

### 6. 🎨 Modern Design System
- **Responsive Web Design:** Built with modern CSS variables, fluid glassmorphism, responsive sidebar app shell, and dark/light theme toggle.
- **Live Activity Queue:** Real-time dashboard KPI cards and organization activity tracking with sub-second response times.

---

## 🏗️ System Architecture

```mermaid
graph TD
    User([Employee / Manager]) -->|HTTP / HTTPS| Topbar[Anukram Web Shell]
    Topbar --> Auth[Authentication & RBAC Middleware]
    Auth --> Tenant[Tenant Isolation Layer]
    
    subgraph Core Engine
        Tenant --> Workflow[Workflow State Machine]
        Tenant --> Forms[Dynamic Forms Engine]
        Tenant --> Approvals[Approval Inbox & History]
    end

    Workflow --> DB[(PostgreSQL Database)]
    Forms --> DB
    Approvals --> DB

    Workflow --> PDF[ReportLab PDF Engine]
    PDF --> QR[QR Code Verification Module]
    QR --> SecurityGuard([Security / Physical Verifier])
```

---

## 💻 Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend Framework** | Django 6.0 (Python 3.12+) |
| **Database** | PostgreSQL 16 / SQLite (Local fallback) |
| **Asset Engine** | ReportLab (PDF generation), Qrcode |
| **Static & Media** | WhiteNoise (Production static file compression) |
| **WSGI Server** | Gunicorn |
| **Frontend UI** | HTML5, Modern CSS Design Tokens, Bootstrap Icons, Vanilla JS |
| **Authentication** | Django Auth, Session Security, OAuth 2.0 (Google SSO ready) |
| **Deployment Target** | Koyeb / Docker / PaaS |

---

## ⚡ Quick Start

### Prerequisites
* Python 3.12+
* PostgreSQL 15+ (or default SQLite)
* Git

### 1. Clone & Setup Virtual Environment
```bash
git clone https://github.com/rajdeep-r24/Enterprise-Workflow-Management-System.git
cd Enterprise-Workflow-Management-System

# Create virtual environment
python -m venv .venv

# Activate on Windows:
.venv\Scripts\activate
# Activate on Linux/macOS:
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the root directory (or copy from `.env.example`):
```env
DEBUG=True
SECRET_KEY=your-secure-django-secret-key
DATABASE_URL=postgres://user:password@localhost:5432/anukram_db
ALLOWED_HOSTS=127.0.0.1,localhost
DEFAULT_FROM_EMAIL=noreply@anukram.local
```

### 4. Database Migrations & Superuser
```bash
python manage.py migrate
python manage.py createsuperuser
```

### 5. Seed Demonstration Data
```bash
python manage.py loaddata initial_data.json  # If fixture present
# Or run initial organization setup wizard via the UI
```

### 6. Run Local Development Server
```bash
python manage.py runserver
```
Visit `http://127.0.0.1:8000/` in your browser.

---

## 🚢 Deployment Guide

### Deploying to Koyeb / Render / PaaS

1. **Procfile** is included in the root directory:
   ```procfile
   web: gunicorn config.wsgi:application
   ```

2. **Environment Configuration for Production:**
   Set the following environment variables in your PaaS dashboard:
   - `DEBUG=False`
   - `PRODUCTION=True`
   - `SECRET_KEY=<your-production-secret-key>`
   - `DATABASE_URL=<your-managed-postgres-connection-string>`
   - `ALLOWED_HOSTS=.koyeb.app,yourcustomdomain.com`

3. **Build & Run Command:**
   - **Build command:** `pip install -r requirements.txt && python manage.py collectstatic --no-input`
   - **Run command:** `python manage.py migrate && gunicorn config.wsgi:application`

---

## 🧪 Testing

Execute the automated test suite covering RBAC permissions, multi-tenancy isolation, and workflow state transitions:
```bash
python manage.py test
```

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.

---

<div align="center">

Built with ❤️ by **Rajdeep Rathod** • Anukram — Enterprise Workflow Management System

</div>
