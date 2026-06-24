package apiclient_test

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/leil-io/saunafs-monitoring/go/internal/apiclient"
)

// stub spins up a fake leilfs-api that returns the given body for the given
// path (query string ignored), and 404 otherwise.
func stub(t *testing.T, path, body string) *apiclient.Client {
	t.Helper()
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != path {
			http.Error(w, `{"error":{"code":"not_found","message":"no"}}`, http.StatusNotFound)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(body))
	}))
	t.Cleanup(srv.Close)
	return apiclient.New(srv.URL, true)
}

// captureQuery spins up a server that records the RawQuery of the first request
// and always answers with an empty JSON array, so the resolve-gating tests can
// assert which query parameters the client sends.
func captureQuery(t *testing.T, resolve bool) (*apiclient.Client, *string) {
	t.Helper()
	got := new(string)
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		*got = r.URL.RawQuery
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`[]`))
	}))
	t.Cleanup(srv.Close)
	return apiclient.New(srv.URL, resolve), got
}

func TestResolveDisabledOmitsResolveParam(t *testing.T) {
	c, q := captureQuery(t, false)
	if _, err := c.GetServers(); err != nil {
		t.Fatal(err)
	}
	if strings.Contains(*q, "resolve=true") {
		t.Errorf("query %q must not carry resolve=true when resolution is disabled", *q)
	}
}

func TestResolveEnabledAddsResolveParam(t *testing.T) {
	c, q := captureQuery(t, true)
	if _, err := c.GetServers(); err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(*q, "resolve=true") {
		t.Errorf("query %q must carry resolve=true when resolution is enabled", *q)
	}
}

// disks already passes verbose=true; gating resolve must keep verbose and append
// resolve with the correct separator rather than clobbering the query.
func TestDisksKeepsVerboseAndGatesResolve(t *testing.T) {
	off, qOff := captureQuery(t, false)
	if _, err := off.GetDisks(); err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(*qOff, "verbose=true") || strings.Contains(*qOff, "resolve=true") {
		t.Errorf("disks query %q: want verbose=true, no resolve=true", *qOff)
	}

	on, qOn := captureQuery(t, true)
	if _, err := on.GetDisks(); err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(*qOn, "verbose=true") || !strings.Contains(*qOn, "resolve=true") {
		t.Errorf("disks query %q: want both verbose=true and resolve=true", *qOn)
	}
}

func TestGetInfoMapping(t *testing.T) {
	c := stub(t, "/api/v1/cluster", `{
		"version":"5.11.0","memoryUsedBytes":208441344,"totalSpaceBytes":1026108821504,
		"availableSpaceBytes":984373452800,"trashSpaceBytes":1,"trashFiles":2,
		"reservedSpaceBytes":3,"reservedFiles":4,"totalObjects":5,"directories":2,
		"files":3,"symlinks":0,"chunks":7,"allCopies":8,"regularCopies":9}`)
	got, err := c.GetInfo()
	if err != nil {
		t.Fatal(err)
	}
	if got.Version != "5.11.0" {
		t.Errorf("version = %q", got.Version)
	}
	if got.RAMUsed != 208441344 || got.TotalSpace != 1026108821504 || got.AvailSpace != 984373452800 {
		t.Errorf("space mapping wrong: %+v", got)
	}
	if got.TrashFiles != 2 || got.ReservedFiles != 4 || got.TotalObjects != 5 || got.Chunks != 7 {
		t.Errorf("count narrowing wrong: %+v", got)
	}
}

func TestGetServersInvertsConnected(t *testing.T) {
	c := stub(t, "/api/v1/chunkservers", `[
		{"id":1,"ip":"10.0.0.1","port":9422,"hostname":"cs1","version":"5.11.0","connected":true,
		 "label":"_","usedSpaceBytes":10,"totalSpaceBytes":100,"chunks":3,
		 "usedSpaceToDeleteBytes":1,"totalSpaceToDeleteBytes":2,"chunksToDelete":4,"errorCount":5},
		{"id":2,"ip":"10.0.0.2","port":9422,"connected":false,"version":"5.11.0"}]`)
	got, err := c.GetServers()
	if err != nil {
		t.Fatal(err)
	}
	if len(got) != 2 {
		t.Fatalf("len = %d", len(got))
	}
	if got[0].IsDisconnected {
		t.Error("connected:true should map to is_disconnected:false")
	}
	if got[0].IPAddress != "10.0.0.1" || got[0].Hostname != "cs1" || got[0].UsedSpace != 10 || got[0].ChunksTobedeleted != 4 {
		t.Errorf("server[0] mapping wrong: %+v", got[0])
	}
	if !got[1].IsDisconnected {
		t.Error("connected:false should map to is_disconnected:true")
	}
}

func TestGetDisksReconstructsStatusAndPath(t *testing.T) {
	// A damaged disk with a last error, plus an ok disk with no error. Derived
	// stats (verbose) are present and must pass through.
	c := stub(t, "/api/v1/disks", `[
		{"chunkserver":"cs1","path":"/mnt/a","flags":2,
		 "lastError":{"chunkId":99,"timestamp":1700000000},
		 "totalSpaceBytes":100,"usedSpaceBytes":10,"chunks":1,
		 "stats":{"minute":{"readBytes":1024,"readOps":2,"readBlockSizeAvg":512},"hour":{},"day":{}}},
		{"chunkserver":"cs1","path":"/mnt/b","flags":0,"lastError":null,
		 "totalSpaceBytes":1,"usedSpaceBytes":0,"chunks":0,"stats":{"minute":{},"hour":{},"day":{}}}]`)
	got, err := c.GetDisks()
	if err != nil {
		t.Fatal(err)
	}
	if got[0].Path != "cs1:/mnt/a" {
		t.Errorf("path = %q, want cs1:/mnt/a", got[0].Path)
	}
	if got[0].Status != "Damaged" {
		t.Errorf("status = %q, want Damaged", got[0].Status)
	}
	if got[0].LastError != "1700000000 on chunk: 99" {
		t.Errorf("last_error = %q", got[0].LastError)
	}
	if got[0].MinuteStats.ReadBytes != 1024 || got[0].MinuteStats.ReadOps != 2 || got[0].MinuteStats.ReadBlockSizeAvg != 512 {
		t.Errorf("minute stats mapping wrong: %+v", got[0].MinuteStats)
	}
	if got[1].Status != "OK" || got[1].LastError != "No errors" {
		t.Errorf("ok disk: status=%q last_error=%q", got[1].Status, got[1].LastError)
	}
}

func TestGetExportsJoinsFlags(t *testing.T) {
	c := stub(t, "/api/v1/exports", `[
		{"id":1,"ipFrom":"0.0.0.0","ipTo":"255.255.255.255","path":"/","flags":["ro","map_all"]}]`)
	got, err := c.GetExports()
	if err != nil {
		t.Fatal(err)
	}
	if got[0].Flags != "ro, map_all" {
		t.Errorf("flags = %q, want 'ro, map_all'", got[0].Flags)
	}
}

func TestGetMountsMapsPointersAndStats(t *testing.T) {
	c := stub(t, "/api/v1/mounts", `[
		{"id":1,"sessionId":6,"ip":"10.0.0.9","hostname":"h","version":"5.11.0",
		 "rootPath":"/r","mountedPath":"/m","mountInfo":"x","flags":["ro"],
		 "rootUid":1,"rootGid":2,"mapAllUid":3,"mapAllGid":4,
		 "minGoal":1,"maxGoal":9,"minTrashTime":0,"maxTrashTime":4294967295,
		 "currentOpStats":{"statfs":7,"read":8,"total":15},
		 "lastHourOpStats":{"write":1,"total":1}}]`)
	got, err := c.GetMounts()
	if err != nil {
		t.Fatal(err)
	}
	m := got[0]
	if m.Flags != "ro" {
		t.Errorf("flags = %q", m.Flags)
	}
	if m.MinGoal == nil || *m.MinGoal != 1 || m.MaxTrashTime == nil || *m.MaxTrashTime != 4294967295 {
		t.Errorf("nullable goal/trash mapping wrong: %+v", m)
	}
	if m.CurrentOpStats == nil || m.CurrentOpStats.Statfs != 7 || m.CurrentOpStats.Read != 8 || m.CurrentOpStats.Total != 15 {
		t.Errorf("current op stats wrong: %+v", m.CurrentOpStats)
	}
}

func TestGetChunkHealthFoldsIntoMaps(t *testing.T) {
	c := stub(t, "/api/v1/cluster/chunk-health", `{
		"regularOnly":true,
		"goals":[
			{"goalId":2,"safe":5,"endangered":1,"lost":0,
			 "replication":[1,2,3,4,5,6,7,8,9,10,11],"deletion":[0,0,0,0,0,0,0,0,0,0,0]}]}`)
	got, err := c.GetChunkHealth()
	if err != nil {
		t.Fatal(err)
	}
	if !got.RegularOnly {
		t.Error("regular_only not mapped")
	}
	if got.Safe[2] != 5 || got.Endangered[2] != 1 || got.Lost[2] != 0 {
		t.Errorf("safe/endangered/lost maps wrong: %+v", got)
	}
	if len(got.Replication[2]) != 11 || got.Replication[2][10] != 11 {
		t.Errorf("replication vector wrong: %v", got.Replication[2])
	}
}

func TestErrorEnvelopeBecomesError(t *testing.T) {
	c := stub(t, "/api/v1/cluster", `{}`) // any other path 404s with an envelope
	_, err := c.GetServers()              // hits /api/v1/chunkservers -> 404
	if err == nil {
		t.Fatal("expected an error from a non-200 response")
	}
	if !strings.Contains(err.Error(), "not_found") {
		t.Errorf("error %q should carry the envelope code", err)
	}
}
