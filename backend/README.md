# 🏥 Sangi Hospital Management System (HMS)

A robust, Full-Stack Hospital Management System designed to handle the complete In-Patient Department (IPD) lifecycle. This platform seamlessly connects front-desk registration, medical records, service charting, and a secure billing approval workflow across multiple hospital branches.

## ✨ Key Features

* **Smart Patient Lifecycle Management:** Step-by-step UI that guides staff through Registration -> Medical History -> Discharge -> Services -> Billing Summary.
* **Auto-Session & Multi-Session Support:** Automated creation of Admission sessions, Medical History, and Billing placeholders upon patient registration using atomic database transactions. Returning patients can generate new admission sessions under their existing UHID, keeping medical histories cleanly separated by visit.
* **Secure Print & Billing Approvals:** Branch staff can generate draft bills, but printing official invoices requires sending a secure digital request to a Super Admin for approval. The backend enforces this via status protections.
* **Dynamic Master Tariff System:** A dynamic `ServiceMaster` database automatically serves up-to-date pricing and codes for 50+ hospital services (ICU, Radiology, Room Charges, etc.). Prices are loaded directly from a central Excel sheet into PostgreSQL.
* **Duplicate Protection:** Strict backend validation prevents the registration of duplicate patients by cross-referencing Phone Numbers and National IDs.
* **Multi-Branch Support:** Built-in location tagging (e.g., Laxmi Nagar vs. Raya) to filter data and calculate branch-specific revenues on the Super Admin Dashboard.

## 🛠️ Tech Stack
* **Frontend:** React.js, Context API, React-Toastify
* **Backend:** Django 5.x, Django REST Framework (DRF)
* **Database:** PostgreSQL (Containerized via Docker)
* **Data Processing:** Python, `openpyxl` (for Excel data ingestion)
* **Middleware:** `django-cors-headers` (Configured for separate React frontend)

---

## ⚙️ Local Setup & Installation

Follow these steps to run the complete Full-Stack application locally on your machine.

### 1. Prerequisites
* Python 3.10+
* Node.js & npm
* Docker Desktop (for the PostgreSQL database)
* Git

### 2. Database Setup (Docker)
We use a custom port (`5433`) to avoid conflicts with any local Windows database installations. Run the following command:
```bash
docker run --name postgres-sangi -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=admin123 -e POSTGRES_DB=sangi_hospital -p 5433:5432 -d postgres

---

 3. Backend Setup

# Navigate to the backend directory
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
pip install openpyxl  # Required for Master Tariff Excel import
pip install xhtml2pdf

# Run database migrations
python manage.py makemigrations
python manage.py migrate

# Import Master Data (Prices & Codes) from Excel
python import_data.py

# Start the Django server
python manage.py runserver


🔒 User Roles & Workflows
Super Admin: Can view all branches, see live revenue/occupancy dashboards, and explicitly APPROVE or REJECT invoice print requests.

Branch Admin/Staff: Can register patients, update medical/discharge records, add clinical services, and request bill print approvals for their specific branch.


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


📡 Backend API Documentation
Base URL: http://127.0.0.1:8000/api/

1. Patient & Admission Management
These endpoints handle the core registration and patient lifecycle tracking.

Register New Patient

Endpoint: POST /patients/

Description: Creates a new patient record and automatically initializes their first admission (admNo: 1).

Key Fields: patientName, phone, gender, locId (maps to 'LNM' or 'RYM').

List All Patients

Endpoint: GET /patients/

Description: Retrieves all patient records, ordered by creation date.

Create New Admission

Endpoint: POST /patients/{uhid}/new_admission/

Description: Generates a subsequent admission session (e.g., Admission #2) for a returning patient.

2. Clinical Documentation
Endpoints for recording medical data and managing the discharge process.

Update Medical History

Endpoint: PATCH /patients/{uhid}/update_medical/

Description: Updates medical records (diagnosis, treating doctor, medications) for a specific admission.

Set Expected Discharge

Endpoint: PATCH /patients/{uhid}/set_expected_dod/

Description: Records the estimated discharge date, used for administrative planning dashboards.

Finalize Discharge Summary

Endpoint: PATCH /patients/{uhid}/discharge/

Description: Records final discharge details (actual DOD, condition, department).

3. Billing & Services Tariff
Handles service entry and the financial summary of each admission.

Fetch Service Master (Tariff)

Endpoint: GET /service-master/

Description: Provides the complete list of available services and their standard rates dynamically from the database.

Add/Update Service Charge

Endpoint: POST /patients/{uhid}/add_service/

Description: Records a specific service charge. This is idempotent; updating the same service name for the same admission updates the existing record.

Update Billing Summary

Endpoint: PATCH /patients/{uhid}/update_billing/

Description: Records discounts, total payments, and payment methods.

4. Administrative Approval Workflow
A secure workflow for managing official invoice printing rights.

Request Bill Print

Endpoint: POST /patients/{uhid}/request_print/

Description: Staff requests permission to print an official bill. Sets status to PENDING.

View Pending Requests

Endpoint: GET /patients/pending_prints/

Description: Used by the Super Admin Dashboard to see all patients currently waiting for bill approval.

Resolve Print Request

Endpoint: POST /patients/{uhid}/resolve_print/

Description: Admin action to APPROVE or REJECT a print request, enabling or disabling the green print feature on the frontend UI.

🛠️ Technical Notes for Frontend Integration:
ID Mapping: When registering patients, the system expects locId as laxmi or raya. The backend automatically converts these to LNM (Laxmi Nagar Mathura) and RYM (Raya Mathura).

Data Integrity: The update_billing endpoint is protected. It explicitly ignores incoming updates to the printStatus field so staff saves cannot overwrite an existing APPROVED or PENDING admin decision.