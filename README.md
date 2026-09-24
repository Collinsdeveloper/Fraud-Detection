# FraudShield — Real-Time Fraud & SIM-Swap Detection

FraudShield is a full-stack fraud-monitoring console for a mobile network operator.
It ingests **SIM-swap**, **airtime-transfer** and **account-activity** events in real time,
scores each one against a configurable rule set, raises alerts for analysts, and pushes
**SMS/Voice alerts to the subscriber** through Africa's Talking — all from the same request.

- **Backend:** Flask + Flask-RESTful + SQLAlchemy + PostgreSQL + JWT
- **Frontend:** React (Vite) analyst console with hash routing and no extra runtime deps
- **Alerts:** Africa's Talking SMS + Voice with per-subscriber channel preference
- **Database:** local PostgreSQL database `fraud_detection_db`

---

## 1. Objective coverage

| Requirement | Status | Where |
| --- | --- | --- |
| Flag suspicious SIM swaps | ✅ | `backend/app/services/risk_engine.py`, `simswap_controller.py` |
| Flag unusual airtime transfers | ✅ | `risk_engine.py` (amount, new recipient, velocity, flagged line) |
| Flag account takeovers | ✅ | `risk_engine.py` (new device, IP/location change, password reset, OTP abuse) |
| Real-time monitoring tools | ✅ | Event ingestion endpoints + live dashboard & monitor pages |
| Instant SMS alerts to subscribers | ✅ | `alerting.py` → `notification_service.py` → Africa's Talking SMS |
| Instant Voice alerts to subscribers | ✅ | Same pipeline, `channel=voice` / `both` |
| Configurable detection rules | ✅ | `fraud_rules` table + `PUT /api/v1/rules/<id>` |
| Analyst alert workflow | ✅ | Alert acknowledgement / resolution + notification delivery log |

### Risk levels (0–100 score)

```text
safe        0–29    → stored, no alert
suspicious  30–59   → MEDIUM alert
flagged     60+     → HIGH alert (CRITICAL at 85+)
```

The score is the sum of the weights of every triggered rule (weights are editable per rule
in the `fraud_rules` table). Each event stores its `risk_score`, `risk_level` and the
human-readable `reasons` that fired.

## 2. How it works

```text
                    ┌──────────────────────────────────────────────────────────┐
SIM swap  ─────────▶│                                                          │
Airtime   ─────────▶│  POST /api/v1/sim-swaps | /airtime/transfers |           │
Account   ─────────▶│       /account/events         (JWT-protected)            │
                    └───────────────┬──────────────────────────────────────────┘
                                    │  payload
                                    ▼
                    ┌──────────────────────────────┐
                    │  risk_engine.score_*()       │  loads active fraud_rules
                    │  • rule evaluation           │  from PostgreSQL and sums
                    │  • score + level + reasons   │  weights of triggered rules
                    └───────────────┬──────────────┘
                                    │
              ┌─────────────────────┴─────────────────────┐
              ▼                                           ▼
   event saved (safe → stop)              alert created (suspicious/flagged)
                                                          │
                                                          ▼
                                        ┌───────────────────────────────────┐
                                        │ alerting.dispatch()               │
                                        │ subscriber.alert_channel:         │
                                        │   sms | voice | both | none       │
                                        └───────────────┬───────────────────┘
                                                        │
                                                        ▼
                                        ┌───────────────────────────────────┐
                                        │ notification_service              │
                                        │  • composes the subscriber message│
                                        │  • Africa's Talking SMS / Voice   │
                                        │  • writes NotificationLog row     │
                                        └───────────────┬───────────────────┘
                                                        │
                                                        ▼
                                analyst console: alerts + delivery receipts
```

Every step is synchronous inside the API request, so an ingested event triggers the
subscriber alert immediately and the delivery result (success/failure, provider response)
is recorded in `notification_logs`.

## 3. How alerts are sent

There are two paths: **automatic** (the product) and **manual test** (for verification).

### 3.1 Automatic alerts (production path)

1. An event is posted to an ingestion endpoint.
2. The risk engine scores it. If the score is **30+**, an `Alert` row is created.
3. The severity gate (`DEFAULT_NOTIFY_LEVEL`, default `HIGH`) decides whether the
   subscriber is contacted: only alerts at or above that level are pushed. With the
   default, `flagged` alerts (HIGH/CRITICAL) notify the subscriber, while `suspicious`
   (MEDIUM) alerts stay in the analyst queue. Set `DEFAULT_NOTIFY_LEVEL=MEDIUM` to also
   notify on suspicious events.
4. `alerting.dispatch()` checks the subscriber's `alert_channel`:
   - `sms` → SMS only
   - `voice` → Voice call only
   - `both` → SMS, then Voice
   - `none` → alert is stored for analysts but no subscriber message is sent
5. Africa's Talking is called, and the outcome is written to `notification_logs`
   (visible on the **Notifications** page of the console).

A subscriber must exist in the `subscribers` table for a message to go out; unknown
MSISDNs are still scored, alerted on and shown to analysts, but there is no one to notify
(`channel_sent` is recorded as `NONE`).

**Set a subscriber's channel** (e.g. to receive a Voice call):

```bash
curl -sS -X PUT http://127.0.0.1:5000/api/v1/subscribers/1 \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"alert_channel":"both"}'
```

Channels: `sms`, `voice`, `both`, `none`.

### 3.2 Manual test alerts (verification path)

Send a one-off SMS or Voice call to any number without creating an event:

```bash
# Get a token
TOKEN=$(curl -sS -X POST http://127.0.0.1:5000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@fraudshield.io","password":"Admin@123"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["token"])')

# SMS
curl -sS -X POST http://127.0.0.1:5000/api/v1/notifications/test \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"msisdn":"+254712345678","channel":"sms"}'

# Voice
curl -sS -X POST http://127.0.0.1:5000/api/v1/notifications/test \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"msisdn":"+254712345678","channel":"voice"}'
```

Response shape:

```json
{
  "message": "Test SMS dispatched to 254712345678",
  "success": true,
  "response": { "...provider payload...": "..." },
  "error": null,
  "simulated": false
}
```

The same test is available in the UI on the **Notifications** page ("Send test alert").

### 3.3 Where delivery results are visible

- **Console → Notifications page:** every SMS/Voice attempt with channel, provider,
  success flag and timestamp.
- **API:** `GET /api/v1/notifications/logs?channel=SMS&success=true`
- **Database:** `notification_logs` table.

---

## 4. Project structure

```text
network-solutions/
├── backend/
│   ├── app/
│   │   ├── controllers/        # REST resources (auth, subscribers, events, alerts, rules,
│   │   │                       #   dashboard, simulation, notifications)
│   │   ├── models/models.py    # SQLAlchemy models
│   │   ├── schemas/schemas.py  # (de)serialisation schemas
│   │   ├── services/
│   │   │   ├── risk_engine.py           # scoring + rule evaluation
│   │   │   ├── alerting.py              # alert creation + channel dispatch
│   │   │   ├── notification_service.py  # message composition + logging
│   │   │   └── africastalking_client.py # SMS/Voice provider wrapper
│   │   ├── utils/              # auth (JWT), helpers (pagination, MSISDN normalisation)
│   │   └── config.py           # env-driven configuration
│   ├── seed.py                 # idempotent demo seed (users, rules, subscribers, events)
│   ├── requirements.txt
│   ├── .env.example
│   └── run.py                  # app entrypoint (port 5000)
└── frontend/
    ├── src/
    │   ├── api.js              # fetch wrapper + endpoint helpers
    │   ├── App.jsx             # hash router + auth gate
    │   ├── components/         # Layout, DataTable/hooks, badges, toasts, UI primitives
    │   └── pages/              # Dashboard, Monitor, Alerts, Subscribers, Rules,
    │                           #   Simulator, Notifications
    ├── vite.config.js          # dev server on 5173, proxies /api → localhost:5000
    └── package.json
```

---

## 5. Quick start

### 5.1 Prerequisites

- Python 3.10+ and a virtualenv at `backend/venv`
- PostgreSQL running locally with database `fraud_detection_db`
- Node 18+ for the frontend
- Africa's Talking sandbox account (optional for local demo; SMS works, sandbox Voice may not)

### 5.2 Backend

```bash
cd backend

# 1. Configure environment
cp .env.example .env
#    then edit .env and set at least:
#      DATABASE_URL=postgresql+psycopg2://<user>@/fraud_detection_db
#      AT_USERNAME=sandbox
#      AT_API_KEY=<your africa's talking sandbox key>

# 2. Install dependencies (first time only)
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# 3. Create tables + demo data (idempotent)
./venv/bin/python seed.py

# 4. Run the API
./venv/bin/python run.py        # http://localhost:5000
```

Health check:

```bash
curl -sS http://localhost:5000/health
# {"service": "fraud-shield", "status": "ok"}
```

### 5.3 Frontend

```bash
cd frontend
npm install          # first time only
npm run dev          # http://localhost:5173
```

The Vite dev server proxies `/api/*` to `http://localhost:5000`, so no CORS setup is
needed in development.

### 5.4 Sign in

| Role | Email | Password |
| --- | --- | --- |
| Admin | `admin@fraudshield.io` | `Admin@123` |
| Analyst | `analyst@fraudshield.io` | `Analyst@123` |

The same credentials are printed by `seed.py`.

---

## 6. API reference

Base URL: `http://localhost:5000/api/v1` — every endpoint except `/auth/login` requires
`Authorization: Bearer <token>`.

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/auth/login` | Get a JWT |
| GET | `/auth/me` | Current operator |
| POST | `/auth/register` | Create operator (admin only) |
| GET | `/subscribers` | List/search subscribers |
| POST | `/subscribers` | Create subscriber (sets `alert_channel`) |
| GET/PUT/DELETE | `/subscribers/<id>` | Read / update / delete subscriber |
| GET/POST | `/sim-swaps` | List / ingest SIM-swap events |
| GET | `/sim-swaps/<id>` | Single SIM-swap event |
| GET/POST | `/airtime/transfers` | List / ingest airtime transfers |
| GET/POST | `/account/events` | List / ingest account events |
| GET | `/alerts` | List alerts (`?status=&severity=&alert_type=&msisdn=`) |
| PUT | `/alerts/<id>/status` | `{"status":"acknowledged"}` or `resolved` |
| GET | `/dashboard/summary` | Console KPIs + 7-day series |
| GET | `/rules` | List fraud rules |
| PUT | `/rules/<id>` | Tune weight / config / `is_active` |
| POST | `/notifications/test` | Send test SMS or Voice |
| GET | `/notifications/logs` | Delivery receipts |
| POST | `/simulate/sim-swap` | Demo SIM-swap event (`scenario`) |
| POST | `/simulate/airtime` | Demo airtime transfer (`scenario`) |
| POST | `/simulate/account` | Demo account event (`scenario`) |
| GET/POST | `/ussd` | Africa's Talking USSD callback (public — no JWT, see §14) |

> `POST /auth/register`, `GET /operators` and all `/rules` endpoints require an **admin**
> token; analysts receive `403` there and can use every other endpoint.


### 6.1 Ingest a SIM-swap event

```bash
curl -sS -X POST http://127.0.0.1:5000/api/v1/sim-swaps \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{
    "msisdn": "254710123456",
    "device_model": "Samsung Galaxy S24",
    "channel": "AGENT",
    "agent_name": "Peter O.",
    "old_imsi": "639021234567890",
    "new_imsi": "639031234567897",
    "old_iccid": "8963911234567890123",
    "new_iccid": "8963911234567890999",
    "swap_datetime": "2026-09-24T10:30:00"
  }'
```

`channel` values: `WEB`, `RETAILER`, `APP`, `AGENT`, `SIM_TOOLKIT`, `WHATSAPP`.
High-risk channels plus a repeat swap on the same line are what typically push the score
into `suspicious`/`flagged`, which creates the alert and notifies the subscriber.

### 6.2 Ingest an airtime transfer

```bash
curl -sS -X POST http://127.0.0.1:5000/api/v1/airtime/transfers \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{
    "sender_msisdn": "254710123456",
    "recipient_msisdn": "254712345679",
    "amount": 2500,
    "is_new_recipient": true,
    "method": "DIAL_CODE",
    "transfer_datetime": "2026-09-24T14:05:00"
  }'
```

`method` values: `USSD`, `APP`, `DIAL_CODE`, `VENDOR`. Rules that can fire:
large amount (≥ KES 500 by default), new recipient, transfer velocity, off-hours.

### 6.3 Ingest an account event

```bash
curl -sS -X POST http://127.0.0.1:5000/api/v1/account/events \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{
    "msisdn": "254710123456",
    "event_type": "PASSWORD_RESET",
    "ip_address": "41.90.64.12",
    "device_hash": "dev-9f21ab77",
    "location": "Mombasa",
    "event_datetime": "2026-09-24T02:15:00",
    "details": {"reset_channel": "USSD"}
  }'
```

`event_type` values: `LOGIN`, `NEW_DEVICE`, `PASSWORD_RESET`, `PROFILE_CHANGE`,
`OTP_REQUEST`, `BENEFICIARY_CHANGE`, `PIN_CHANGE`. New device, IP/location change,
password reset and OTP abuse patterns drive the account-takeover score.

### 6.4 Work the alert queue

```bash
# Queue of open, high-severity alerts
curl -sS -H "Authorization: Bearer $TOKEN" \
  'http://127.0.0.1:5000/api/v1/alerts?status=open&severity=HIGH'

# Acknowledge an alert
curl -sS -X PUT http://127.0.0.1:5000/api/v1/alerts/1/status \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"status":"acknowledged"}'

# Resolve it
curl -sS -X PUT http://127.0.0.1:5000/api/v1/alerts/1/status \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"status":"resolved"}'
```

---

## 7. Simulator (fastest way to see alerts fire)

The **Simulator** page (or the API) generates realistic events for three scenarios:

| Scenario | Expected result | Notes |
| --- | --- | --- |
| `normal` | `safe`, score 0, **no alert** | uses a fresh synthetic MSISDN per request |
| `suspicious` | `suspicious`, MEDIUM alert | stable fixture line; analyst queue only at the default notify level |
| `flagged` | `flagged`, HIGH/CRITICAL alert + SMS/Voice dispatch | stable seeded high-risk line |

```bash
curl -sS -X POST http://127.0.0.1:5000/api/v1/simulate/sim-swap \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"scenario":"flagged"}'
```

Allowed `scenario` values: `normal`, `suspicious`, `flagged` (anything else → HTTP 400).
The response contains the created event, its `risk_level`, `risk_score`, `reasons`,
and the generated alert when one was raised.

> The simulator writes real rows to the database (events, alerts, notification logs), so
> counts grow with every run — that is intentional for a live demo.

---

## 8. Frontend walkthrough

| Page | What it does |
| --- | --- |
| **Dashboard** | KPIs (open alerts, flagged subscribers, SIM swaps today, delivery success), severity donut, 7-day event-volume chart, SIM-swap/airtime/ATO trend charts, latest alerts, watchlist |
| **Monitor → SIM Swaps** | Paginated event stream with risk badges; open an event for forensic detail (score, reasons, IMSI/ICCID change) |
| **Monitor → Airtime** | Transfer stream with amount, recipient and risk context |
| **Monitor → Account** | Account-event stream (device, IP, location, event type) |
| **Alerts** | Filter by status/severity/type, acknowledge and resolve alerts |
| **Subscribers** | Search, create, edit (including `alert_channel`), flag/block lines |
| **Rules** | View and tune rule weights, thresholds and active state |
| **Simulator** | One-click normal / suspicious / flagged events for all three event types |
| **Notifications** | Delivery receipts and "Send test alert" (SMS/Voice) form |

The UI is a hash-router SPA (`#/dashboard`, `#/monitor/sim-swaps`, …), stores the JWT in
`localStorage`, and auto-logs-out on a 401.

---

## 9. Configuration (`backend/.env`)

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Flask session/signing secret — change in production |
| `DATABASE_URL` | SQLAlchemy URL, e.g. `postgresql+psycopg2://user@/fraud_detection_db` |
| `AT_USERNAME` / `AT_API_KEY` | Africa's Talking credentials (`sandbox` for testing) |
| `AT_SENDER_ID` | Optional alphanumeric sender; leave blank in sandbox |
| `AT_VOICE_FROM` | Voice caller ID (sandbox default `+254711082000`) |
| `AT_SMS_URL` / `AT_VOICE_URL` | Provider endpoints (sandbox vs production) |
| `AT_SIMULATE_VOICE_ON_UNAVAILABLE` | When `true`, an unreachable sandbox Voice host is logged as a simulated delivery instead of failing hard — **set to `false` in production** |
| `JWT_EXPIRATION_HOURS` | Token lifetime (default 24) |
| `COUNTRY_CODE` | Default country code for MSISDN normalisation (254) |
| `DEFAULT_NOTIFY_LEVEL` | Minimum severity that triggers a subscriber notification (default `HIGH`) |

`backend/.env` is git-ignored — never commit real credentials. Use `.env.example` as the
template.

---

## 10. Detection rule catalog

Rules live in the `fraud_rules` table and can be tuned live (weight, thresholds,
`is_active`). Seeded defaults:

**SIM swap** — `SIM_SWAP_REPEAT` (45), `SIM_SWAP_ACCOUNT_AGE` (30), `SIM_SWAP_CHANNEL` (25),
`SIM_SWAP_ODD_HOUR` (20), `SIM_SWAP_NETWORK_CHANGE` (20), `SIM_SWAP_VIP` (20)

**Airtime** — `AIRTIME_FLAGGED_LINE` (40), `AIRTIME_VELOCITY` (35), `AIRTIME_NEW_RECIPIENT` (30),
`AIRTIME_AMOUNT` (25), `AIRTIME_ODD_HOUR` (15)

**Account takeover** — `ACCOUNT_PIN_PLUS_OTP` (55), `ACCOUNT_OTP_STORM` (40),
`ACCOUNT_BENEFICIARY_CHANGE` (35), `ACCOUNT_FLAGGED_LINE` (35), `ACCOUNT_PIN_CHANGE` (30),
`ACCOUNT_PASSWORD_RESET` (25), `ACCOUNT_NEW_DEVICE` (25), `ACCOUNT_PROFILE_CHANGE` (20),
`ACCOUNT_ODD_HOUR` (15)

Reason codes such as *"Repeat SIM swap within 30 days"* or *"Transfer from flagged line"*
are stored on the event and included in the subscriber alert message.

---

## 11. Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| `psycopg2.OperationalError` on start | PostgreSQL not running or `DATABASE_URL` wrong. Confirm with `psql -d fraud_detection_db -c '\dt'` |
| `401 Invalid email or password` | Re-run `./venv/bin/python seed.py` to recreate demo users |
| SMS not received (sandbox) | Africa's Talking sandbox only delivers to numbers you registered/verified in your sandbox dashboard; check `notification_logs` for the provider response |
| Voice call fails with host/DNS error | Known sandbox limitation. Keep `AT_SIMULATE_VOICE_ON_UNAVAILABLE=true` locally; deliveries are logged with `simulated: true`. Use production Voice endpoints for real calls |
| `success:false` in `/notifications/test` | Read the `error` field — usually a wrong `AT_API_KEY`, or a `from`/`AT_SENDER_ID` not approved for the sandbox |
| Simulator `flagged` returns no subscriber message | The fixture MSISDN has no `subscribers` row, or its `alert_channel` is `none`; create/update the subscriber, then re-run |
| Frontend shows "Failed to fetch" | Backend not running on port 5000, or you opened the built app without the dev proxy — use `npm run dev` and `http://localhost:5173` |
| `normal` simulator event unexpectedly alerts | Not expected after the current fixtures: normal events always use a fresh synthetic MSISDN. If it happens, check `PUT /rules` for a rule that fires on unrelated conditions |
| Need to re-seed demo data | `./venv/bin/python seed.py` is idempotent (it only fills empty tables) |

Useful checks:

```bash
# Tail the API log
tail -f /tmp/fraudshield-server.log

# Recent notification attempts
psql -d fraud_detection_db -c \
  "SELECT channel, success, msisdn, created_at FROM notification_logs ORDER BY created_at DESC LIMIT 10;"

# Alerts by severity
psql -d fraud_detection_db -c \
  "SELECT severity, status, count(*) FROM alerts GROUP BY 1,2 ORDER BY 1;"
```

---

## 12. Security notes

- `backend/.env` (with the Africa's Talking key) is **git-ignored** — keep it that way and
  rotate any key that has been shared or committed.
- Set `SECRET_KEY` to a strong random value in production.
- Disable `AT_SIMULATE_VOICE_ON_UNAVAILABLE` and point `AT_SMS_URL` / `AT_VOICE_URL` at the
  production Africa's Talking endpoints before going live.
- JWTs expire after `JWT_EXPIRATION_HOURS`; admin-only routes (`/auth/register`,
  `/operators`) are enforced server-side.
- MSISDNs are normalised to `2547XXXXXXXX` format before storage and lookup.

---

## 13. Verification performed

- Backend: all controllers compile; `/health` returns `200 {"status": "ok"}`.
- Authenticated `GET` dashboard/event/alert/notification endpoints return `200` with
  paginated payloads.
- Normal simulator runs (SIM swap, airtime, account) return `201` with
  `risk_level: safe`, `risk_score: 0` and no alert.
- Invalid simulator scenario returns `400` with a validation message.
- Flagged simulator runs create alerts and dispatch notifications; results are recorded in
  `notification_logs`.
- Frontend: `npm run lint` passes with no diagnostics and `npm run build` succeeds
  (Vite production bundle).
- USSD: `POST/GET /api/v1/ussd` honours the Africa's Talking contract — `CON` for the root
  menu, `END` for status/settings/report/invalid paths — and registers the dialling number
  as a subscriber on first contact.

---

## 14. USSD channel (callback URL for Africa's Talking)

Subscribers without smartphones can dial in to check their line, report a suspected SIM
swap and change their alert channel. The callback endpoint is:

```text
GET/POST  https://<your-public-host>/api/v1/ussd
```

The route is intentionally **public** (Africa's Talking cannot send a JWT) and only ever
returns data for the calling `phoneNumber`. Sessions are stateless: the telco posts the
full dialled path in `text` (`''` → `1` → `1*2`) and the app replies in plain text with
`CON` (keep session) or `END` (close session). No SMS/Voice call is made inside a session,
so replies stay well under the ~20 s USSD timeout.

### 14.1 Menu map

| Dialled path | Reply |
| --- | --- |
| *(root)* | `CON` main menu |
| `1` | `END` line status, open alerts, current alert channel |
| `2` → `1` | Flags the line and opens a **HIGH** `SIM_SWAP` alert for analysts |
| `2` → `2` | `END` cancelled |
| `3` → `1`/`2`/`3`/`4` | `END` alert channel set to SMS / Voice / SMS+Voice / None |
| `4` | `END` fraud help-desk instructions |
| anything else | `END` invalid option |

The first time a number dials in it is auto-registered as a subscriber (`status: active`,
`alert_channel: sms`).

### 14.2 Link the URL to your USSD channel

1. Start the backend: `cd backend && ./venv/bin/python run.py` (listens on port `5000`).
2. Expose it publicly — Africa's Talking cannot reach `localhost`:
   - `ngrok http 5000`, or
   - `cloudflared tunnel --url http://localhost:5000`
3. Take the HTTPS URL from the tunnel and append the path, e.g.
   `https://1a2b-3c4d.ngrok-free.app/api/v1/ussd`.
4. In the Africa's Talking dashboard open **USSD → your service code → Callback URL**,
   paste that address, set the method to `POST` and save. The sandbox simulator in the
   same menu calls the same URL.
5. Dial the service code (e.g. `*384*123#`) from the simulator or a handset.

Production notes: the URL must be HTTPS, the host must answer within ~20 s, and the body
must be `CON`/`END` plain text. When deploying, point the channel at
`https://<your-domain>/api/v1/ussd` and use the tunnel only for local testing.

### 14.3 Test locally without a tunnel

```bash
curl -sS -X POST http://127.0.0.1:5000/api/v1/ussd \
  -d 'sessionId=test1&serviceCode=*384*123#&phoneNumber=+254799000111&text='
# CON FraudShield ...

curl -sS -X POST http://127.0.0.1:5000/api/v1/ussd \
  -d 'sessionId=test1&serviceCode=*384*123#&phoneNumber=+254799000111&text=3*2'
# END Alert channel set to Voice call.
```






