// Package webui serves the embedded Preact single-page app (built by Vite into
// the dist/ directory). It is consumed by cmd/leil-monitoring.
package webui

import (
	"embed"
	"io/fs"
	"net/http"
	"path"
	"strings"
)

//go:embed all:dist
var distFS embed.FS

// Handler returns an http.Handler that serves the built SPA. Real asset paths
// are served directly; any other path falls back to index.html so client-side
// routing works.
func Handler() http.Handler {
	sub, err := fs.Sub(distFS, "dist")
	if err != nil {
		panic(err)
	}
	fileServer := http.FileServer(http.FS(sub))
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		p := strings.TrimPrefix(path.Clean(r.URL.Path), "/")
		if p == "" {
			p = "index.html"
		}
		if _, err := fs.Stat(sub, p); err != nil {
			// Not a built asset -> serve the SPA entrypoint.
			r.URL.Path = "/"
		}
		fileServer.ServeHTTP(w, r)
	})
}
