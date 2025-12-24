# Lotus CRM – Web Application

Lotus CRM is a bilingual (Arabic/English) web-based customer and complaints management system for Lotus Pharmacies. It replaces the legacy Tkinter desktop apps with a modern Flask web stack backed by PostgreSQL.

## Features

- **Dual language** – Arabic (RTL) and English (LTR) via top navigation
- **Branding** – Configurable brand name and primary color in Admin settings
- **Complaints** – Create, view, update status, branch/date filters, email notifications
- **Dashboards** – Complaint status charts and branch comparison charts
- **Knowledge base** – Product search and alternatives
- **Users & permissions** – Role flags (reports, functions, users, Excel) + per-feature visibility
- **Configurable email** – SMTP or Microsoft Graph for complaint notifications
- **Reports** – Complaints and customers with Excel export, date and branch filters
- **Daily backups** – Automated PostgreSQL dumps (Docker backup service)

## Default Login

| Username | Password |
|----------|----------|
| `admin`    | `admin`    |

Change this password immediately after first login in production.

## Local Development

### Prerequisites

- Python 3.11+
- PostgreSQL 16 (or use Docker)

### Setup

```bash
# Clone / open project
cd CRM

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env with your PostgreSQL credentials

# Initialize database
python scripts/init_db.py

# Run development server
python run.py
```

Open http://localhost:16350 (or the port set in `.env`).

## Docker Deployment (VPS)

Deploy on your VPS (`187.124.15.14`) on port **16350**:

```bash
# On VPS
git clone https://github.com/Refaat1942/Lotus-CRM.git
cd Lotus-CRM

cp .env.example .env
# Edit .env: set SECRET_KEY, POSTGRES_PASSWORD

docker compose up -d --build
```

Access: **http://187.124.15.14:16350**

### Firewall

```bash
sudo ufw allow 16350/tcp
```

### Backups

Backups are stored in `./backups/` as compressed SQL dumps. The backup container runs daily. Manual backup:

```bash
docker compose exec backup /backup_db.sh
```

## Admin Configuration

After login as `admin`, go to **Admin Panel**:

1. **Branding** – Set company name and theme color
2. **Email** – Set notification sender email and SMTP (or enable Microsoft Graph)
3. **Users** – Create users and assign permissions
4. **Features** – Enable/disable menu items per user

## Project Structure

```
app/
  models.py          # PostgreSQL models
  routes/            # Blueprints (auth, complaints, admin, reports, knowledge)
  templates/         # Jinja2 HTML templates
  static/            # CSS & JS
  services/          # Email, i18n
scripts/
  init_db.py         # Database seed + admin user
  backup_db.sh       # PostgreSQL backup script
legacy/              # Original Tkinter desktop apps (reference)
docker-compose.yml
Dockerfile
run.py
```

## Push to GitHub

```bash
git remote add origin https://github.com/Refaat1942/Lotus-CRM.git
git add .
git commit -m "Add Lotus CRM web application with PostgreSQL and Docker deployment"
git push -u origin main
```

## Legacy Desktop Apps

The original Tkinter applications (`main_menu.py`, `complaints_app.py`, etc.) remain in the repository for reference. The web app is the primary deployment target.
