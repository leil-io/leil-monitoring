package wire

import (
	"net"
	"strings"
)

// Resolve performs a reverse-DNS lookup, mirroring the Python models' use of
// socket.gethostbyaddr with an "(unresolved)" fallback. It is a package
// variable so tests can substitute a deterministic resolver.
var Resolve = func(ip string) string {
	names, err := net.LookupAddr(ip)
	if err != nil || len(names) == 0 {
		return "(unresolved)"
	}
	// gethostbyaddr returns names without the trailing dot; LookupAddr keeps it.
	return strings.TrimSuffix(names[0], ".")
}
