# leil-monitoring web (Preact)

Browser frontend that consumes the Go `leil-api` JSON API. Visually mirrors the
Python/Jinja UI (reuses `leil-modern.css`, ports `charts.js`/`leil-sort.js`).

Stack: **Preact + Vite + TypeScript**, Chart.js for charts. Built to
`../internal/webui/dist` and embedded into the `cmd/leil-monitoring` Go binary,
which serves the SPA and reverse-proxies `/api/*` to leil-api (same origin).

## Develop

```sh
# 1) run the API (proxied target), pointing at a reachable master
cd .. && go run ./cmd/leil-api          # :8001

# 2) Vite dev server with HMR (proxies /api -> :8001)
cd web && npm install && npm run dev     # :5173
```

Override the proxy target with `LEIL_API_URL` (used by the dev compose service).

## Build + serve (single binary)

```sh
cd web && npm ci && npm run build        # -> ../internal/webui/dist
cd .. && go run ./cmd/leil-monitoring     # :8000, serves SPA + proxies /api
```

`LEIL_API_URL` (default `http://localhost:8001`) selects the API backend;
`SAUNAFS_MONITORING_HOST`/`SAUNAFS_MONITORING_PORT` (0.0.0.0/8000) the bind addr.

## Layout

- `src/api.ts` — typed fetch wrappers; forwards `masterhost`/`masterport`.
- `src/types.ts` — interfaces mirroring the Go models.
- `src/format.ts` — `humanizeBytes`/`formatTimestamp` (ports of the Jinja filters).
- `src/chunkhealth.ts` — client-side `from_chunk_health` + goal sums.
- `src/charts.ts` — port of `charts.js` (chart catalogs + CSV pipeline).
- `src/components/*Section.tsx` — one component per nav section.
- `src/components/DataTable.tsx` — generic sortable `.FR` table.

## Docker

```sh
docker build -f ../Dockerfile.web -t leil-monitoring-go ..
docker compose up leil-monitoring-go     # host port 8003 -> 8000
```
