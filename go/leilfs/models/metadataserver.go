package models

import (
	"encoding/binary"
	"fmt"
	"net"

	"github.com/leil-io/saunafs-monitoring/go/leilfs/internal/wire"
)

// MetadataServer mirrors models.MetadataServer.
type MetadataServer struct {
	ID              int    `json:"id"`
	Hostname        string `json:"hostname"`
	IPAddress       string `json:"ip_address"`
	Port            uint16 `json:"port"`
	Version         string `json:"version"`
	Personality     string `json:"personality"`
	State           string `json:"state"`
	MetadataVersion int64  `json:"metadata_version"`
}

// MetadataServerFromBuffer mirrors from_buffer (">LHHBB").
func MetadataServerFromBuffer(r *wire.Reader) (MetadataServer, error) {
	var m MetadataServer
	ip, err := r.U32()
	if err != nil {
		return m, wrap("MetadataServer", err)
	}
	port, err := r.U16()
	if err != nil {
		return m, wrap("MetadataServer", err)
	}
	v1, err := r.U16()
	if err != nil {
		return m, wrap("MetadataServer", err)
	}
	v2, err := r.U8()
	if err != nil {
		return m, wrap("MetadataServer", err)
	}
	v3, err := r.U8()
	if err != nil {
		return m, wrap("MetadataServer", err)
	}

	var ipBytes [4]byte
	binary.BigEndian.PutUint32(ipBytes[:], ip)
	m = MetadataServer{
		IPAddress:       net.IP(ipBytes[:]).String(),
		Port:            port,
		Version:         version(v1, v2, v3),
		MetadataVersion: -1,
	}
	return m, nil
}

// ApplyStatus mirrors status_from_buffer (">LBQ"): msgid, status, metadata_version.
func (m *MetadataServer) ApplyStatus(buf []byte) error {
	if len(buf) < 13 {
		return &wire.Error{Msg: fmt.Sprintf("MetadataServer status buffer too short: %d", len(buf))}
	}
	status := buf[4]
	m.MetadataVersion = int64(binary.BigEndian.Uint64(buf[5:13]))
	switch status {
	case 1:
		m.Personality, m.State = "master", "running"
	case 2:
		m.Personality, m.State = "shadow", "connected"
	case 3:
		m.Personality, m.State = "shadow", "disconnected"
	default:
		m.Personality = fmt.Sprintf("(unknown: code %d)", status)
		m.State = fmt.Sprintf("(unknown: code %d)", status)
	}
	return nil
}

// MetadataServerList mirrors get_list: master_version(uint32, skipped) +
// vector_size(uint32) + entries, ids assigned i+2 (master is id 1).
func MetadataServerList(r *wire.Reader) ([]MetadataServer, error) {
	if _, err := r.U32(); err != nil { // master_version, unused
		return nil, wrap("MetadataServer", err)
	}
	vectorSize, err := r.U32()
	if err != nil {
		return nil, wrap("MetadataServer", err)
	}
	servers := make([]MetadataServer, 0, vectorSize)
	for i := uint32(0); i < vectorSize; i++ {
		s, err := MetadataServerFromBuffer(r)
		if err != nil {
			return nil, err
		}
		s.ID = int(i) + 2
		servers = append(servers, s)
	}
	return servers, nil
}
