<h1 align="center">Fact Check</h1>
<p align="center">A simple, not-so-crappy-looking Browser Extention to inform you about crappy Websites</p>


---

<p align="center">
  <img 
    alt="Logo Banner" 
    src="https://github.com/MaxKitsune/fact.check/blob/main/src/authentication-page/static/images/fact.check.icon.png?raw=true" 
    width="200">  
</p>
    
---

A frontend and Flask-based backend that lets a community **vote on the credibility of any HTTPS URL**.  
It powers a browser extension (manifest included) and provides a simple web interface for manual testing.

> **Project status:** ‑ Experimental / under active development. Expect breaking changes.

## Features

| ✔︎ | Description |
|----|-------------|
| **User auth** | Registration & login with BCrypt‑hashed passwords  |
| **Rate‑limited voting** | 10 votes/min per IP via **Flask‑Limiter** + Redis backend  |
| **Domain + (optional) sub‑page scoring** | Up‑ & down‑votes stored in `votable_domains` tables  |
| **REST‑style JSON** | `GET /get‑votes` returns `[hostname, path, up, down]`  |
| **Session management** | Signed cookies (`SECRET_KEY`) keep users logged in |
| **Health check UI** | `/` renders **index.html** and prints DB status badge  |
| **Browser extension** | Plug‑in (manifest v2) calls the same endpoints  |

---

## Tech Stack
| Layer | Choice |
|-------|--------|
| Language | Python 3.11 |
| Web framework | Flask 3.1  |
| DB | PostgreSQL 15 |
| Cache / rate‑limit store | Redis 7 |
| Auth helpers | bcrypt, itsdangerous (token serializer) |
| Other libs | flask‑cors, flask‑limiter, python‑dotenv, tld |

---

## Prerequisites
| Tool | Why |
|------|-----|
| **Python ≥ 3.10** | Core runtime |
| **PostgreSQL** | Primary datastore |
| **Redis** | Backing store for Flask‑Limiter |
| **Docker** | Easiest way to spin up Postgres + Redis for local dev |

---

## Getting Started

```bash
# 1  Clone
git clone https://github.com/your‑user/fact.check‑api.git
cd fact.check‑api

# 2  Create virtualenv
python -m venv .venv && source .venv/bin/activate

# 3  Install deps
pip install -r requirements.txt

# 4  Copy env template
cp .env.example .env   # then fill in the vars below

# 5  Run services (Docker Compose example below) and migrate DB
docker compose up -d postgres redis
# psql ‑h localhost ‑U $DB_USER -c "CREATE DATABASE $DB_NAME;"

# 6  Launch the app
flask --app server.py run --debug
```

---

## Environment Variables

The app reads **nothing** from hard‑coded strings – everything lives in `.env`:

| Key                                               | Purpose                  |
| ------------------------------------------------- | ------------------------ |
| `SECRET_KEY`                                      | Session signing + CSRF   |
| `DB_HOST` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` | Postgres creds           |
| *(future)* `MAIL_SERVER`, `MAIL_USERNAME`, …      | For confirmation e‑mails |

Example:

```
# .env.example
SECRET_KEY="changeme‑super‑secret"

DB_HOST="localhost"
DB_NAME="factcheck"
DB_USER="factcheck_app"
DB_PASSWORD="s3cr3t"

# Optional mail settings in the future
# MAIL_SERVER="smtp.gmail.com"
# MAIL_USERNAME="noreply@factcheck.dev"
```

---

## Database & Redis Setup

The repo does **not** include migration scripts yet.
Schema references can be found in the SQL embedded in `server.py` (temporary until Alembic is wired up).

### Quick docker‑compose

```
version: "3.9"
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: factcheck
      POSTGRES_USER: factcheck_app
      POSTGRES_PASSWORD: s3cr3t
    ports: ["5432:5432"]

  redis:
    image: redis:7
    command: ["redis-server", "--appendonly", "yes"]
    ports: ["6379:6379"]
```


Bring them up with `docker compose up -d`.

---

## Running Locally

1. Ensure Postgres & Redis are reachable.
2. Activate your virtualenv.
3. `flask --app server.py run --debug`
4. Visit [http://localhost:5000](http://localhost:5000) — a green badge means DB connectivity is OK.

---

## API Reference

> All endpoints are prefixed **/** (no versioning yet) and expect `Content-Type: application/x-www-form-urlencoded` for POSTs unless noted.

| Verb   | Path               | Body / Query                  | Auth?  | Description                       |
| ------ | ------------------ | ----------------------------- | ------ | --------------------------------- |
| `GET`  | `/`                | –                             | –      | Returns status page with DB badge |
| `POST` | `/register`        | `email`, `password`           | –      | Create user                       |
| `POST` | `/login`           | `email`, `password`           | –      | Log in and start session          |
| `GET`  | `/logout`          | –                             | Cookie | Destroy session                   |
| `GET`  | `/get-votes`       | `url=https://example.com/...` | –      | Fetch current up/down votes       |
| `GET`  | `/vote/<up\|down>` | `url=…`                       | Cookie | Cast a vote (rate‑limited)        |
| `GET`  | `/limited`         | –                             | –      | Shown when rate‑limit exceeded    |

**Rate limiting**: 10 calls/min per IP on voting routes; 5 calls/min on `/downvote` (placeholder) .

---

## Frontend & Extension

| Piece                 | Where                                                  | Notes                          |
| --------------------- | ------------------------------------------------------ | ------------------------------ |
| **HTML templates**    | `templates/index.html`, `login.html`, `register.html`  | Use Bootstrap 4 + custom CSS   |
| **Browser extension** | `manifest.json` + `/content`, `/background` folders    | Calls the same Flask endpoints |

---

## Roadmap

* **Confirmation e‑mails** (tokenized links via Flask‑Mail & itsdangerous)
* **AI‑assisted trustworthiness scoring** – first prototype will use a lightweight OpenAI function call to seed trust scores, later replaced by custom model
* Account lockout after repeated failed logins
* Forgot‑password & change‑password screens
* Migrate to a production WSGI server (uWSGI / Gunicorn)

---

## Contributing

1. Fork the repo & create a feature branch.
2. Follow the *Getting Started* steps.
3. Run `pre‑commit install` (black, isort, flake8).
4. Open a PR — make sure CI is 💚.

---

## License

Distributed under the **MIT License**.

---

*Happy fact‑checking!* ✨

---

**This README was generated with assistance from an AI coding assistant.**
