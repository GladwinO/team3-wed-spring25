# ParkEasy: Local Development Guide

## Prerequisites
- Python 3.8 or higher
- PostgreSQL 12 or higher
- pip (Python package manager)
- Git

## PostgreSQL Setup Instructions

### Install PostgreSQL and psycopg2

#### On macOS/Linux
```bash
# For Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# For macOS (using Homebrew)
brew install postgresql
```

#### On Windows
1. Download and install PostgreSQL from the [official website](https://www.postgresql.org/download/windows/)
2. During installation, note the username (`postgres`) and password you set

### Start PostgreSQL Service

#### For Linux/macOS (systemd)
```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql # Start PostgreSQL on boot
```

#### For Windows
1. Open **pgAdmin** or use **Windows Services** (`services.msc`) to start PostgreSQL
2. Ensure **PostgreSQL Server** is running

### Create the Database

#### Log in to PostgreSQL
```bash
sudo -i -u postgres
psql
```

#### Create Database
```sql
CREATE DATABASE parkeasy_db;
```

#### Configure User Privileges
```sql
ALTER USER postgres WITH PASSWORD 'postgres';
GRANT ALL PRIVILEGES ON DATABASE parkeasy_db TO postgres;
```

#### Exit PostgreSQL
```sql
\q
```

## Project Setup

### 📌 1. Clone the Repository
```bash
git clone https://github.com/yourusername/parkeasy.git
cd parkeasy
```

### 📌 2. Set Up the Virtual Environment
Before running the Django app, create and activate a virtual environment.

#### For macOS/Linux
```bash
python3 -m venv venv
source venv/bin/activate
```

#### For Windows (cmd)
```bash
python -m venv venv
venv\Scripts\activate
```

### 📦 3. Install Dependencies
Ensure all required dependencies are installed.
```bash
pip install -r requirements.txt
```

If new packages were installed, update `requirements.txt`:
```bash
pip freeze > requirements.txt
```


### 🔄 4. Apply Migrations
Run the following commands to set up the database:
```bash
python manage.py makemigrations
python manage.py migrate
```

### 🔑 5. Create a Superuser (Optional)
If you need access to the Django Admin panel:
```bash
python manage.py createsuperuser
```

Follow the prompts to create an admin user.

### 🚀 6. Run the Development Server
Start the Django app:
```bash
python manage.py runserver
```

Access the app at http://127.0.0.1:8000/

## Development Workflow

### 🧪 Running Tests
Execute the test suite:
```bash
python manage.py test
```

For a specific app:
```bash
python manage.py test booking
```

### 🛠️ Adding New Dependencies
If you install any new libraries, make sure to update `requirements.txt`:
```bash
pip install <package-name>
pip freeze > requirements.txt
```

## Project Structure

### Code Organization
- **ParkEasy**: Main ParkEasy orchestration app
- **accounts**: To manage accounts
- **listing**: For parking spot owners to list and view their parking spots
- **booking**: For users to book parking spots, see the spots they booked and manage them

## Resources
- Styling: [Bootstrap](https://getbootstrap.com/)
- Django: [Django Documentation](https://www.djangoproject.com/start/)
- Django REST Framework: [DRF Documentation](https://www.django-rest-framework.org/)
