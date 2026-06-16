// Command leil-monitoring serves the Preact frontend and reverse-proxies /api/*
// (plus /docs and /openapi.json) to the leil-api JSON backend. Keeping the SPA
// and the API on the same origin avoids CORS.
package main

import (
	"log"
	"net"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"strconv"

	"github.com/leil-io/saunafs-monitoring/go/internal/webui"
)

func main() {
	apiURL := env("LEIL_API_URL", "http://localhost:8001")
	host := env("SAUNAFS_MONITORING_HOST", "0.0.0.0")
	port := envInt("SAUNAFS_MONITORING_PORT", 8000)

	target, err := url.Parse(apiURL)
	if err != nil {
		log.Fatalf("invalid LEIL_API_URL %q: %v", apiURL, err)
	}
	proxy := httputil.NewSingleHostReverseProxy(target)

	mux := http.NewServeMux()
	mux.Handle("/api/", proxy)
	mux.Handle("/docs", proxy)
	mux.Handle("/openapi.json", proxy)
	mux.Handle("/", webui.Handler())

	addr := net.JoinHostPort(host, strconv.Itoa(port))
	log.Printf("leil-monitoring listening on %s (api -> %s)", addr, apiURL)
	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Fatalf("server error: %v", err)
	}
}

func env(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

func envInt(key string, def int) int {
	if v := os.Getenv(key); v != "" {
		if n, err := strconv.Atoi(v); err == nil {
			return n
		}
	}
	return def
}
