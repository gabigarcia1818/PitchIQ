# PitchIQ

---

## Database
### Setup
Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
docker compose up -d
```

### Running
```bash
# start
docker compose up -d

# stop
docker compose stop

# stop and remove
docker compose down
```

### After changes
Re-run `docker compose up -d` if you edit `docker-compose.yml`.

---

## Backend
API: http://127.0.0.1:8000

### Setup
Database must already be running.

```bash
cd backend
py -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
```

Note: If using Mac instead of Windows, use:
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
```

### Running
```bash
cd backend
.venv/Scripts/activate
python manage.py runserver
```

For Mac:
```bash
cd backend
source .venv/bin/activate
python manage.py runserver
```

### After changes
| What changed | Commands |
|--------------|----------|
| `requirements.txt` | `pip install -r requirements.txt` |
| `api/models.py` (or other models) | `python manage.py makemigrations` then `python manage.py migrate` |
| Existing migration files only | `python manage.py migrate` |

---

## Statcast data (ML)

Pulls 2021-2025 regular season Statcast data with `pybaseball` into `backend/ml/data/` (gitignored). It downloads in weekly chunks and skips ones it already has, so you can stop it and rerun.

```bash
cd backend
python -m ml.collect_statcast --combine                 # all seasons
python -m ml.collect_statcast --seasons 2024 --combine  # one season
python -m ml.collect_statcast --start 2024-04-01 --end 2024-04-02 --force  # small test pull
```

Tests: `python -m pytest ml`

---

## Frontend

App: http://localhost:5173

### Setup (once)

```bash
cd frontend
npm install
```

### Running

```bash
cd frontend
npm run dev
```

### After changes
| What changed | Commands |
|--------------|----------|
| `package.json` | `npm install` |


### Login/Authentication Info
## Admin Login
To create an admin account:
```bash
cd backend
python manage.py createsuperuser
```
Then fill in info for username, email, and password.
Admin API: http://127.0.0.1:8000/admin

## Pitcher Login/Signup
Pitcher account signup and login can be done through the frontend app
