# SmartEdu — Setup Guide

## Prerequisites
| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.10+ | Flask backend |
| MySQL | 8.0+ | Relational database |
| n8n | latest | AI automation workflow |
| OpenAI API Key | — | GPT-4o-mini summarization |

---

## 1 — Database Setup

```bash
# Create the database and all tables
mysql -u root -p < schema.sql
```

This creates 6 tables (`Users`, `Courses`, `Enrollments`, `Lessons`,
`AI_Summaries`, `Progress_Tracking`) and inserts demo seed data.

---

## 2 — Flask Backend Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Copy env file and fill in your values
cp .env.example .env
```

Edit `.env`:
```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=smartedu
JWT_SECRET_KEY=any-long-random-string
N8N_WEBHOOK_URL=http://localhost:5678/webhook/smartedu-summary
```

```bash
# Run the server
python app.py
# → Running on http://localhost:5000
```

---

## 3 — n8n Workflow Setup

1. Install n8n: `npm install -g n8n` then run `n8n start`
2. Open `http://localhost:5678` in your browser
3. Go to **Workflows → Import** and upload `n8n_workflow.json`
4. Go to **Settings → Credentials → New → OpenAI API** and paste your key
5. Open the imported workflow and click **Activate**

The webhook URL will be: `http://localhost:5678/webhook/smartedu-summary`

---

## 4 — End-to-End Flow Test

```bash
# 1. Register a teacher
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Teacher","email":"t@test.com","password":"pass123","role":"teacher"}'

# 2. Login and grab the token
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"t@test.com","password":"pass123"}'

# 3. Create a course (replace TOKEN below)
curl -X POST http://localhost:5000/api/courses \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"CS101","description":"Intro course"}'

# 4. Post a lesson — this fires the n8n webhook automatically
curl -X POST http://localhost:5000/api/lessons \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"What is an Algorithm?","youtube_url":"https://www.youtube.com/watch?v=6hfOvs8pY1k","course_id":1}'

# 5. After ~10s, check if the AI summary arrived
curl http://localhost:5000/api/summaries/1 \
  -H "Authorization: Bearer TOKEN"
```

---

## 5 — Project File Structure

```
smartedu-backend/
├── app.py                    ← Flask entry point
├── config.py                 ← Environment config
├── extensions.py             ← db + jwt singletons
├── models.py                 ← SQLAlchemy models (6 entities)
├── schema.sql                ← MySQL DDL + seed data + sample JOINs
├── n8n_workflow.json         ← Import into n8n
├── requirements.txt
├── .env.example
├── middleware/
│   └── auth_middleware.py    ← JWT role decorators
└── routes/
    ├── auth.py               ← /api/auth/*
    ├── courses.py            ← /api/courses/*
    ├── lessons.py            ← /api/lessons/*  (triggers n8n)
    ├── summaries.py          ← /api/summaries/* (n8n callback)
    └── progress.py           ← /api/progress/*
```

---

## Course Rubric Coverage

| Requirement | Where it's met |
|---|---|
| **FSE** — Input validation | `routes/auth.py`, `routes/lessons.py` — email regex, URL regex, required field checks |
| **FSE** — MVP architecture | Blueprints, single-responsibility routes, .env config separation |
| **DBS** — 5-6 entities | `Users`, `Courses`, `Enrollments`, `Lessons`, `AI_Summaries`, `Progress_Tracking` |
| **DBS** — 8-9 tables | 6 core + `schema.sql` comment block with views ready to add |
| **DBS** — Complex JOINs | 3 sample queries in `schema.sql` — 4-table JOIN, GROUP BY aggregate, COALESCE |
| **AI** — LLM integration | n8n → OpenAI GPT-4o-mini via `n8n_workflow.json` |
| **AI** — Automation tool | n8n orchestrates transcript fetch + OpenAI call + Flask callback |
