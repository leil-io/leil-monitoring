package httpapi_test

import (
	"bytes"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"net"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/leil-io/saunafs-monitoring/go/internal/httpapi"
	"github.com/leil-io/saunafs-monitoring/go/leilfs"
)

// minimal scripted dialer (mirrors the one in the proto tests) ---------------

type mockConn struct {
	read  *bytes.Reader
	write bytes.Buffer
}

func (m *mockConn) Read(p []byte) (int, error)         { return m.read.Read(p) }
func (m *mockConn) Write(p []byte) (int, error)        { return m.write.Write(p) }
func (m *mockConn) Close() error                       { return nil }
func (m *mockConn) LocalAddr() net.Addr                { return mockAddr{} }
func (m *mockConn) RemoteAddr() net.Addr               { return mockAddr{} }
func (m *mockConn) SetDeadline(t time.Time) error      { return nil }
func (m *mockConn) SetReadDeadline(t time.Time) error  { return nil }
func (m *mockConn) SetWriteDeadline(t time.Time) error { return nil }

type mockAddr struct{}

func (mockAddr) Network() string { return "tcp" }
func (mockAddr) String() string  { return "mock" }

func frameV1(respCmd uint32, payload []byte) []byte {
	b := make([]byte, 8+len(payload))
	binary.BigEndian.PutUint32(b[0:], respCmd)
	binary.BigEndian.PutUint32(b[4:], uint32(len(payload)))
	copy(b[8:], payload)
	return b
}

func systemInfoPayload() []byte {
	var b bytes.Buffer
	binary.Write(&b, binary.BigEndian, uint16(2)) // major
	b.WriteByte(5)                                // minor
	b.WriteByte(1)                                // patch
	for _, v := range []uint64{1000, 5000, 3000, 100} {
		binary.Write(&b, binary.BigEndian, v)
	}
	binary.Write(&b, binary.BigEndian, uint32(5)) // trash_files
	binary.Write(&b, binary.BigEndian, uint64(50))
	for _, v := range []uint32{2, 200, 20, 150, 10, 300, 600, 550} {
		binary.Write(&b, binary.BigEndian, v)
	}
	return b.Bytes()
}

// dialerFactory returns a ClientFactory whose clients replay the given frames.
func dialerFactory(frames [][]byte) httpapi.ClientFactory {
	return func(host string, port int) *leilfs.Client {
		idx := 0
		dial := func(h string, p int) (net.Conn, error) {
			if idx >= len(frames) {
				return nil, fmt.Errorf("no more frames")
			}
			f := frames[idx]
			idx++
			return &mockConn{read: bytes.NewReader(f)}, nil
		}
		return leilfs.NewClientWithDial(host, port, dial)
	}
}

func testConfig() httpapi.Config {
	return httpapi.Config{MasterHost: "127.0.0.1", MasterPort: 9421, Host: "0.0.0.0", Port: 8001}
}

func TestRootRedirectsToDocs(t *testing.T) {
	h := httpapi.NewRouterWithClient(testConfig(), dialerFactory(nil))
	req := httptest.NewRequest(http.MethodGet, "/", nil)
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)

	if rec.Code != http.StatusTemporaryRedirect {
		t.Fatalf("status = %d, want 307", rec.Code)
	}
	if loc := rec.Header().Get("Location"); loc != "/docs" {
		t.Fatalf("Location = %q, want /docs", loc)
	}
}

func TestInfoEndpoint(t *testing.T) {
	frames := [][]byte{
		frameV1(511, systemInfoPayload()[:4]), // constructor version probe
		frameV1(511, systemInfoPayload()),     // GetInfo
	}
	h := httpapi.NewRouterWithClient(testConfig(), dialerFactory(frames))
	req := httptest.NewRequest(http.MethodGet, "/api/info", nil)
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200 (body=%s)", rec.Code, rec.Body.String())
	}
	var got map[string]any
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if got["version"] != "2.5.1" {
		t.Errorf("version = %v, want 2.5.1", got["version"])
	}
	if got["total_space"].(float64) != 5000 {
		t.Errorf("total_space = %v, want 5000", got["total_space"])
	}
}

// recordingFactory captures the host/port a built client targets, and replays
// optional frames so the call can still complete.
func recordingFactory(frames [][]byte, gotHost *string, gotPort *int) httpapi.ClientFactory {
	return func(host string, port int) *leilfs.Client {
		*gotHost, *gotPort = host, port
		idx := 0
		dial := func(string, int) (net.Conn, error) {
			if idx >= len(frames) {
				return nil, fmt.Errorf("no more frames")
			}
			f := frames[idx]
			idx++
			return &mockConn{read: bytes.NewReader(f)}, nil
		}
		return leilfs.NewClientWithDial(host, port, dial)
	}
}

// TestDataIgnoresMasterQuery: in the single-cluster model the binary data path
// uses the configured master and ignores the SPA's ?masterhost/?masterport.
func TestDataIgnoresMasterQuery(t *testing.T) {
	var gotHost string
	var gotPort int
	frames := [][]byte{
		frameV1(511, systemInfoPayload()[:4]), // version probe
		frameV1(511, systemInfoPayload()),     // GetInfo
	}
	h := httpapi.NewRouterWithClient(testConfig(), recordingFactory(frames, &gotHost, &gotPort))
	req := httptest.NewRequest(http.MethodGet, "/api/info?masterhost=evil.example&masterport=1", nil)
	h.ServeHTTP(httptest.NewRecorder(), req)
	if gotHost != "127.0.0.1" || gotPort != 9421 {
		t.Fatalf("data dialed %s:%d, want configured 127.0.0.1:9421 (query must be ignored)", gotHost, gotPort)
	}
}

// TestChartHostRouting: the legacy "sfsmaster" placeholder routes master charts
// to the configured master, while an explicit chunkserver host is honored.
func TestChartHostRouting(t *testing.T) {
	var gotHost string
	var gotPort int
	// No frames needed: we only assert the target the chart client is built with.
	h := httpapi.NewRouterWithClient(testConfig(), recordingFactory(nil, &gotHost, &gotPort))

	h.ServeHTTP(httptest.NewRecorder(),
		httptest.NewRequest(http.MethodGet, "/api/cgicharts?id=90200&host=sfsmaster&port=9421", nil))
	if gotHost != "127.0.0.1" || gotPort != 9421 {
		t.Fatalf("master chart dialed %s:%d, want configured 127.0.0.1:9421", gotHost, gotPort)
	}

	h.ServeHTTP(httptest.NewRecorder(),
		httptest.NewRequest(http.MethodGet, "/api/cgicharts?id=91000&host=10.0.0.5&port=9422", nil))
	if gotHost != "10.0.0.5" || gotPort != 9422 {
		t.Fatalf("server chart dialed %s:%d, want explicit 10.0.0.5:9422", gotHost, gotPort)
	}
}
