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

## Run

```sh
go run ./cmd/leil-api          # serves on :8001 by default
go build ./... && go vet ./... && go test ./...
```

Configuration (same env vars and defaults as the Python API):

| Env | Default |
|---|---|
| `SAUNAFS_MASTER_HOST` | `sfsmaster` |
| `SAUNAFS_MASTER_PORT` | `9421` |
| `SAUNAFS_API_HOST` | `0.0.0.0` |
| `SAUNAFS_API_PORT` | `8001` |
| `SAUNAFS_API_LOGLEVEL` | `INFO` |

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
