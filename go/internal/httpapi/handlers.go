// Package httpapi exposes the LeilFS/SaunaFS monitoring data over HTTP. The
// JSON responses are byte-compatible with the legacy Python API (same field
// names, same shapes) so the Preact SPA is unaffected.
//
// The data is served from a DataSource. Two implementations exist:
//
//   - apiclient.Client — fetches the canonical leilfs-api (/api/v1/*) over HTTP
//     and maps it back to the legacy models. Selected when LEILFS_API_URL is
//     set; this is the supported path now that leilfs-api is the canonical API.
//   - leilfs.Client — the in-process binary-protocol client, kept as a fallback
//     for deployments without leilfs-api and still used for charts (which
//     leilfs-api does not expose).
package httpapi

import (
	"bytes"
	"encoding/json"
	"net/http"
	"strconv"
	"sync"

	"github.com/go-chi/chi/v5"
	"github.com/leil-io/saunafs-monitoring/go/internal/apiclient"
	"github.com/leil-io/saunafs-monitoring/go/leilfs"
	"github.com/leil-io/saunafs-monitoring/go/leilfs/models"
)

// legacyMasterAlias is the placeholder master host the SPA sends by default.
// In the single-cluster model (leilfs-api is configured with one cluster, D4)
// it means "the configured master", so it is resolved to cfg.MasterHost rather
// than looked up in DNS (which would block ~10s when unresolvable).
const legacyMasterAlias = "sfsmaster"

// DataSource is the set of read operations the JSON endpoints need. Both
// leilfs.Client (binary protocol) and apiclient.Client (leilfs-api over HTTP)
// satisfy it.
type DataSource interface {
	GetInfo() (models.SystemInfo, error)
	GetChunkHealth() (models.ChunkHealth, error)
	GetServers() ([]models.Server, error)
	GetDisks() ([]models.Disk, error)
	GetMounts() ([]models.Mount, error)
	GetMetadataServers() ([]models.MetadataServer, error)
	GetInotifiers() ([]models.INotifier, error)
	GetFsCheckInfo() (models.FsCheckInfo, error)
	GetChunkOperationsInfo() (models.ChunkOperationsInfo, error)
	GetGoals() ([]models.Goal, error)
	GetExports() ([]models.Export, error)
	GetChunkMatrix() (models.ChunkMatrix, error)
	GetMetaloggers() ([]models.Metalogger, error)
}

// ClientFactory builds a binary-protocol client for a given master host/port.
// Injectable so tests can supply a client backed by a mock dialer; also used
// for charts, which are not part of leilfs-api.
type ClientFactory func(host string, port int) *leilfs.Client

// API holds handler dependencies.
type API struct {
	cfg Config
	// dataFor resolves the per-request data source.
	dataFor func(r *http.Request) (DataSource, *apiError)
	// newChartClient builds the binary client used by the chart endpoint.
	newChartClient ClientFactory

	// chartLocks serializes chart requests per target node (host:port). The SPA
	// renders ~20 chart panels at once, firing that many concurrent
	// /api/cgicharts requests; a chunkserver aborts (SIGABRT in a netWorker)
	// when it handles concurrent chart exchanges on its client port. Holding a
	// per-target lock across the dial+exchange means a given node never sees
	// more than one in-flight chart connection from us. Different nodes (master
	// vs each chunkserver) still run in parallel.
	chartGate  sync.Mutex
	chartLocks map[string]*sync.Mutex
}

type apiError struct {
	status int
	detail string
}

// NewRouter builds the chi router. When LEILFS_API_URL is configured the data
// is served from leilfs-api; otherwise it falls back to the in-process binary
// client (the legacy behavior).
func NewRouter(cfg Config) http.Handler {
	if cfg.LeilfsAPIURL != "" {
		client := apiclient.New(cfg.LeilfsAPIURL)
		dataFor := func(*http.Request) (DataSource, *apiError) { return client, nil }
		return newRouter(cfg, dataFor, leilfs.NewChartClient)
	}
	// Binary mode: data uses the probing client (the version gates need the
	// master version); charts use the no-probe client so they never send an
	// INFO probe to a chart target that may be a chunkserver (which aborts on
	// an unexpected INFO and drops off the cluster).
	dataFor := func(r *http.Request) (DataSource, *apiError) {
		return clientFromRequest(cfg, leilfs.NewClient, r)
	}
	return newRouter(cfg, dataFor, leilfs.NewChartClient)
}

// NewRouterWithClient builds the router in binary-client mode with a custom
// client factory (used by tests). Each request builds a client from the master
// host/port, preserving the legacy contract. The injected factory backs both
// data and charts so tests can observe chart routing; production charts use the
// no-probe client (see NewRouter).
func NewRouterWithClient(cfg Config, newClient ClientFactory) http.Handler {
	dataFor := func(r *http.Request) (DataSource, *apiError) {
		return clientFromRequest(cfg, newClient, r)
	}
	return newRouter(cfg, dataFor, newClient)
}

func newRouter(cfg Config, dataFor func(*http.Request) (DataSource, *apiError), newChartClient ClientFactory) http.Handler {
	a := &API{cfg: cfg, dataFor: dataFor, newChartClient: newChartClient, chartLocks: map[string]*sync.Mutex{}}
	r := chi.NewRouter()

	r.Get("/api/info", a.json(func(c DataSource) (any, error) { return c.GetInfo() }))
	r.Get("/api/chunkhealth", a.json(func(c DataSource) (any, error) { return c.GetChunkHealth() }))
	r.Get("/api/chunkservers", a.json(func(c DataSource) (any, error) { return c.GetServers() }))
	r.Get("/api/disks", a.json(func(c DataSource) (any, error) { return c.GetDisks() }))
	r.Get("/api/mounts", a.json(func(c DataSource) (any, error) { return c.GetMounts() }))
	r.Get("/api/metadataservers", a.json(func(c DataSource) (any, error) { return c.GetMetadataServers() }))
	r.Get("/api/inotifiers", a.json(func(c DataSource) (any, error) { return c.GetInotifiers() }))
	r.Get("/api/fscheckinfo", a.json(func(c DataSource) (any, error) { return c.GetFsCheckInfo() }))
	r.Get("/api/chunkoperationsinfo", a.json(func(c DataSource) (any, error) { return c.GetChunkOperationsInfo() }))
	r.Get("/api/goals", a.json(func(c DataSource) (any, error) { return c.GetGoals() }))
	r.Get("/api/exports", a.json(func(c DataSource) (any, error) { return c.GetExports() }))
	r.Get("/api/chunkmatrix", a.json(func(c DataSource) (any, error) { return c.GetChunkMatrix() }))
	r.Get("/api/metaloggers", a.json(func(c DataSource) (any, error) { return c.GetMetaloggers() }))
	r.Get("/api/cgicharts", a.handleChart)

	r.Get("/", func(w http.ResponseWriter, r *http.Request) {
		http.Redirect(w, r, "/docs", http.StatusTemporaryRedirect)
	})
	r.Get("/docs", a.handleDocs)
	r.Get("/openapi.json", a.handleOpenAPI)

	return r
}

// json wraps a data-source call that returns a JSON-serializable value (404 on
// master lookup failure, 500 on client error).
func (a *API) json(fn func(DataSource) (any, error)) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		data, aerr := a.dataFor(r)
		if aerr != nil {
			writeDetail(w, aerr.status, aerr.detail)
			return
		}
		result, err := fn(data)
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
	// Master charts arrive with the SPA's master-selector host (the legacy
	// "sfsmaster" placeholder by default); server charts arrive with a real
	// chunkserver IP. Route the master case to the configured master and honor
	// explicit (chunkserver) hosts as-is.
	host := q.Get("host")
	port := a.cfg.MasterPort
	if p := q.Get("port"); p != "" {
		if n, err := strconv.Atoi(p); err == nil {
			port = n
		}
	}
	if host == "" || host == legacyMasterAlias {
		host = a.cfg.MasterHost
		port = a.cfg.MasterPort
	}

	// Serialize concurrent chart requests to this node (see API.chartLocks): a
	// chunkserver aborts when it processes chart exchanges concurrently on its
	// client port.
	unlock := a.lockChartTarget(host + ":" + strconv.Itoa(port))
	defer unlock()

	client := a.newChartClient(host, port)

	data, err := client.GetChart(host, port, uint32(id))
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

// lockChartTarget acquires the per-target chart lock for "host:port", creating
// it on first use, and returns the unlock function. Requests to the same node
// serialize; requests to different nodes proceed in parallel.
func (a *API) lockChartTarget(target string) func() {
	a.chartGate.Lock()
	mu := a.chartLocks[target]
	if mu == nil {
		mu = &sync.Mutex{}
		a.chartLocks[target] = mu
	}
	a.chartGate.Unlock()

	mu.Lock()
	return mu.Unlock
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

// clientFromRequest builds a binary-protocol client for the configured master.
// In the single-cluster model the per-request ?masterhost/?masterport overrides
// the SPA still sends are ignored (leilfs-api / this service is bound to one
// configured cluster, D4), which also avoids the ~10s DNS hang the legacy
// "sfsmaster" lookup caused when that placeholder did not resolve.
func clientFromRequest(cfg Config, newClient ClientFactory, _ *http.Request) (DataSource, *apiError) {
	return newClient(cfg.MasterHost, cfg.MasterPort), nil
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
