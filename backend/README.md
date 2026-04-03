# 🏥 Sangi Hospital Management System - Backend API

A robust, Django-based REST API built for the Sangi Hospital In-Patient Department (IPD) Portal. This backend handles the complete patient lifecycle, from smart registration and admission tracking to dynamic billing and master tariff management.

## 🚀 Key Features

* **Smart Patient Lifecycle Management:** Automated creation of Admission sessions, Medical History, and Billing placeholders upon patient registration using atomic database transactions.
* **Duplicate Protection:** Strict backend validation prevents the registration of duplicate patients by cross-checking Phone Numbers and National IDs.
* **Action-Based APIs:** Dedicated "clinical doors" (custom ViewSet actions) for updating medical records, adding services, and discharging patients without sending massive JSON payloads.
* **Master Tariff System:** A dynamic `ServiceMaster` database that automatically serves up-to-date pricing and codes for 50+ hospital services (ICU, Radiology, Room Charges, etc.).
* **Multi-Session Support:** Allows returning patients to start new admission sessions while retaining their original UHID and historical records.

## 🛠️ Tech Stack
* **Framework:** Django 5.x / Django REST Framework (DRF)
* **Database:** PostgreSQL (Containerized via Docker)
* **Scripting/Data:** Python, `openpyxl` (for Excel data ingestion)
* **Middleware:** `django-cors-headers` (Configured for separate React frontend)

---

## ⚙️ Local Setup & Installation

Follow these steps to run the backend locally on your machine.

### 1. Prerequisites
* Python 3.10+
* Docker Desktop (for the PostgreSQL database)
* Git

### 2. Database Setup (Docker)
We use a custom port (`5433`) to avoid conflicts with any local Windows database installations.
```bash
docker run --name postgres-sangi -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=admin123 -e POSTGRES_DB=sangi_hospital -p 5433:5432 -d postgres

Install Dependencies & Run

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
pip install openpyxl  # Required for Master Tariff Excel import

# Run database migrations
python manage.py makemigrations
python manage.py migrate

# Import Master Data (Prices & Codes) from Excel
python import_data.py

# Start the server
python manage.py runserver

🗂️ Project Structure
backend/
├── data/
│   └── SANGIESIC.xlsx       # Master Excel file containing prices and codes
├── patients/   
│   ├── models.py            # Database schemas (Patient, Admission, ServiceMaster, etc.)
│   ├── serializers.py       # JSON serialization and Validation logic
│   ├── views.py             # ViewSets and Custom Action routes
│   └── urls.py              # API endpoint routing
├── sangi_hospital/
│   ├── settings.py          # Django config (CORS, DB, Installed Apps)
│   └── urls.py              # Main URL router
├── import_data.py           # Custom script to ingest Excel into PostgreSQL
├── manage.py
└── requirements.txt
