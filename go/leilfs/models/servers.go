package models

import "github.com/leil-io/saunafs-monitoring/go/leilfs/internal/wire"

// Server mirrors models.Server (struct ">BBBBBBBBHQQLQQLLL" + V2 label).
type Server struct {
	ID                    int    `json:"id"`
	Hostname              string `json:"hostname"`
	IPAddress             string `json:"ip_address"`
	Port                  uint16 `json:"port"`
	Version               string `json:"version"`
	IsDisconnected        bool   `json:"is_disconnected"`
	Label                 string `json:"label"`
	UsedSpace             uint64 `json:"used_space"`
	TotalSpace            uint64 `json:"total_space"`
	Chunks                uint32 `json:"chunks"`
	UsedSpaceTobedeleted  uint64 `json:"used_space_tobedeleted"`
	TotalSpaceTobedeleted uint64 `json:"total_space_tobedeleted"`
	ChunksTobedeleted     uint32 `json:"chunks_tobedeleted"`
	ErrorCount            uint32 `json:"error_count"`
}

func ServerFromBuffer(r *wire.Reader) (Server, error) {
	var s Server
	u8 := func() (uint8, error) { return r.U8() }
	disconnected, err := u8()
	if err != nil {
		return s, wrap("Server", err)
	}
	v1b, err := u8()
	if err != nil {
		return s, wrap("Server", err)
	}
	v2, err := u8()
	if err != nil {
		return s, wrap("Server", err)
	}
	v3, err := u8()
	if err != nil {
		return s, wrap("Server", err)
	}
	ip1, err := u8()
	if err != nil {
		return s, wrap("Server", err)
	}
	ip2, err := u8()
	if err != nil {
		return s, wrap("Server", err)
	}
	ip3, err := u8()
	if err != nil {
		return s, wrap("Server", err)
	}
	ip4, err := u8()
	if err != nil {
		return s, wrap("Server", err)
	}
	port, err := r.U16()
	if err != nil {
		return s, wrap("Server", err)
	}
	used, err := r.U64()
	if err != nil {
		return s, wrap("Server", err)
	}
	total, err := r.U64()
	if err != nil {
		return s, wrap("Server", err)
	}
	chunks, err := r.U32()
	if err != nil {
		return s, wrap("Server", err)
	}
	tdused, err := r.U64()
	if err != nil {
		return s, wrap("Server", err)
	}
	tdtotal, err := r.U64()
	if err != nil {
		return s, wrap("Server", err)
	}
	tdchunks, err := r.U32()
	if err != nil {
		return s, wrap("Server", err)
	}
	errcnt, err := r.U32()
	if err != nil {
		return s, wrap("Server", err)
	}
	labelLen, err := r.U32()
	if err != nil {
		return s, wrap("Server", err)
	}
	raw, err := r.Raw(int(labelLen))
	if err != nil {
		return s, wrap("Server", err)
	}
	// V2-style: the length includes a trailing NUL.
	label := ""
	if labelLen > 0 {
		label = string(raw[:labelLen-1])
	}

	ip := ipv4(ip1, ip2, ip3, ip4)
	s = Server{
		ID:                    0, // assigned by caller
		Hostname:              wire.Resolve(ip),
		IPAddress:             ip,
		Port:                  port,
		Version:               version(uint16(v1b), v2, v3),
		IsDisconnected:        disconnected != 0,
		Label:                 label,
		UsedSpace:             used,
		TotalSpace:            total,
		Chunks:                chunks,
		UsedSpaceTobedeleted:  tdused,
		TotalSpaceTobedeleted: tdtotal,
		ChunksTobedeleted:     tdchunks,
		ErrorCount:            errcnt,
	}
	return s, nil
}

// ServerList mirrors Server.get_list: count-prefixed list, ids assigned 1..n.
func ServerList(r *wire.Reader) ([]Server, error) {
	count, err := r.U32()
	if err != nil {
		return nil, wrap("Server", err)
	}
	servers := make([]Server, 0, count)
	for i := uint32(0); i < count; i++ {
		s, err := ServerFromBuffer(r)
		if err != nil {
			return nil, err
		}
		s.ID = int(i) + 1
		servers = append(servers, s)
	}
	return servers, nil
}

// Metalogger mirrors models.Metalogger (struct ">HBBBBBB").
type Metalogger struct {
	ID        int    `json:"id"`
	Hostname  string `json:"hostname"`
	IPAddress string `json:"ip_address"`
	Version   string `json:"version"`
}

func MetaloggerFromBuffer(r *wire.Reader) (Metalogger, error) {
	var m Metalogger
	v1, err := r.U16()
	if err != nil {
		return m, wrap("Metalogger", err)
	}
	v2, err := r.U8()
	if err != nil {
		return m, wrap("Metalogger", err)
	}
	v3, err := r.U8()
	if err != nil {
		return m, wrap("Metalogger", err)
	}
	ip1, err := r.U8()
	if err != nil {
		return m, wrap("Metalogger", err)
	}
	ip2, err := r.U8()
	if err != nil {
		return m, wrap("Metalogger", err)
	}
	ip3, err := r.U8()
	if err != nil {
		return m, wrap("Metalogger", err)
	}
	ip4, err := r.U8()
	if err != nil {
		return m, wrap("Metalogger", err)
	}
	ip := ipv4(ip1, ip2, ip3, ip4)
	m = Metalogger{Hostname: wire.Resolve(ip), IPAddress: ip, Version: version(v1, v2, v3)}
	return m, nil
}

// MetaloggerList mirrors Metalogger.get_list: no count prefix, reads until the
// buffer is exhausted; ids assigned sequentially.
func MetaloggerList(r *wire.Reader) ([]Metalogger, error) {
	loggers := []Metalogger{}
	for r.Remaining() > 0 {
		m, err := MetaloggerFromBuffer(r)
		if err != nil {
			return nil, err
		}
		m.ID = len(loggers) + 1
		loggers = append(loggers, m)
	}
	return loggers, nil
}

// INotifier mirrors models.INotifier (struct ">BBBBHBB" — note the differing
// field order from Metalogger).
type INotifier struct {
	ID        int    `json:"id"`
	Hostname  string `json:"hostname"`
	IPAddress string `json:"ip_address"`
	Version   string `json:"version"`
}

func INotifierFromBuffer(r *wire.Reader) (INotifier, error) {
	var n INotifier
	ip1, err := r.U8()
	if err != nil {
		return n, wrap("INotifier", err)
	}
	ip2, err := r.U8()
	if err != nil {
		return n, wrap("INotifier", err)
	}
	ip3, err := r.U8()
	if err != nil {
		return n, wrap("INotifier", err)
	}
	ip4, err := r.U8()
	if err != nil {
		return n, wrap("INotifier", err)
	}
	v1, err := r.U16()
	if err != nil {
		return n, wrap("INotifier", err)
	}
	v2, err := r.U8()
	if err != nil {
		return n, wrap("INotifier", err)
	}
	v3, err := r.U8()
	if err != nil {
		return n, wrap("INotifier", err)
	}
	ip := ipv4(ip1, ip2, ip3, ip4)
	n = INotifier{Hostname: wire.Resolve(ip), IPAddress: ip, Version: version(v1, v2, v3)}
	return n, nil
}

// INotifierList mirrors INotifier.get_list: count-prefixed (uint32) list.
func INotifierList(r *wire.Reader) ([]INotifier, error) {
	count, err := r.U32()
	if err != nil {
		return nil, wrap("INotifier", err)
	}
	notifiers := make([]INotifier, 0, count)
	for i := uint32(0); i < count; i++ {
		n, err := INotifierFromBuffer(r)
		if err != nil {
			return nil, err
		}
		n.ID = len(notifiers) + 1
		notifiers = append(notifiers, n)
	}
	return notifiers, nil
}
