# Cloudflare production setup (free plan)

Everything in Tier 0 runs on the Cloudflare free plan: Pages (site + functions),
D1 (database), the domain's DNS, and email forwarding. One account, $0/mo.
Prereq: mitehuacan.mx purchased at a registrar (see production-stack.md §1).

## 1. Add the domain

Dashboard → **Add a domain** → `mitehuacan.mx` → Free plan. Cloudflare shows two
nameservers → set them at your registrar (replaces the registrar's DNS). Wait for
"Active" (minutes to hours). Nothing else to configure yet — Pages adds its own DNS.

## 2. Create the Pages project (site + API)

Dashboard → Workers & Pages → **Create → Pages → Connect to Git** → pick the
GitHub repo (`mauriciotellezdev/mitehuacan` — see production-stack.md §2).

- Build command: `python3 tehuacan/scripts/06_build_map.py && python3 tehuacan/scripts/12_build_sponsors.py && python3 tehuacan/scripts/09_build_site.py`
- Build output directory: `site`
- The `functions/` directory at repo root deploys automatically (analytics
  middleware, /system, /api/*).

After first deploy: project → **Custom domains** → add `mitehuacan.mx` (and `www`).

## 3. D1 database + migrations

```bash
bunx wrangler login                       # one-time browser auth (or use API token, §5)
bunx wrangler d1 create quecombi          # prints database_id
# put that id into wrangler.toml (database_id = "...")
bunx wrangler d1 migrations apply quecombi --remote
```

Then bind it: Pages project → Settings → Functions → **D1 database bindings** →
variable `DB` → database `quecombi`. (The wrangler.toml binding covers direct
`wrangler pages deploy`; the dashboard binding covers Git-triggered builds.)

## 4. Secrets

Pages project → Settings → Environment variables → Production:

- `STATS_TOKEN` = long random string (`openssl rand -hex 24`) — gates /system.

## 5. API token so the agent can manage this (SECURITY.md rules apply)

My Profile → API Tokens → **Create Token → Custom**:

| Scope | Permission |
|---|---|
| Account · Cloudflare Pages | Edit |
| Account · D1 | Edit |
| Zone · DNS (zone: mitehuacan.mx) | Edit |

Copy the token ONCE into `~/.config/mitehuacan/secrets.env` (`chmod 600`) as
`CLOUDFLARE_API_TOKEN=...` plus `CLOUDFLARE_ACCOUNT_ID=...` (dashboard sidebar).
Never into the repo. The agent then deploys/migrates with
`CLOUDFLARE_API_TOKEN=... bunx wrangler ...` without browser auth.
Also add both as **GitHub Actions secrets** if/when CI deploys.

## 6. Email + optional GPS tunnel

- **Email Routing** (free): mitehuacan.mx → Email → enable → route
  `security@mitehuacan.mx` → your inbox. Unblocks SECURITY.md's contact with no
  mail provider.
- **cloudflared named tunnel** (free, later): `cloudflared tunnel create gps`,
  route `gps.mitehuacan.mx` → `http://localhost:5055`, run as a service on the Mac.
  Gives Traccar Client a live URL (MAPPING.md §6).

## 7. Verify production

1. `https://mitehuacan.mx` → lands on the map (the `_redirects` 302).
2. `https://mitehuacan.mx/qr/test-1` → map with `?qr=test-1`.
3. `https://mitehuacan.mx/system` → token → dashboard shows YOUR visit already logged.
4. Submit a test report on /acerca/ → appears in /system "Reportes de rutas".
5. `curl -sI https://mitehuacan.mx/system | grep -i x-robots` → noindex.

## Free-tier limits that matter (and our §9 triggers)

| Resource | Free limit | Our design point (10k DAU) |
|---|---|---|
| Pages Functions requests | 100k/day | ~15-25k/day (hits+events) — fine |
| D1 storage | 5 GB | analytics+reports: years of headroom |
| D1 reads/writes | 5M reads / 100k writes per day | writes ~25k/day — fine |
| Pages builds | 500/mo | a few per day — fine |

First real pressure point is Functions requests around ~40k DAU — which is §9
territory anyway (Tier 1 migration).
