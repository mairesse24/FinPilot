# Deploying the frontend (free) and connecting it to the backend

The frontend (`frontend/`, Vite + React) is static files. The backend runs on Render. They connect through one build-time setting:

`VITE_API_BASE` = the backend address, for example `https://finpilot-o0gj.onrender.com` (no trailing slash needed).

- Local development: leave it unset. Vite proxies `/api` to `http://127.0.0.1:8000` (`FINPILOT_API_TARGET` changes that).
- Hosted: set it when you build. The browser then calls the backend directly. The backend allows any website (`CORS_ORIGINS=*` in Render), so no proxy or rewrite rule is needed. This also avoids proxy time limits when the free Render server wakes up (30–60 s).
- The app uses `#/page` routes, so the host needs no special page-routing rules.

## Option A: Netlify Drop (no GitHub access needed, about 5 minutes)

1. Build: `cd frontend && npm ci && VITE_API_BASE=https://<your-backend>.onrender.com npm run build` (creates `frontend/dist`).
2. Open https://app.netlify.com/drop, sign up or log in, and drag the `dist` folder onto the page.
3. Netlify prints an address like `https://random-name.netlify.app`. Open it.
4. Keep the site: log in so the drop is attached to your account. Rename it under **Site configuration → Change site name**.
5. Redeploy after any change: rebuild (step 1) and drop the new `dist` onto **Deploys → drag and drop**.

## Option B: Git-connected (auto-deploys on every push)

Netlify or Vercel: import the GitHub repo, set **Base/Root directory** `frontend`, **Build command** `npm run build`, **Publish/Output directory** `dist`, and the environment variable `VITE_API_BASE`. This needs the GitHub account that owns the repo to authorize the host.

## Checks

- Open the backend `/healthz` first (the free server sleeps after about 15 minutes idle).
- Open the site. The Overview page should show Alex's accounts and a Guardian alert.
- If the page says "API unavailable" or "unable to load", the build was made without `VITE_API_BASE` or the backend is asleep.
- Backend CORS test: `curl -i -H "Origin: https://x.netlify.app" <backend>/api/accounts` shows `access-control-allow-origin: *`.
