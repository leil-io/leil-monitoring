package leilfs

import (
	"bytes"
	"encoding/binary"
	"fmt"
	"net"
	"testing"
	"time"

	"github.com/leil-io/saunafs-monitoring/go/leilfs/internal/wire"
)

// --- mock net.Conn + scripted dialer --------------------------------------

type mockConn struct {
	read  *bytes.Reader
	write bytes.Buffer
}

func (m *mockConn) Read(p []byte) (int, error)         { return m.read.Read(p) }
func (m *mockConn) Write(p []byte) (int, error)        { return m.write.Write(p) }
func (m *mockConn) Close() error                       { return nil }
func (m *mockConn) LocalAddr() net.Addr                { return dummyAddr{} }
func (m *mockConn) RemoteAddr() net.Addr               { return dummyAddr{} }
func (m *mockConn) SetDeadline(t time.Time) error      { return nil }
func (m *mockConn) SetReadDeadline(t time.Time) error  { return nil }
func (m *mockConn) SetWriteDeadline(t time.Time) error { return nil }

type dummyAddr struct{}

func (dummyAddr) Network() string { return "tcp" }
func (dummyAddr) String() string  { return "mock" }

type scriptDialer struct {
	frames [][]byte
	idx    int
	dialed int
}

func (s *scriptDialer) dial(host string, port int) (net.Conn, error) {
	s.dialed++
	if s.idx >= len(s.frames) {
		return nil, fmt.Errorf("no more scripted frames (idx=%d)", s.idx)
	}
	f := s.frames[s.idx]
	s.idx++
	return &mockConn{read: bytes.NewReader(f)}, nil
}

// --- frame + payload builders ---------------------------------------------

func frameV1(respCmd uint32, payload []byte) []byte {
	b := make([]byte, 8+len(payload))
	binary.BigEndian.PutUint32(b[0:], respCmd)
	binary.BigEndian.PutUint32(b[4:], uint32(len(payload)))
	copy(b[8:], payload)
	return b
}

func frameV2(respCmd, version uint32, payload []byte) []byte {
	full := make([]byte, 4+len(payload))
	binary.BigEndian.PutUint32(full[0:], version)
	copy(full[4:], payload)
	return frameV1(respCmd, full)
}

type bw struct{ b bytes.Buffer }

func (x *bw) u8(v uint8)   { x.b.WriteByte(v) }
func (x *bw) u16(v uint16) { binary.Write(&x.b, binary.BigEndian, v) }
func (x *bw) u32(v uint32) { binary.Write(&x.b, binary.BigEndian, v) }
func (x *bw) u64(v uint64) { binary.Write(&x.b, binary.BigEndian, v) }
func (x *bw) raw(p []byte) { x.b.Write(p) }
func (x *bw) out() []byte  { return x.b.Bytes() }

// versionPayload mirrors _mock_initial_version_response (V1, >HBB).
func versionPayload(v1 uint16, v2, v3 uint8) []byte {
	w := &bw{}
	w.u16(v1)
	w.u8(v2)
	w.u8(v3)
	return w.out()
}

func systemInfoPayload() []byte {
	w := &bw{}
	w.u16(2) // version major
	w.u8(5)  // minor
	w.u8(1)  // patch
	w.u64(1000)
	w.u64(5000)
	w.u64(3000)
	w.u64(100)
	w.u32(5)
	w.u64(50)
	w.u32(2)
	w.u32(200)
	w.u32(20)
	w.u32(150)
	w.u32(10)
	w.u32(300)
	w.u32(600)
	w.u32(550)
	return w.out()
}

func serverEntry(disconnected uint8, ip string, port uint16, label string) []byte {
	w := &bw{}
	w.u8(disconnected)
	w.u8(1) // version 1.2.3
	w.u8(2)
	w.u8(3)
	for _, oct := range parseOctets(ip) {
		w.u8(oct)
	}
	w.u16(port)
	w.u64(1000) // used
	w.u64(2000) // total
	w.u32(50)   // chunks
	w.u64(10)   // tdused
	w.u64(20)   // tdtotal
	w.u32(1)    // tdchunks
	w.u32(0)    // errcnt
	lbl := append([]byte(label), 0)
	w.u32(uint32(len(lbl))) // label length includes NUL
	w.raw(lbl)
	return w.out()
}

func serversPayload(entries ...[]byte) []byte {
	w := &bw{}
	w.u32(uint32(len(entries)))
	for _, e := range entries {
		w.raw(e)
	}
	return w.out()
}

func diskEntry(path string, used, total uint64, chunks uint32, flags uint8) []byte {
	inner := &bw{}
	inner.u8(uint8(len(path)))
	inner.raw([]byte(path))
	inner.u8(flags)
	inner.u64(0)      // err_chunk_id
	inner.u32(0)      // err_time
	inner.u64(used)   // used
	inner.u64(total)  // total
	inner.u32(chunks) // chunks
	for s := 0; s < 3; s++ {
		for q := 0; q < 5; q++ {
			inner.u64(0)
		}
		for l := 0; l < 6; l++ {
			inner.u32(0)
		}
	}
	body := inner.out()
	w := &bw{}
	w.u16(uint16(len(body)))
	w.raw(body)
	return w.out()
}

func parseOctets(ip string) []uint8 {
	p := net.ParseIP(ip).To4()
	return []uint8{p[0], p[1], p[2], p[3]}
}

func withResolver(t *testing.T, m map[string]string) {
	t.Helper()
	orig := wire.Resolve
	wire.Resolve = func(ip string) string {
		if h, ok := m[ip]; ok {
			return h
		}
		return "(unresolved)"
	}
	t.Cleanup(func() { wire.Resolve = orig })
}

// --- tests ----------------------------------------------------------------

func TestGetMasterVersionSuccess(t *testing.T) {
	d := &scriptDialer{frames: [][]byte{frameV1(511, versionPayload(2, 5, 1))}}
	c := NewClientWithDial("master", 9421, d.dial)
	if got := c.MasterVersion(); got != [3]int{2, 5, 1} {
		t.Fatalf("version = %v, want {2 5 1}", got)
	}
}

func TestGetMasterVersionConnectionError(t *testing.T) {
	dial := func(host string, port int) (net.Conn, error) { return nil, fmt.Errorf("refused") }
	c := NewClientWithDial("master", 9421, dial)
	if got := c.MasterVersion(); got != [3]int{0, 0, 0} {
		t.Fatalf("version = %v, want {0 0 0}", got)
	}
}

func TestGetSystemInfoSuccess(t *testing.T) {
	d := &scriptDialer{frames: [][]byte{
		frameV1(511, versionPayload(2, 5, 1)), // constructor probe
		frameV1(511, systemInfoPayload()),     // GetInfo
	}}
	c := NewClientWithDial("master", 9421, d.dial)
	info, err := c.GetInfo()
	if err != nil {
		t.Fatalf("GetInfo: %v", err)
	}
	if info.Version != "2.5.1" {
		t.Errorf("version = %q, want 2.5.1", info.Version)
	}
	if info.TotalSpace != 5000 || info.AvailSpace != 3000 || info.Chunks != 300 {
		t.Errorf("unexpected SystemInfo: %+v", info)
	}
}

func TestGetSystemInfoWrongResponse(t *testing.T) {
	d := &scriptDialer{frames: [][]byte{
		frameV1(511, versionPayload(2, 5, 1)),
		frameV1(999, systemInfoPayload()), // wrong response command
	}}
	c := NewClientWithDial("master", 9421, d.dial)
	if _, err := c.GetInfo(); err == nil {
		t.Fatal("expected error for wrong response command")
	}
}

func TestGetChartSuccess(t *testing.T) {
	gif := []byte("GIF89a-some-bytes")
	d := &scriptDialer{frames: [][]byte{
		frameV1(511, versionPayload(2, 5, 1)), // constructor
		frameV1(505, gif),                     // chart
	}}
	c := NewClientWithDial("master", 9421, d.dial)
	out, err := c.GetChart("10.0.0.5", 9425, 42)
	if err != nil {
		t.Fatalf("GetChart: %v", err)
	}
	if !bytes.Equal(out, gif) {
		t.Errorf("chart bytes = %q, want %q", out, gif)
	}
	if d.dialed != 2 {
		t.Errorf("dialed %d times, want 2", d.dialed)
	}
}

func TestGetServersSuccess(t *testing.T) {
	withResolver(t, map[string]string{
		"10.0.0.1": "host-one.local",
		"10.0.0.2": "host-two.local",
	})
	payload := serversPayload(
		serverEntry(1, "10.0.0.2", 9422, "ssd"), // disconnected, out of order
		serverEntry(0, "10.0.0.1", 9422, "hdd"),
	)
	d := &scriptDialer{frames: [][]byte{
		frameV1(511, versionPayload(2, 5, 1)),
		frameV2(1550, 0, payload),
	}}
	c := NewClientWithDial("master", 9421, d.dial)
	servers, err := c.GetServers()
	if err != nil {
		t.Fatalf("GetServers: %v", err)
	}
	if len(servers) != 2 {
		t.Fatalf("got %d servers, want 2", len(servers))
	}
	// Sorted by hostname: host-one first.
	if servers[0].Hostname != "host-one.local" || servers[0].IsDisconnected {
		t.Errorf("servers[0] = %+v", servers[0])
	}
	if servers[0].Label != "hdd" || servers[0].Port != 9422 {
		t.Errorf("servers[0] label/port = %q/%d", servers[0].Label, servers[0].Port)
	}
	if servers[1].Hostname != "host-two.local" || !servers[1].IsDisconnected {
		t.Errorf("servers[1] = %+v", servers[1])
	}
	if servers[0].ID == servers[1].ID {
		t.Errorf("ids not assigned distinctly: %d %d", servers[0].ID, servers[1].ID)
	}
}

func TestGetDisksSuccess(t *testing.T) {
	withResolver(t, map[string]string{
		"10.0.0.1": "host-one.local",
		"10.0.0.2": "host-two.local",
	})
	servers := serversPayload(
		serverEntry(0, "10.0.0.1", 9422, "hdd"), // connected
		serverEntry(1, "10.0.0.2", 9422, "ssd"), // disconnected -> skipped
	)
	disks := diskEntry("/mnt/disk1", 2000, 4000, 200, 0)
	d := &scriptDialer{frames: [][]byte{
		frameV1(511, versionPayload(2, 5, 1)), // constructor
		frameV2(1550, 0, servers),             // GetServers (inside GetDisks)
		frameV1(601, disks),                   // HDD list for the connected server
	}}
	c := NewClientWithDial("master", 9421, d.dial)
	got, err := c.GetDisks()
	if err != nil {
		t.Fatalf("GetDisks: %v", err)
	}
	if len(got) != 1 {
		t.Fatalf("got %d disks, want 1", len(got))
	}
	if got[0].Path != "host-one.local:/mnt/disk1" {
		t.Errorf("path = %q", got[0].Path)
	}
	if got[0].TotalSpace != 4000 || got[0].UsedSpace != 2000 || got[0].Chunks != 200 {
		t.Errorf("unexpected disk: %+v", got[0])
	}
	if got[0].Status != "OK" {
		t.Errorf("status = %q, want OK", got[0].Status)
	}
}
