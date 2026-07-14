# Production stack — signups, API keys, and free-tier choices

Rule that picked every tech here: **free tier as long as possible**, with a known
paid escape hatch. Total monthly cost at launch: **$0** (only real money: domain
~$300 MXN/yr; store fees deferred to app launch).

For every key below: paste it once into `~/.config/quecombi/secrets.env`
(`chmod 600`, outside the repo — SECURITY.md §2). The agent reads keys from there
to manage services; nothing secret ever enters the repo or chat.

## 1. Domain registrar — quecombi.mx (~$250–450 MXN/yr; the only mandatory cost)

- **Choice:** any registrar that sells .mx cheaply (Namecheap, Porkbun, or the
  Mexican Akky). Cloudflare Registrar does NOT support .mx, so buy elsewhere and
  point nameservers at Cloudflare (docs/setup/cloudflare.md §1). DNS lives at
  Cloudflare, so registrar choice barely matters — optimize for renewal price.
- Turn OFF registrar auto-features (parking, their DNS, email upsells). Turn ON
  auto-renew + 2FA. **A lapsed domain kills every printed QR sticker** — this is
  the single most protect-worthy account in the stack.
- No API key needed (agent never touches the registrar).

## 2. GitHub (free) — code, CI, deploy trigger

- Repo `mauriciotellezdev/quecombi`, **public** (AGPL). Push this repo:
  `git remote add origin git@github.com:mauriciotellezdev/quecombi.git && git push -u origin main`
  (SSH key `~/.ssh/mauriciotellez_rsa` is already wired via `core.sshCommand`).
- Enable: Settings → branch protection on `main` (require PR for outside
  contributors); Security → secret scanning + push protection (free for public
  repos — this backs SECURITY.md's gitleaks rule server-side).
- **Agent key:** fine-grained PAT → only repo `quecombi` → permissions:
  Contents RW, Pull requests RW, Issues RW, Actions RW. Save as `GITHUB_TOKEN`
  in secrets.env (used by `gh` CLI).
- Actions secrets (for the deploy workflow, when added): `CLOUDFLARE_API_TOKEN`,
  `CLOUDFLARE_ACCOUNT_ID`.
- Free-tier limits: public repos get unlimited Actions minutes. No trigger to leave.

## 3. Cloudflare (free) — hosting, DB, DNS, analytics store, email forwarding

Full walkthrough: **docs/setup/cloudflare.md** (account exists; add domain, Pages,
D1, secrets, scoped API token for the agent, Email Routing).

## 4. Geocoding & tiles — no accounts at all (deliberately)

- **OpenFreeMap** (basemap tiles): no key, no signup, no usage cap. Escape hatch:
  self-host tiles on the Tier 1 VPS.
- **Photon (komoot) + Nominatim (OSM)** (address search): public instances, no keys.
  Fair-use rules we already follow: identify via UA/referer, cache results, ~1 rps.
  Escape hatch: self-host Photon (~2 GB RAM) when volume grows.
- Why no Mapbox/Google/HERE: all meter by key and invoice at exactly the moment a
  free civic app succeeds. Chosen against on the free-tier metric.

## 5. Traccar (self-hosted, free) — field mapping

Local on the Mac via colima/docker (MAPPING.md). Moves to the Tier 1 VPS when
recruited riders need an always-on server. No external account ever.

## 6. App stores — the only unavoidable paid accounts (deferred to app launch)

- Apple Developer Program **$99/yr** + Google Play **$25 once**. Sign up only when
  the Expo v0 build is ready for TestFlight (PRD-mobile §7); fee-waiver path via a
  university/civic partnership stays open.
- When created: App Store Connect API key + Play service-account JSON go in
  secrets.env for CI submissions (never in repo).

## 7. Explicitly NOT in the stack (and why)

| Service | Why not |
|---|---|
| Google Analytics / Firebase | third-party tracking; we built first-party (/system) |
| Sentry SaaS | js_error events cover it at our scale; GlitchTip on Tier 1 if needed |
| Mailgun/Resend/etc. | no outbound email product need yet; CF Email Routing handles inbound security@ |
| AWS/GCP anything | free tiers expire or require cards armed for overage; CF free doesn't |
| Paid CI/CD | GitHub Actions free on public repos |

## 8. The keys file (recap)

`~/.config/quecombi/secrets.env` — chmod 600, never committed, rotate per SECURITY.md:

```
CLOUDFLARE_API_TOKEN=...      # scoped: Pages+D1+DNS(quecombi.mx) Edit
CLOUDFLARE_ACCOUNT_ID=...
GITHUB_TOKEN=...              # fine-grained PAT, repo quecombi only
STATS_TOKEN=...               # same value as the Pages env var; for /system
```

Setup order: registrar (§1) → GitHub push (§2) → Cloudflare (§3, needs both) →
verify prod (cloudflare.md §7) → print the first sticker.
