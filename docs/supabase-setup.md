# Supabase Setup (one-time, ~10 minutes)

You need a Supabase project to hold the six tables. Free tier is enough. The backend connects to it as a normal Postgres client, so you only need the **database connection string**, not the API keys.

Dashboard labels change occasionally. If something is named slightly differently, look for the closest match.

## 1. Create the account and project

1. Go to https://supabase.com and click **Start your project**. Sign in with GitHub (easiest, since your team uses GitHub).
2. Create an **Organization** if prompted. Name it anything, pick the **Free** plan.
3. Click **New project** and fill in:
   - **Name:** `finsight-ai`
   - **Database password:** click *Generate a password*, then **copy it somewhere safe now**. You can't view it again later (only reset it).
   - **Region:** pick the one closest to where you'll deploy the backend (for Render's default, US East / N. Virginia is a good match).
4. Click **Create new project** and wait 1–2 minutes until the dashboard shows the project as ready.

## 2. Get the connection string

1. Click the **Connect** button at the top of the project dashboard.
2. Choose the **Session pooler** connection string (Type: URI). Use this one, not "Direct connection": the direct host is IPv6-only on the free tier, and many networks and hosts (including some Render regions) are IPv4-only.
3. It looks like:
   `postgresql://postgres.<project-ref>:[YOUR-PASSWORD]@aws-0-<region>.pooler.supabase.com:5432/postgres`
4. Replace `[YOUR-PASSWORD]` with the password from step 1. If the password contains special characters (`@ : / ? # %`), URL-encode them.

## 3. Put it in the backend environment

Never commit this value. The file `backend/.env` already exists (created from `backend/.env.example`) and is git-ignored.

1. In VS Code, open `backend/.env` (left sidebar → `backend` → `.env`).
2. Find the line `DATABASE_URL=` (nothing after the `=`).
3. Paste your full connection string right after the `=`, with no spaces and no quotes:

```
DATABASE_URL=postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres
```

4. Save the file (Cmd+S).

Share the string with teammates privately (not in the repo or a group chat history).

If `backend/.env` is ever missing, run this from the repo root: `cp backend/.env.example backend/.env`.

## 4. Create the tables

> **Not yet available:** `schema.sql` and the seed script are created during implementation (about minute 35–75 of the build). Stop after step 3 for now; the build agent will do steps 4 and 5 for you or tell you exactly what to click.

1. In the dashboard, open **SQL Editor** → **New query**.
2. Paste the full contents of `backend/app/db/schema.sql` (created by the implementation plan) and click **Run**.
3. Open **Table Editor** and confirm you see: `users`, `accounts`, `transactions`, `recurring_bills`, `income_sources`, `financial_snapshots`, `risk_alerts`.

The schema file also runs `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` on every table, with no policies. This blocks Supabase's public REST API from reading the data using the anon key, while the backend (which connects as the database owner) is unaffected. That is the intended MVP setup: the browser never talks to Supabase directly.

## 5. Seed the data

```
cd backend
python -m scripts.seed_database --reset
```

Then check **Table Editor** → `transactions` has rows, and `users` contains the demo customer.

## 6. Production (Render) later

Set the same `DATABASE_URL` as an environment variable in the Render dashboard (**Environment** tab). Do not copy the `.env` file into the repo or the build.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `password authentication failed` | Wrong password or un-encoded special characters. Reset it under **Project Settings → Database**. |
| `could not translate host name` / hangs | You used the Direct connection on an IPv4 network. Use the Session pooler string. |
| `relation "users" does not exist` | The schema SQL from step 4 hasn't been run on this project. |
| Seed script says tables are not empty | Re-run with `--reset` (it truncates only the app tables). |
