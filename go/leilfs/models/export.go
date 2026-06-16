package models

import (
	"strings"

	"github.com/leil-io/saunafs-monitoring/go/leilfs/internal/wire"
)

// Export mirrors models.Export. Not exposed by the JSON API directly, but used
// by get_mounts/goal handling parity and kept for completeness.
type Export struct {
	ID     int    `json:"id"`
	IPFrom string `json:"ip_from"`
	IPTo   string `json:"ip_to"`
	Path   string `json:"path"`
	Flags  string `json:"flags"`
}

func ExportFromBuffer(r *wire.Reader) (Export, error) {
	var e Export
	octs := make([]uint8, 8)
	for i := range octs {
		v, err := r.U8()
		if err != nil {
			return e, wrap("Export", err)
		}
		octs[i] = v
	}
	path, err := r.String(true)
	if err != nil {
		return e, wrap("Export", err)
	}
	if r.Remaining() < 22 {
		return e, &wire.Error{Msg: "Failed to deserialize Export: Unsupported master version"}
	}
	// ">HBBBBLLLL": version(H,B,B), exportflags(B), sesflags(B), then 4 × L.
	if _, err := r.U16(); err != nil { // v1
		return e, wrap("Export", err)
	}
	if _, err := r.U8(); err != nil { // v2
		return e, wrap("Export", err)
	}
	if _, err := r.U8(); err != nil { // v3
		return e, wrap("Export", err)
	}
	if _, err := r.U8(); err != nil { // exportflags
		return e, wrap("Export", err)
	}
	sesflags, err := r.U8()
	if err != nil {
		return e, wrap("Export", err)
	}
	for i := 0; i < 4; i++ { // rootuid, rootgid, mapalluid, mapallgid
		if _, err := r.U32(); err != nil {
			return e, wrap("Export", err)
		}
	}

	var flags []string
	if sesflags&1 != 0 {
		flags = append(flags, "ro")
	} else {
		flags = append(flags, "rw")
	}
	if sesflags&2 != 0 {
		flags = append(flags, "dynamic_ip")
	}
	if sesflags&4 != 0 {
		flags = append(flags, "ignore_gid")
	}
	if sesflags&8 != 0 {
		flags = append(flags, "quota_admin")
	}
	if sesflags&16 != 0 {
		flags = append(flags, "map_all")
	}

	e = Export{
		IPFrom: ipv4(octs[0], octs[1], octs[2], octs[3]),
		IPTo:   ipv4(octs[4], octs[5], octs[6], octs[7]),
		Path:   path,
		Flags:  strings.Join(flags, ", "),
	}
	return e, nil
}

// ExportList mirrors Export.get_list: reads while at least 12 bytes remain.
func ExportList(r *wire.Reader) ([]Export, error) {
	exports := []Export{}
	i := 1
	for r.Remaining() >= 12 {
		e, err := ExportFromBuffer(r)
		if err != nil {
			return nil, err
		}
		e.ID = i
		i++
		exports = append(exports, e)
	}
	return exports, nil
}
