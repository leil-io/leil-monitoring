# leil-api (Go)

Go port of the LeilFS/SaunaFS monitoring **JSON API** and its reusable
**client**. Functionally equivalent to the Python `src/leil_api` + `src/leil_client`,
with byte-compatible JSON responses (identical field names and shapes).

Scope of this phase: the wire client + models + the 13 HTTP endpoints. The
server-rendered monitoring UI (`src/leil_monitoring`) is **not** ported.

## Layout

Three layers, mirroring the Python `leil_client` / `leil_api` / `leil_monitoring`
split. The client layer is **public** (importable by other modules); only the
app-specific server code lives under `internal/`.

```
# Layer 1 — reusable client library (rooted at leilfs/):
leilfs/                  wire protocol (V1/V2 framing) + the Client (Get* methods)
leilfs/models/           data structs with *FromBuffer parsers and json tags (public)
leilfs/internal/wire/    cursor-based binary Reader + reverse-DNS helper (private)

# Layer 2 — JSON API:
internal/httpapi/  chi handlers, config, Swagger /docs
cmd/leil-api/      main(): env config + chi router + http.Server

# Layer 3 — frontend (Preact SPA + thin Go server):
web/               Vite + Preact + TS SPA (see web/README.md)
internal/webui/    embeds the built SPA (dist/)
cmd/leil-monitoring/ serves the SPA + reverse-proxies /api to leil-api
```

The client is dependency-free over the wire (`net`, `encoding/binary`). The only
third-party dependency is `github.com/go-chi/chi/v5` (API/web routing).

## Directory guide

Each top-level folder under `go/`, and the Go convention behind it:

| Path | What it is | Convention |
|---|---|---|
| `go.mod` / `go.sum` | Module definition (`github.com/leil-io/saunafs-monitoring/go`) and dependency checksums. The folder holding `go.mod` is the module root. | Standard Go module files. |
| `cmd/` | One subdirectory per executable; each holds a `package main` with `func main()`. `cmd/leil-api` → the JSON API binary, `cmd/leil-monitoring` → the web/SPA server. | Go idiom: `cmd/<name>/` is where binaries live, kept thin (wiring only). |
| `internal/` | Packages importable **only** by code inside this module — the Go compiler enforces this. Holds app-specific glue not meant for reuse: `internal/httpapi` (HTTP handlers), `internal/webui` (embeds the built SPA). | `internal/` is a Go-enforced privacy boundary. |
| `leilfs/` | The reusable client: protocol framing + the `Client` type and its `Get*` methods. The whole client library is rooted here. | Public package (not under `internal/`). |
| `leilfs/models/` | Plain data structs returned by the client, with binary `*FromBuffer` parsers and JSON tags. Callers need these for `Get*` return types. | Public subpackage of the client. |
| `leilfs/internal/wire/` | Low-level binary read primitives (cursor `Reader`) + reverse-DNS helper — a client implementation detail. | `internal/` under `leilfs/`: importable by `leilfs` and `leilfs/models` only, not by outside code. |
| `web/` | The Preact + Vite + TypeScript SPA source (its own npm project). Built output is embedded by `internal/webui`. | Front-end sub-project; not Go code. See `web/README.md`. |
| `Dockerfile` / `Dockerfile.web` | Container builds for the API binary and for the SPA+web-server binary, respectively. | — |

Key Go rules at play: a package's directory name is independent of its `package`
name (e.g. `leilfs/` declares `package leilfs`); identifiers are exported only when
Capitalized; and anything under any `internal/` directory is import-restricted to
this module.

## Using the client as a library

```go
import "github.com/leil-io/saunafs-monitoring/go/leilfs"

c := leilfs.NewClient("master-host", 9421) // probes master version
info, err := c.GetInfo()                    // returns models.SystemInfo
servers, err := c.GetServers()              // []models.Server
```

Returned types come from `github.com/leil-io/saunafs-monitoring/go/leilfs/models`.

## Data source: leilfs-api or the binary client

The JSON layer is fed by a `DataSource`. There are two implementations, chosen
at startup by whether `LEILFS_API_URL` is set:

- **leilfs-api mode (recommended)** — set `LEILFS_API_URL` to a running
  [leilfs-api](https://github.com/leil-io/leilfs-api) (the canonical LeilFS
  Unified API). `internal/apiclient` fetches `/api/v1/*` and maps the responses
  back to the legacy models, so the SPA and the `/api/*` contract are unchanged.
  The master host/port are then used **only for charts** (`/api/cgicharts`),
  which leilfs-api does not expose by design.
- **binary mode (fallback)** — `LEILFS_API_URL` unset: the in-process
  `leilfs.Client` speaks the cluster protocol directly, as before.

Data flow in leilfs-api mode:
`browser → leil-monitoring (SPA + proxy) → leil-api (this, adapter) → leilfs-api → cluster`.

## Run

```sh
# Against the canonical leilfs-api (assumed reachable at :8080):
LEILFS_API_URL=http://localhost:8080 go run ./cmd/leil-api   # serves :8001

# Legacy binary mode (talk to the master directly):
SAUNAFS_MASTER_HOST=master-host go run ./cmd/leil-api        # serves :8001

go build ./... && go vet ./... && go test ./...
```

Configuration (the Python API's env vars, plus `LEILFS_API_URL`):

| Env | Default | Meaning |
|---|---|---|
| `LEILFS_API_URL` | _(empty)_ | leilfs-api base URL; empty → legacy binary mode |
| `SAUNAFS_MASTER_HOST` | `sfsmaster` | master host (binary mode + charts) |
| `SAUNAFS_MASTER_PORT` | `9421` | master client port (binary mode + charts) |
| `SAUNAFS_API_HOST` | `0.0.0.0` | bind address |
| `SAUNAFS_API_PORT` | `8001` | listen port |
| `SAUNAFS_API_LOGLEVEL` | `INFO` | log level |

`GET /` redirects to `/docs` (Swagger UI backed by `/openapi.json`).

## Docker / compose

```sh
docker build -f go/Dockerfile -t leil-api-go:latest go
docker compose up leil-api-go        # host port 8002 -> container 8001
```

The `leil-api-go` service runs alongside the Python `leil-api` during migration.

## Compatibility notes

- Integer-keyed maps in `ChunkHealth` marshal to string-keyed JSON objects,
  matching Pydantic's `Dict[int, ...]` output (covered by a test).
- `DiskStats` float fields are JSON numbers; an integer-valued float serializes
  as `5` in Go vs `5.0` in Python — semantically identical once parsed.
