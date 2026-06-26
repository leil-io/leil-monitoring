# Design: connect leilfs-monitoring directly to leilfs-api

**Date:** 2026-06-26
**Repo:** leilfs-monitoring
**Phase:** 2 of 2 (depends on Phase 1: charts endpoint in leilfs-api)
**Status:** approved, pending implementation plan

## Context

Today leilfs-monitoring is a three-tier stack:

```
SPA (Preact, embedded)
  → leil-monitoring   (Go: serves the SPA + reverse-proxies /api/*)        :8000
  → leil-api          (Go: its OWN JSON API /api/* + apiclient adapter)    :8001  ← the "second API"
  → leilfs-api (/api/v1/*)  OR  master binary protocol
```

`leil-api` is an intermediate API: its `apiclient` adapter calls leilfs-api's
canonical `/api/v1/*` (camelCase) and re-maps the responses to legacy model
shapes the SPA expects, and it serves charts itself over the binary protocol.

We are removing `leil-api` entirely so the SPA consumes leilfs-api's canonical
contract directly. Once leilfs-api serves charts (Phase 1), nothing in
`leil-api` is still needed.

Target topology (chosen: "thin proxy"):

```
SPA (Preact, embedded)
  → leil-monitoring   (Go: serves the SPA + reverse-proxies /api/v1/* to leilfs-api)
  → leilfs-api (/api/v1/*)
```

Same origin (SPA + proxy on one host) → no CORS. `leil-monitoring` stays as a
static host + reverse proxy; it is not an API.

## Goal

1. Delete the intermediate `leil-api` service and the `apiclient` adapter.
2. Rewrite the SPA data layer to consume leilfs-api's canonical `/api/v1/*`
   responses directly.
3. Repoint `leil-monitoring` to reverse-proxy leilfs-api.
4. Replace the free-text host/port + "Go" control with a node dropdown that
   drives per-node charts.

## Non-goals

- Changing leilfs-api (done in Phase 1).
- Re-styling the dashboard beyond swapping the node control.
- Keeping a binary-protocol fallback in monitoring (it goes away with leil-api).

## Components

### Deletions

- `cmd/leil-api/` — the intermediate service entrypoint.
- `internal/httpapi/` — its JSON `/api/*` handlers + router (the second API).
- `internal/apiclient/` — the canonical→legacy adapter.
- `leilfs/` — the binary-protocol client, **if** nothing else references it after
  the above are gone (charts now come from leilfs-api). Confirm during planning;
  expected fully removable.

> `internal/apiclient/apiclient.go` is the authoritative reference for the SPA
> rewrite: it documents exactly which canonical `/api/v1/*` field maps to each
> legacy field. Use it as the rosetta stone, then delete it.

### leil-monitoring (the surviving proxy + SPA host)

`cmd/leil-monitoring/main.go`
- Reverse-proxy target → leilfs-api (env `LEIL_API_URL`, e.g.
  `http://leilfs-api:8080`). `/api/v1/*` is under the existing `/api/` match, so
  paths pass through unchanged (no rewrite).
- Keep serving the embedded SPA at `/` (`webui.Handler()`), unchanged.
- Optionally proxy `/docs` and `/openapi.json` to leilfs-api too (now that
  leilfs-api serves Swagger UI).

### SPA (`web/src/`) — the bulk of the work

`api.ts`
- Repoint every call from legacy `/api/*` to canonical `/api/v1/*`:

  | Legacy (delete)            | Canonical (leilfs-api)            |
  |----------------------------|-----------------------------------|
  | `/api/info`                | `/api/v1/cluster`                 |
  | `/api/chunkservers`        | `/api/v1/chunkservers`            |
  | `/api/disks`               | `/api/v1/disks?verbose=true`      |
  | `/api/metaloggers`         | `/api/v1/metaloggers`             |
  | `/api/inotifiers`          | `/api/v1/inotifiers`              |
  | `/api/mounts`              | `/api/v1/mounts`                  |
  | `/api/metadataservers`     | `/api/v1/metadata-servers`        |
  | `/api/fscheckinfo`         | `/api/v1/cluster/fs-check`        |
  | `/api/chunkoperationsinfo` | `/api/v1/cluster/chunk-operations`|
  | `/api/chunkmatrix`         | `/api/v1/cluster/chunk-matrix`    |
  | `/api/goals`               | `/api/v1/goals`                   |
  | `/api/exports`             | `/api/v1/exports`                 |
  | `/api/chunkhealth`         | `/api/v1/cluster/chunk-health`    |
  | `/api/cgicharts`           | `/api/v1/charts`                  |

- Drop the `masterhost`/`masterport` query params (leilfs-api is configured with
  its own master and ignores them).
- Pass `resolve=true` where the UI shows hostnames (the adapter did this).

TypeScript types + components
- Replace legacy model types with leilfs-api's canonical camelCase shapes; update
  every component field access. Derived from the `apiclient` mapping. Flag any
  legacy field with **no** canonical source as a gap (decide per field: add to
  leilfs-api or drop from the SPA — record in the plan).

`charts.ts`
- Fetch `/api/v1/charts?id=<id>&node=<selected>`; `node` empty → master.

### Charts: two enumerated pages (`ChartsSection.tsx`, `app.tsx`)

- Remove the `host`/`port` `<input>`s and the `Go` button (and `applyMaster`).
  Keep the `Refresh` button. No dropdown.
- **Keep the two chart pages** — a **Masters** page and a **Chunkservers** page —
  each *enumerating* its nodes (one chart block per node), matching the existing
  per-server charts behavior and scaling to future multi-master clusters.
  - **Chunkservers page:** enumerate `/api/v1/chunkservers` (connected), one block
    per server, `node=<ip>`.
  - **Masters page:** enumerate masters from `/api/v1/metadata-servers`
    (`personality === "master"`), one block per master. **Phase-1 targeting
    limit:** leilfs-api's `/api/v1/charts` resolves `node` only to `""` (configured
    master) or a known chunkserver id/ip, so every master block uses `node=""`
    today. True per-master targeting needs a future leilfs-api enhancement
    (resolve master/shadow ips); the page is structured to enumerate so it is
    ready when that lands.
- Data sections no longer need a master selector (single-cluster — leilfs-api is
  bound to one cluster); they keep a constant `master` prop to avoid churn.

### Deploy

- `compose.yaml`: remove the `leil-api-go` service; add leilfs-api; set
  `leil-monitoring-go`'s `LEIL_API_URL` → leilfs-api.
- Remove the leil-api Dockerfile/build wiring.
- `vite.config.ts`: dev proxy `/api` (and `/api/v1`, `/docs`, `/openapi.json`)
  → leilfs-api dev URL.

## Data flow (after)

```
SPA fetch /api/v1/chunkservers
  → leil-monitoring (reverse proxy, same origin)
  → leilfs-api /api/v1/chunkservers  → master binary
Charts: SPA /api/v1/charts?id&node → proxy → leilfs-api → target node binary
```

## Error handling

leilfs-api returns canonical JSON errors; the SPA surfaces them as today. The
proxy passes status codes through. No adapter error-translation layer remains.

## Testing

- Go: suite shrinks with the deletions; keep/adjust the `leil-monitoring` proxy
  test to assert it forwards `/api/v1/*` to the configured target.
- SPA: `npm run build` clean; component/type checks compile against the new
  shapes.
- End-to-end (compose): leilfs-api + leil-monitoring + integration cluster →
  load the SPA, verify every section renders, charts load for Master and a
  chunkserver via the dropdown, errors surface.

## Cutover

Single cutover (no gradual toggle — leil-api is deleted): the SPA rewrite and
the proxy repoint land together. Phase 1 (charts in leilfs-api) must be deployed
first. Mitigation for shape gaps: the `apiclient` mapping is the field-by-field
reference; planning resolves every gap before the cutover.

## Risks

1. Legacy↔canonical field gaps — some dashboard fields may lack a canonical
   source. The `apiclient` adapter reveals them; resolve each (add to leilfs-api
   or drop) during planning.
2. `resolve=true` must be set where hostnames are shown, or the UI shows raw IPs.
3. Charts depend on Phase 1 being live (per-node targeting + content-type sniff).
4. If `leilfs/` is referenced by something unexpected, its removal is deferred —
   confirm before deleting.

## Commit convention

Plain (unsigned) commits, per this repo's convention (unlike leilfs-api).
