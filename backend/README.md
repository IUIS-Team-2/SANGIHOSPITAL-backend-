# Sangi Hospital Backend

Updated on: `2026-04-29`

This backend is the active API for the HMS portal. Use it with `HMS-Frontend-new/frontend`.

## Stack

- Django + Django REST Framework
- PostgreSQL
- JWT auth via `rest_framework_simplejwt`

## Local setup

### 1. Start PostgreSQL

The backend reads DB config from `.env` and is currently set to:

```env
DB_NAME=sangi_hospital
DB_USER=postgres
DB_PASSWORD=admin123
DB_HOST=127.0.0.1
DB_PORT=5433
```

If you already have the Docker container:

```bash
docker start postgres-sangi
docker exec -it postgres-sangi pg_isready -U postgres -d sangi_hospital
```

If you need to create it:

```bash
docker run --name postgres-sangi \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=admin123 \
  -e POSTGRES_DB=sangi_hospital \
  -p 5433:5432 \
  -d postgres
```

### 2. Install backend dependencies

```bash
cd /Users/ritikkumar/Desktop/IUI/HMS-Portal/SANGIHOSPITAL-backend-/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Apply schema

```bash
python manage.py migrate
```

### 4. Seed the main Super Admin

Run the seed file:

```bash
python seed_superadmin.py
```

Default seeded credentials:

- username: `superadmin`
- password: `Super@123`
- email: `gmy.healthcare@gmail.com`

Optional environment overrides:

- `SEED_SUPERADMIN_USERNAME`
- `SEED_SUPERADMIN_PASSWORD`
- `SEED_SUPERADMIN_EMAIL`
- `SEED_SUPERADMIN_FIRST_NAME`
- `SEED_SUPERADMIN_LAST_NAME`
- `SEED_SUPERADMIN_EMP_ID`
- `SEED_SUPERADMIN_PHONE`

### 5. Import master tariff data

```bash
python import_data.py
```

### 6. Run the API

```bash
python manage.py runserver 8000
```

If port `8000` is already occupied, run:

```bash
python manage.py runserver 8001
```

Base URL:

```text
http://127.0.0.1:8000/api
```

Frontend connection note:

- `HMS-Frontend-new` now defaults to `http://127.0.0.1:8000`
- if you move Django to another port, start the frontend with:

```bash
export REACT_APP_API_ORIGIN=http://127.0.0.1:8001
npm start
```

## Required admin creation flow

The intended hierarchy is now enforced in backend user management:

1. `seed_superadmin.py` creates the main `superadmin`
2. only `superadmin` can create:
   - `admin` (Branch Admin)
   - `office_admin` (Management / Back Office Admin for all hospitals)
3. `admin` and `office_admin` can create staff users such as:
   - `receptionist`
   - `hod`
   - `billing`
   - `opd`
   - `intimation`
   - `query`
   - `uploading`

Branch rules:

- `superadmin` is a global all-hospitals role
- `office_admin` is a global all-hospitals role and is forced to branch `ALL`
- `admin` is forced to its own branch
- staff users must belong to `LNM` or `RYM`
- patient and branch records are still hardcoded to `LNM` / `RYM`, so onboarding a new hospital still needs a hospital/branch master refactor

The seeded `superadmin` cannot be created, edited, or deleted through the normal user-management API.

## Task manager flow

Two task flows are active:

### Management / Office Admin task flow

- endpoints:
  - `GET /api/tasks/`
  - `POST /api/tasks/`
  - `PATCH /api/tasks/{id}/`
  - `DELETE /api/tasks/{id}/`
- one task now points to exactly one patient through `Task.patient`
- backend still accepts the legacy frontend alias payloads and maps them to the live `patient` field
- branch validation is enforced for Branch Admin assignments

### HOD task flow

- endpoints:
  - `GET /api/hod/employees/`
  - `GET /api/hod/tasks/`
  - `POST /api/hod/tasks/`
  - `PATCH /api/hod/tasks/{id}/`
  - `GET /api/hod/analytics/`
  - `GET/POST /api/hod/reviews/`
  - `GET /api/hod/reports/download/`
- old broken references to the removed `Task.patients` relation were fixed
- HOD task assignment now validates department role and branch

## Main business flows

- patient registration and search: `/api/patients/`
- returning patient new admission: `POST /api/patients/{uhid}/new_admission/`
- medical history: `PATCH /api/patients/{uhid}/update_medical/`
- discharge: `PATCH /api/patients/{uhid}/discharge/`
- service rows bulk save: `POST /api/patients/{uhid}/admissions/{adm_no}/services/bulk-save/`
- lab reports bulk save: `POST /api/patients/{uhid}/admissions/{adm_no}/lab-reports/bulk-save/`
- pharmacy bulk save: `POST /api/patients/{uhid}/admissions/{adm_no}/pharmacy-records/bulk-save/`
- billing: `PATCH /api/patients/{uhid}/update_billing/`
- print approval:
  - `POST /api/patients/{uhid}/request_print/`
  - `POST /api/patients/{uhid}/resolve_print/`

## Verified state

- `python manage.py check` passed
- `python seed_superadmin.py` ran successfully against the local database

## Known incomplete areas

- `doctor` and `nursing` frontend pages are still not on the same backend-backed flow
- employee HR fields such as separate designation/department schema are still simplified into role-driven user records
