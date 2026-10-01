# PitchIQ

## Backend

```bash
cd backend
py -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

Requires PostgreSQL with a `pitchiq` database (see `.env.example`).

API: http://127.0.0.1:8000

## Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173
