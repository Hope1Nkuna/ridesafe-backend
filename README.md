# RideSafe ZA — Backend API

Community-powered driver safety for South African riders.
Built with **Python + FastAPI + PostgreSQL**.

---

## Project structure

```
ridesafe/
├── main.py          ← App entry point, starts the server
├── routes.py        ← All API endpoints
├── models.py        ← Database table definitions
├── schemas.py       ← Request / response data shapes
├── auth.py          ← JWT login, password hashing
├── utils.py         ← Score calculation, search limits
├── database.py      ← DB connection + session
├── requirements.txt ← Python dependencies
└── .env.example     ← Copy this to .env and fill in your values
```

---

## Quick start (local)

### 1. Install PostgreSQL
Download from https://postgresql.org and create a database:
```sql
CREATE DATABASE ridesafe;
CREATE USER ridesafe_user WITH PASSWORD 'yourpassword';
GRANT ALL PRIVILEGES ON DATABASE ridesafe TO ridesafe_user;
```

### 2. Clone and install
```bash
git clone <your-repo>
cd ridesafe
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Set up environment variables
```bash
cp .env.example .env
# Edit .env with your real values:
# DATABASE_URL=postgresql://ridesafe_user:yourpassword@localhost:5432/ridesafe
# SECRET_KEY=a-long-random-string-at-least-32-chars
```

### 4. Run the server
```bash
uvicorn main:app --reload
```
Open http://localhost:8000/docs to see the interactive API docs.

---

## API endpoints

### Auth
| Method | Endpoint         | Description              |
|--------|-----------------|--------------------------|
| POST   | /auth/register  | Create a new rider account |
| POST   | /auth/login     | Login, get a JWT token   |

### Search
| Method | Endpoint            | Description                          |
|--------|---------------------|--------------------------------------|
| GET    | /search/{plate}     | Search a number plate (auth required) |

### Reports
| Method | Endpoint       | Description                       |
|--------|----------------|-----------------------------------|
| POST   | /reports       | Submit a safety report            |
| GET    | /reports/my    | View your own submitted reports   |

### Subscriptions
| Method | Endpoint    | Description                      |
|--------|-------------|----------------------------------|
| POST   | /subscribe  | Start Rider Pro 7-day free trial |
| DELETE | /subscribe  | Cancel subscription              |

### Admin (requires is_admin=1 in DB)
| Method | Endpoint                      | Description                    |
|--------|-------------------------------|--------------------------------|
| GET    | /admin/reports/pending        | List all pending reports       |
| PATCH  | /admin/reports/{id}           | Approve or reject a report     |

---

## Making a user an admin
Connect to your database and run:
```sql
UPDATE users SET is_admin = 1 WHERE email = 'you@example.com';
```

---

## Deploying to production

### Recommended: Railway.app (easiest for beginners)
1. Go to https://railway.app and create a free account
2. Click "New Project" → "Deploy from GitHub repo"
3. Add a PostgreSQL plugin — Railway gives you a DATABASE_URL automatically
4. Add your environment variables in the Railway dashboard
5. Railway detects Python and deploys automatically

### Start command for production
```
uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Other options
- **Render.com** — also free tier, similar to Railway
- **Heroku** — paid but very reliable
- **DigitalOcean App Platform** — R150/month, great for SA-based hosting

---

## Connecting your app to the API

In your frontend (React Native, Flutter, or web), replace the hardcoded
`db` object with real API calls:

```javascript
// Search a plate
const res = await fetch('https://your-api.railway.app/search/CA123456', {
  headers: { 'Authorization': `Bearer ${userToken}` }
});
const data = await res.json();

// Submit a report
await fetch('https://your-api.railway.app/reports', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${userToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    plate_number: 'GP456789',
    star_rating: 1,
    incident_types: ['theft', 'assault'],
    description: 'Driver became threatening...',
    incident_date: 'Today around 3pm'
  })
});
```
