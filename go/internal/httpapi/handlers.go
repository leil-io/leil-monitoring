// Package httpapi exposes the LeilFS/SaunaFS client over HTTP, mirroring the
// FastAPI service in src/leil_api/main.py. Responses are byte-compatible with
// the Python API (same field names, same shapes).
package httpapi

import (
	"bytes"
	"encoding/json"
	"net"
	"net/http"
	"strconv"

	"github.com/go-chi/chi/v5"
	"github.com/leil-io/saunafs-monitoring/go/leilfs"
)

// ClientFactory builds a client for a given master host/port. Injectable so
// tests can supply a client backed by a mock dialer.
type ClientFactory func(host string, port int) *leilfs.Client

// API holds handler dependencies.
type API struct {
	cfg       Config
	newClient ClientFactory
}

type apiError struct {
	status int
	detail string
}

// NewRouter builds the chi router with the real client factory.
func NewRouter(cfg Config) http.Handler {
	return NewRouterWithClient(cfg, leilfs.NewClient)
}

// NewRouterWithClient builds the router with a custom client factory.
func NewRouterWithClient(cfg Config, newClient ClientFactory) http.Handler {
	a := &API{cfg: cfg, newClient: newClient}
	r := chi.NewRouter()

	r.Get("/api/info", a.json(func(c *leilfs.Client) (any, error) { return c.GetInfo() }))
	r.Get("/api/chunkhealth", a.json(func(c *leilfs.Client) (any, error) { return c.GetChunkHealth() }))
	r.Get("/api/chunkservers", a.json(func(c *leilfs.Client) (any, error) { return c.GetServers() }))
	r.Get("/api/disks", a.json(func(c *leilfs.Client) (any, error) { return c.GetDisks() }))
	r.Get("/api/mounts", a.json(func(c *leilfs.Client) (any, error) { return c.GetMounts() }))
	r.Get("/api/metadataservers", a.json(func(c *leilfs.Client) (any, error) { return c.GetMetadataServers() }))
	r.Get("/api/inotifiers", a.json(func(c *leilfs.Client) (any, error) { return c.GetInotifiers() }))
	r.Get("/api/fscheckinfo", a.json(func(c *leilfs.Client) (any, error) { return c.GetFsCheckInfo() }))
	r.Get("/api/chunkoperationsinfo", a.json(func(c *leilfs.Client) (any, error) { return c.GetChunkOperationsInfo() }))
	r.Get("/api/goals", a.json(func(c *leilfs.Client) (any, error) { return c.GetGoals() }))
	r.Get("/api/exports", a.json(func(c *leilfs.Client) (any, error) { return c.GetExports() }))
	r.Get("/api/chunkmatrix", a.json(func(c *leilfs.Client) (any, error) { return c.GetChunkMatrix() }))
	r.Get("/api/metaloggers", a.json(func(c *leilfs.Client) (any, error) { return c.GetMetaloggers() }))
	r.Get("/api/cgicharts", a.handleChart)

	r.Get("/", func(w http.ResponseWriter, r *http.Request) {
		http.Redirect(w, r, "/docs", http.StatusTemporaryRedirect)
	})
	r.Get("/docs", a.handleDocs)
	r.Get("/openapi.json", a.handleOpenAPI)

	return r
}

// json wraps a client call that returns a JSON-serializable value, mirroring the
// thin FastAPI endpoints (404 on master lookup failure, 500 on client error).
func (a *API) json(fn func(*leilfs.Client) (any, error)) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		client, aerr := a.clientFromRequest(r)
		if aerr != nil {
			writeDetail(w, aerr.status, aerr.detail)
			return
		}
		result, err := fn(client)
		if err != nil {
			writeDetail(w, http.StatusInternalServerError, "Internal Server Error")
			return
		}
		writeJSON(w, http.StatusOK, result)
	}
}

func (a *API) handleChart(w http.ResponseWriter, r *http.Request) {
	q := r.URL.Query()
	idStr := q.Get("id")
	id, err := strconv.ParseUint(idStr, 10, 32)
	if err != nil {
		writeDetail(w, http.StatusUnprocessableEntity, "Invalid or missing 'id'")
		return
	}
	host := q.Get("host")
	if host == "" {
		host = a.cfg.MasterHost
	}
	port := a.cfg.MasterPort
	if p := q.Get("port"); p != "" {
		if n, err := strconv.Atoi(p); err == nil {
			port = n
		}
	}

	resolved, aerr := resolveHost(host)
	if aerr != nil {
		writeDetail(w, aerr.status, aerr.detail)
		return
	}
	client := a.newClient(resolved, port)

	data, err := client.GetChart(resolved, port, uint32(id))
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, "Could not get charts: "+err.Error())
		return
	}
	mediaType, ok := sniffChart(data)
	if !ok {
		writeDetail(w, http.StatusInternalServerError, "Could not get charts: unknown data")
		return
	}
	w.Header().Set("Content-Type", mediaType)
	w.WriteHeader(http.StatusOK)
	w.Write(data)
}

// sniffChart mirrors the media-type detection in main.py:174-181.
func sniffChart(data []byte) (string, bool) {
	switch {
	case bytes.HasPrefix(data, []byte("\x89PNG\r\n\x1a\n")):
		return "image/png", true
	case bytes.HasPrefix(data, []byte("timestamp")):
		return "text/plain", true
	case bytes.HasPrefix(data, []byte("GIF")):
		return "image/gif", true
	default:
		return "", false
	}
}

func (a *API) clientFromRequest(r *http.Request) (*leilfs.Client, *apiError) {
	q := r.URL.Query()
	host := q.Get("masterhost")
	if host == "" {
		host = a.cfg.MasterHost
	}
	port := a.cfg.MasterPort
	if p := q.Get("masterport"); p != "" {
		if n, err := strconv.Atoi(p); err == nil {
			port = n
		}
	}
	resolved, aerr := resolveHost(host)
	if aerr != nil {
		return nil, aerr
	}
	return a.newClient(resolved, port), nil
}

// resolveHost mirrors get_client: only the magic "sfsmaster" name is resolved
// here, and a lookup failure becomes a 404. Other hosts pass through unchanged.
func resolveHost(host string) (string, *apiError) {
	if host != "sfsmaster" {
		return host, nil
	}
	addrs, err := net.LookupHost(host)
	if err != nil || len(addrs) == 0 {
		return "", &apiError{status: http.StatusNotFound, detail: "Master host not found: " + host}
	}
	return addrs[0], nil
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetEscapeHTML(false) // match Starlette JSONResponse (no HTML escaping)
	if err := enc.Encode(v); err != nil {
		writeDetail(w, http.StatusInternalServerError, "Internal Server Error")
		return
	}
	body := bytes.TrimRight(buf.Bytes(), "\n")
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	w.Write(body)
}

func writeDetail(w http.ResponseWriter, status int, detail string) {
	writeJSON(w, status, map[string]string{"detail": detail})
}
