package httpapi

import (
	"os"
	"strconv"
)

// Config holds the runtime settings, mirroring the environment variables read
// by src/leil_api/main.py, plus LEILFS_API_URL which selects the canonical
// leilfs-api as the data source.
type Config struct {
	MasterHost string
	MasterPort int
	Host       string
	Port       int
	LogLevel   string
	// LeilfsAPIURL is the base URL of the canonical leilfs-api service (e.g.
	// "http://leilfs-api:8080"). When set, data is served from it instead of
	// the in-process binary client. The master host/port are still used for
	// charts, which leilfs-api does not expose.
	LeilfsAPIURL string
}

// LoadConfig reads configuration from the environment with the same defaults as
// the Python API.
func LoadConfig() Config {
	return Config{
		MasterHost:   env("SAUNAFS_MASTER_HOST", "sfsmaster"),
		MasterPort:   envInt("SAUNAFS_MASTER_PORT", 9421),
		Host:         env("SAUNAFS_API_HOST", "0.0.0.0"),
		Port:         envInt("SAUNAFS_API_PORT", 8001),
		LogLevel:     env("SAUNAFS_API_LOGLEVEL", "INFO"),
		LeilfsAPIURL: env("LEILFS_API_URL", ""),
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
