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

### Running
```bash
cd backend
.venv/Scripts/activate
python manage.py runserver
```

### After changes
| What changed | Commands |
|--------------|----------|
| `requirements.txt` | `pip install -r requirements.txt` |
| `api/models.py` (or other models) | `python manage.py makemigrations` then `python manage.py migrate` |
| Existing migration files only | `python manage.py migrate` |

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
