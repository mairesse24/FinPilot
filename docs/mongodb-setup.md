# MongoDB Atlas Setup — your steps (about 10 minutes)

You do these steps once. At the end you have one secret line in `backend/.env`. Everything else is done by the build agent.
Labels in the Atlas website change now and then. If a button is named a little differently, pick the closest one.

**Never paste your password into chat, Git, or a screenshot.**

## Checklist

- [ ] **1. Create the account.** Go to https://www.mongodb.com/cloud/atlas and click **Try Free**. Sign up with Google or email.
- [ ] **2. Create a free cluster.** Choose **M0 (Free)**. Pick any cloud provider. Pick the region closest to Render (US West/Oregon or US East/N. Virginia). Name it `finpilot`. Click **Create**. Wait 1–3 minutes.
- [ ] **3. Create a database user.** Left menu → **Database Access** → **Add New Database User**.
  - Authentication: **Password**.
  - Username: `finpilot`.
  - Click **Autogenerate Secure Password**, then **Copy**. Keep it in a safe place.
  - Role: **Read and write to any database**. Click **Add User**.
- [ ] **4. Allow connections.** Left menu → **Network Access** → **Add IP Address** → **Allow Access from Anywhere** → **Confirm**.
  - Why: Render's free servers have no fixed address. The data is fictional and the password protects it.
- [ ] **5. Copy the connection string.** Left menu → **Database** → your cluster → **Connect** → **Drivers**. Copy the line that starts with `mongodb+srv://`. It looks like this:
  ```
  mongodb+srv://finpilot:<password>@finpilot.abc12.mongodb.net/?retryWrites=true&w=majority
  ```
- [ ] **6. Put your password in.** In a scratch place (Notes, not a shared file), replace `<password>` with your real password. Delete the angle brackets `<` and `>` too.
  - Password has any of `@ : / ? # %`? Do not paste it. Tell me which characters it has (not the password itself) and I will tell you how to convert them.
- [ ] **7. Save it in `backend/.env`.** In VS Code, open `backend/.env`. Add this line at the end (or fill it in if it exists), with no spaces and no quotes:
  ```
  MONGODB_URI=mongodb+srv://finpilot:YourRealPassword@finpilot.abc12.mongodb.net/?retryWrites=true&w=majority
  ```
  Save with **Cmd+S**.
  - **Your string may end differently** from this example, for example at `.mongodb.net/` or with `?appName=Cluster0`. That is fine. Keep exactly what Atlas gave you and only replace `<password>`.
- [ ] **8. Tell me "done".** I will test the connection without showing the password.

## Later (the build agent tells you when)

- **Add the same line to Render.** Open your service → **Environment** → **Add Environment Variable** → key `MONGODB_URI`, value = the same string.
- **See your data.** In Atlas → **Database** → **Browse Collections**. You will see the database `finpilot` with the collections `users`, `accounts`, `transactions`, `recurring_bills` and `income_sources`. This is a good screen to show the judges.

## If something goes wrong

| What you see | Likely cause |
|---|---|
| `bad auth` or `Authentication failed` | Wrong password, or the user name is not `finpilot`. |
| A timeout, or hanging for 30 seconds | Step 4 was skipped. Add the "Allow Access from Anywhere" rule. |
| `<password>` still in the string | Step 6 was skipped. |
