# Library Service API

Django REST Framework implementation of the eight selected Flex tasks from
DRF Library Practice: book CRUD, book permissions, email users with JWT,
borrowing list/detail, borrowing creation, borrowing filters, book returns,
and Telegram notifications. See `docs/tasks.md` for scope and dependencies.

No separate frontend is needed: use the browsable API, Swagger or an HTTP
client. The selected Flex scope does not include Stripe, payments, fines or
daily overdue reports. This is not the full-time implementation of every task.

## Features

- Public, paginated book list and details; staff-only create/update/delete.
- HARD/SOFT covers, nonnegative inventory and positive decimal daily fees.
- Email-only registration, hashed/validated passwords, JWT login and refresh.
- Private profile reading and updating; clients cannot grant staff privileges.
- Detailed borrowing history with date constraints and protected book history.
- Atomic borrowing creation: one SQL stock check/decrement and a borrowing.
- Customers see only their own borrowings; staff can filter any customer's.
- Atomic returns: today's date is recorded and one copy restored exactly once.
- Persistent notification outbox, asynchronous Celery delivery and retries.
- SQLite for local use; PostgreSQL, Redis, worker and beat in Docker Compose.
- OpenAPI/Swagger/ReDoc, admin, branch coverage and GitHub Actions checks.

## Quick start with Docker

Requirements: Docker Desktop with Compose. Clone the repository's main branch:

```sh
git clone https://github.com/makar111111/library-service.git
cd library-service
```

PowerShell:

```powershell
Copy-Item .env.sample .env
```

Edit `.env`: replace `DJANGO_SECRET_KEY` and `POSTGRES_PASSWORD` with random
local values. Keep this file private. Leave `POSTGRES_HOST` empty in the file;
Compose overrides it with `db`, while local Python uses SQLite.

```sh
docker compose up --build -d --wait
docker compose exec app python manage.py createsuperuser
```

Migrations run automatically before Gunicorn starts. The API listens on
`127.0.0.1:8018`; set `APP_PORT` in `.env` if that port is occupied.

- Browsable API: <http://127.0.0.1:8018/api/>
- Books: <http://127.0.0.1:8018/api/books/>
- Registration: <http://127.0.0.1:8018/api/users/>
- Swagger: <http://127.0.0.1:8018/api/docs/>
- ReDoc: <http://127.0.0.1:8018/api/redoc/>
- Schema: <http://127.0.0.1:8018/api/schema/>
- Admin: <http://127.0.0.1:8018/admin/>

Use **Log in** in the browsable API for Django session authentication; forms
include CSRF protection. Gunicorn serves collected CSS/JS through WhiteNoise.
`docker compose down` stops services and preserves database/Redis volumes.

## Run with local Python

Python 3.10+ and uv (or pip) are sufficient for API use. PowerShell:

```powershell
uv venv --python 3.10 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.lock
Copy-Item .env.sample .env
# Edit DJANGO_SECRET_KEY in .env. Keep POSTGRES_HOST empty for SQLite.
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver 8018
```

Alternatively, create a venv with `python -m venv .venv` and use
`.venv\Scripts\python.exe -m pip install -r requirements.lock`. On Linux/macOS
use `.venv/bin/python` and `cp .env.sample .env`. The locked dependencies are
used by Docker and CI so their versions match local verification.

## Authentication

The assignment requests a custom JWT header. Send this exact header:

```http
Authorize: Bearer <access>
```

Use Swagger's **Authorize** button and enter `Bearer <access>` including the
prefix. Token endpoints accept email/password and normalize email case.
Access tokens last 30 minutes and refresh tokens last one day. Session login
is also available for browsers at `/api-auth/login/`.

Registration example:

```http
POST /api/users/
Content-Type: application/json

{
  "email": "reader@example.com",
  "password": "Choose-a-strong-local-password-485!",
  "first_name": "Alice",
  "last_name": "Reader"
}
```

Obtain tokens by posting `email` and `password` to `/api/users/token/`.
Refresh by posting `{"refresh": "<refresh>"}` to `/api/users/token/refresh/`.
Passwords are never returned. `id` and `is_staff` cannot be changed by clients.

## Endpoints

All resource paths start with `/api/` and require a trailing slash.

| Method | Path | Access and behavior |
| --- | --- | --- |
| GET | `users/` | Public registration instructions and browsable form |
| POST | `users/` | Public registration |
| POST | `users/token/` | Email/password to access + refresh tokens |
| POST | `users/token/refresh/` | Refresh token to a new access token |
| GET, PUT, PATCH | `users/me/` | Own private profile |
| GET | `books/` | Public paginated list |
| POST | `books/` | Staff only |
| GET | `books/{id}/` | Public details |
| PUT, PATCH, DELETE | `books/{id}/` | Staff only; borrowing history prevents deletion |
| GET | `borrowings/` | Own borrowings; staff can see everyone's |
| POST | `borrowings/` | Authenticated; borrow one available book |
| GET | `borrowings/{id}/` | Owner or staff; includes detailed book information |
| POST | `borrowings/{id}/return/` | Owner or staff; return once and restore one copy |

Book fields: `title`, `author`, `cover` (`HARD` or `SOFT`), `inventory` (zero
or more), `daily_fee` (positive USD decimal, e.g. `"1.50"`). Book authors are
strings as specified by the assignment. Staff can set available inventory.

### Borrow a book

```http
POST /api/borrowings/
Authorize: Bearer <access>
Content-Type: application/json

{
  "book": 1,
  "expected_return_date": "2030-12-31"
}
```

Use an actual date today or later. Dates use the `Europe/Kyiv` timezone.
The server assigns `user`, `borrow_date` and `actual_return_date`. Successful
creation returns 201 with nested book details, user ID, dates and `is_active`.
Insufficient stock, past dates and invalid book IDs return 400 without
creating a borrowing or reducing inventory.

`POST /api/borrowings/{id}/return/` has no request body. It returns 200 with
the updated borrowing. A second return gets 400. Another customer's record
gets 404. Borrowings cannot be arbitrarily edited or deleted. Book inventory
and borrowing changes commit together; failed writes roll back both.

### Filters and pagination

- `?is_active=true` or `?is_active=1`: books not yet returned.
- `?is_active=false` or `?is_active=0`: returned books.
- Without `is_active`, include both states. Invalid values return 400.
- Staff can use `?user_id=3` and combine it with `is_active`.
- For customers, `user_id` is ignored; ownership always limits their results.
- Lists have 20 results per page. Use `?page=2` or the response's `next` URL.
- Borrowings are newest first; books are ordered by ID.

List responses have `count`, `next`, `previous` and `results` fields.

## Telegram notifications

Create a bot using Telegram's BotFather, add it to the administrators' chat,
and configure its credentials **locally** in `.env`:

```dotenv
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

Set both values, then recreate app, worker and beat:

```sh
docker compose up -d --force-recreate app worker beat
```

Every successful borrowing creates an outbox row inside the same transaction.
Only after commit is its Celery task queued. The worker posts the borrowing
ID, book title/author, reader email, borrow date and expected return date to
the configured administrators' chat. Only configure a chat allowed to receive
these details. Network calls have a ten-second timeout, sanitized errors and
exponential retries. Beat requeues up to 100 pending notifications per minute,
including records retained during an outage. Sending a previously completed
notification is skipped. Delivery is at least once: a timeout after Telegram
accepted a message can lead to a duplicate on retry.

When either credential is absent, sending is disabled and rows remain pending.
They are delivered after configuring the credentials and running worker/beat.
Automated tests mock Telegram; they never send actual messages. A live Telegram
delivery must be verified with your bot and chat after configuration.

For local Python plus an existing Redis server, use two extra terminals:

```sh
celery -A config worker --loglevel=info
celery -A config beat --loglevel=info
```

Celery workers should run in the Linux Docker service on Windows.

## Verification

The Docker suite uses PostgreSQL and exercises five simultaneous requests for
the last copy and for returning the same book. Each permits exactly one
successful stock change. The live-server test uses real HTTP requests for
JWT, books, borrow/return, HTML pages and the OpenAPI authentication header.

```sh
docker compose exec -T app coverage run manage.py test --settings=config.test_settings --noinput
docker compose exec -T app coverage report
docker compose exec -T app flake8
docker compose exec -T app black --check .
docker compose exec -T app python manage.py check
docker compose exec -T app python manage.py makemigrations --check --dry-run
docker compose exec -T app python manage.py spectacular --validate --fail-on-warn
docker compose exec -T app python -m pip check
```

For local verification, replace `docker compose exec -T app` with
`.venv\Scripts\python.exe -m` for coverage/flake8/black, and with
`.venv\Scripts\python.exe` for manage.py commands. Use `uv pip check` for the
local uv environment. The two concurrency tests skip on SQLite; run Compose
or CI to verify them on PostgreSQL. The coverage threshold is 60%.

Test settings use a fast password hasher and an in-memory Celery transport
only for isolated tests. Normal settings retain Django's PBKDF2 password
hashing. No database, real credentials, runtime evidence or venv is committed.

## Project structure

- `users/`: email user model, registration, JWT, private profile and admin.
- `books/`: book model, CRUD and public-read/staff-write permission.
- `borrowings/`: history, serializers, filters and atomic inventory operations.
- `notifications/`: outbox, Telegram transport, Celery tasks and recovery.
- `config/`: Django, Celery, routes and isolated test settings.
- `tests/`: API, validation, permissions, rollback, network and concurrency tests.
- `docs/tasks.md`: eight selected tasks and branch/PR dependency order.

## Reference documentation

- [Django transactions](https://docs.djangoproject.com/en/5.2/topics/db/transactions/)
- [Simple JWT custom authentication header](https://django-rest-framework-simplejwt.readthedocs.io/en/stable/settings.html#auth-header-name)
- [Celery and Django](https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html)
- [Telegram sendMessage](https://core.telegram.org/bots/api#sendmessage)
