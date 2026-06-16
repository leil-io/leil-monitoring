// Command leil-api serves the LeilFS/SaunaFS monitoring JSON API. It is the Go
// port of src/leil_api/main.py.
package main

import (
	"log"
	"net"
	"net/http"
	"strconv"

	"github.com/leil-io/saunafs-monitoring/go/internal/httpapi"
)

func main() {
	cfg := httpapi.LoadConfig()
	addr := net.JoinHostPort(cfg.Host, strconv.Itoa(cfg.Port))

	srv := &http.Server{
		Addr:    addr,
		Handler: httpapi.NewRouter(cfg),
	}

	log.Printf("leil-api listening on %s (master %s:%d)", addr, cfg.MasterHost, cfg.MasterPort)
	if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatalf("server error: %v", err)
	}
}
