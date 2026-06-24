// Package apiclient adapts the leilfs-api HTTP service (the canonical LeilFS
// Unified API, github.com/leil-io/leilfs-api) to the data-source interface the
// monitoring's JSON layer expects.
//
// It fetches the new /api/v1/* endpoints and maps their (camelCase, cleaned-up)
// responses back into the legacy leilfs/models.* shapes, so the existing HTTP
// handlers and the Preact SPA keep working byte-compatibly. This replaces the
// in-process binary-protocol client (leilfs.Client) as the data source when
// LEILFS_API_URL is configured; the binary client remains the fallback and is
// still used for charts (which leilfs-api does not expose).
//
// Mapping notes (new -> legacy):
//   - is_disconnected = !connected
//   - disk status/last_error strings are reconstructed from the raw `flags`
//     byte and structured lastError using the legacy rendering rules
//   - disk path is prefixed with "<chunkserver>:" as the legacy client did
//   - mount/export flags arrays are joined with ", "
//   - chunk-health per-goal entries are folded back into the int-keyed maps
//   - hostname-bearing endpoints are requested with ?resolve=true so names show
package apiclient

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/leil-io/saunafs-monitoring/go/leilfs/models"
)

// Client talks to a leilfs-api instance over HTTP.
type Client struct {
	baseURL string
	http    *http.Client
}

// New returns a Client targeting the given leilfs-api base URL (e.g.
// "http://leilfs-api:8080"). A trailing slash is tolerated.
func New(baseURL string) *Client {
	return &Client{
		baseURL: strings.TrimRight(baseURL, "/"),
		http:    &http.Client{Timeout: 30 * time.Second},
	}
}

// get fetches path and decodes a 200 JSON body into dest. A non-200 response is
// turned into an error carrying the leilfs-api error envelope (§6.1), which the
// HTTP layer maps to a 500 just like the legacy client's errors.
func (c *Client) get(path string, dest any) error {
	res, err := c.http.Get(c.baseURL + path)
	if err != nil {
		return err
	}
	defer res.Body.Close()
	body, err := io.ReadAll(res.Body)
	if err != nil {
		return err
	}
	if res.StatusCode != http.StatusOK {
		return fmt.Errorf("leilfs-api GET %s: %s (%s)", path, res.Status, errMessage(body))
	}
	return json.Unmarshal(body, dest)
}

// errMessage extracts "code: message" from a leilfs-api error envelope, falling
// back to the raw body.
func errMessage(body []byte) string {
	var env struct {
		Error struct {
			Code    string `json:"code"`
			Message string `json:"message"`
		} `json:"error"`
	}
	if json.Unmarshal(body, &env) == nil && env.Error.Code != "" {
		return env.Error.Code + ": " + env.Error.Message
	}
	return strings.TrimSpace(string(body))
}

func deref(p *float64) float64 {
	if p != nil {
		return *p
	}
	return 0
}

// --- GET /cluster -> SystemInfo -------------------------------------------

type clusterSummaryDTO struct {
	Version             string `json:"version"`
	MemoryUsedBytes     uint64 `json:"memoryUsedBytes"`
	TotalSpaceBytes     uint64 `json:"totalSpaceBytes"`
	AvailableSpaceBytes uint64 `json:"availableSpaceBytes"`
	TrashSpaceBytes     uint64 `json:"trashSpaceBytes"`
	TrashFiles          uint64 `json:"trashFiles"`
	ReservedSpaceBytes  uint64 `json:"reservedSpaceBytes"`
	ReservedFiles       uint64 `json:"reservedFiles"`
	TotalObjects        uint64 `json:"totalObjects"`
	Directories         uint64 `json:"directories"`
	Files               uint64 `json:"files"`
	Symlinks            uint64 `json:"symlinks"`
	Chunks              uint64 `json:"chunks"`
	AllCopies           uint64 `json:"allCopies"`
	RegularCopies       uint64 `json:"regularCopies"`
}

func (c *Client) GetInfo() (models.SystemInfo, error) {
	var d clusterSummaryDTO
	if err := c.get("/api/v1/cluster", &d); err != nil {
		return models.SystemInfo{}, err
	}
	// The widened counts are u32-range on the wire; narrow them back.
	return models.SystemInfo{
		Version:       d.Version,
		RAMUsed:       d.MemoryUsedBytes,
		TotalSpace:    d.TotalSpaceBytes,
		AvailSpace:    d.AvailableSpaceBytes,
		TrashSpace:    d.TrashSpaceBytes,
		TrashFiles:    uint32(d.TrashFiles),
		ReservedSpace: d.ReservedSpaceBytes,
		ReservedFiles: uint32(d.ReservedFiles),
		TotalObjects:  uint32(d.TotalObjects),
		Directories:   uint32(d.Directories),
		Files:         uint32(d.Files),
		Symlinks:      uint32(d.Symlinks),
		Chunks:        uint32(d.Chunks),
		AllCopies:     uint32(d.AllCopies),
		RegularCopies: uint32(d.RegularCopies),
	}, nil
}

// --- GET /chunkservers -> []Server ----------------------------------------

type chunkserverDTO struct {
	ID                      uint32 `json:"id"`
	IP                      string `json:"ip"`
	Port                    uint16 `json:"port"`
	Hostname                string `json:"hostname"`
	Version                 string `json:"version"`
	Connected               bool   `json:"connected"`
	Label                   string `json:"label"`
	UsedSpaceBytes          uint64 `json:"usedSpaceBytes"`
	TotalSpaceBytes         uint64 `json:"totalSpaceBytes"`
	Chunks                  uint64 `json:"chunks"`
	UsedSpaceToDeleteBytes  uint64 `json:"usedSpaceToDeleteBytes"`
	TotalSpaceToDeleteBytes uint64 `json:"totalSpaceToDeleteBytes"`
	ChunksToDelete          uint64 `json:"chunksToDelete"`
	ErrorCount              uint32 `json:"errorCount"`
}

func (c *Client) GetServers() ([]models.Server, error) {
	var ds []chunkserverDTO
	if err := c.get("/api/v1/chunkservers?resolve=true", &ds); err != nil {
		return nil, err
	}
	out := make([]models.Server, 0, len(ds))
	for _, d := range ds {
		out = append(out, models.Server{
			ID:                    int(d.ID),
			Hostname:              d.Hostname,
			IPAddress:             d.IP,
			Port:                  d.Port,
			Version:               d.Version,
			IsDisconnected:        !d.Connected,
			Label:                 d.Label,
			UsedSpace:             d.UsedSpaceBytes,
			TotalSpace:            d.TotalSpaceBytes,
			Chunks:                uint32(d.Chunks),
			UsedSpaceTobedeleted:  d.UsedSpaceToDeleteBytes,
			TotalSpaceTobedeleted: d.TotalSpaceToDeleteBytes,
			ChunksTobedeleted:     uint32(d.ChunksToDelete),
			ErrorCount:            d.ErrorCount,
		})
	}
	return out, nil
}

// --- GET /disks -> []Disk --------------------------------------------------

type diskStatsDTO struct {
	ReadBytes    uint64 `json:"readBytes"`
	ReadOps      uint64 `json:"readOps"`
	ReadUsec     uint64 `json:"readUsec"`
	ReadUsecMax  uint64 `json:"readUsecMax"`
	WriteBytes   uint64 `json:"writeBytes"`
	WriteOps     uint64 `json:"writeOps"`
	WriteUsec    uint64 `json:"writeUsec"`
	WriteUsecMax uint64 `json:"writeUsecMax"`
	FsyncOps     uint64 `json:"fsyncOps"`
	FsyncUsec    uint64 `json:"fsyncUsec"`
	FsyncUsecMax uint64 `json:"fsyncUsecMax"`

	ReadBytesPerSecond  *float64 `json:"readBytesPerSecond"`
	WriteBytesPerSecond *float64 `json:"writeBytesPerSecond"`
	ReadUsecAvg         *float64 `json:"readUsecAvg"`
	WriteUsecAvg        *float64 `json:"writeUsecAvg"`
	FsyncUsecAvg        *float64 `json:"fsyncUsecAvg"`
	ReadBlockSizeAvg    *float64 `json:"readBlockSizeAvg"`
	WriteBlockSizeAvg   *float64 `json:"writeBlockSizeAvg"`
}

type diskErrorDTO struct {
	ChunkID   uint64 `json:"chunkId"`
	Timestamp int64  `json:"timestamp"`
}

type diskDTO struct {
	Chunkserver     string        `json:"chunkserver"`
	Path            string        `json:"path"`
	Flags           uint8         `json:"flags"`
	LastError       *diskErrorDTO `json:"lastError"`
	TotalSpaceBytes uint64        `json:"totalSpaceBytes"`
	UsedSpaceBytes  uint64        `json:"usedSpaceBytes"`
	Chunks          uint64        `json:"chunks"`
	Stats           struct {
		Minute diskStatsDTO `json:"minute"`
		Hour   diskStatsDTO `json:"hour"`
		Day    diskStatsDTO `json:"day"`
	} `json:"stats"`
}

func mapDiskStats(d diskStatsDTO) models.DiskStats {
	return models.DiskStats{
		ReadBytes:             d.ReadBytes,
		ReadBytesPersecond:    deref(d.ReadBytesPerSecond),
		ReadOps:               uint32(d.ReadOps),
		ReadUsec:              d.ReadUsec,
		ReadUsecAvg:           deref(d.ReadUsecAvg),
		ReadUsecMax:           uint32(d.ReadUsecMax),
		ReadBlockSizeAvg:      deref(d.ReadBlockSizeAvg),
		WrittenBytes:          d.WriteBytes,
		WrittenBytesPersecond: deref(d.WriteBytesPerSecond),
		WriteOps:              uint32(d.WriteOps),
		WrittenUsec:           d.WriteUsec,
		WrittenUsecAvg:        deref(d.WriteUsecAvg),
		WrittenUsecMax:        uint32(d.WriteUsecMax),
		WrittenBlockSizeAvg:   deref(d.WriteBlockSizeAvg),
		FsyncOps:              uint32(d.FsyncOps),
		FsyncUsec:             d.FsyncUsec,
		FsyncUsecAvg:          deref(d.FsyncUsecAvg),
		FsyncUsecMax:          uint32(d.FsyncUsecMax),
	}
}

// diskStatusAndError reproduces the legacy status/last_error strings from the
// raw flags byte and the structured last error (leilfs/models/disk.go).
func diskStatusAndError(flags uint8, lastErr *diskErrorDTO) (status, lastError string) {
	const defaultStatus = "OK"
	status = defaultStatus
	switch {
	case flags&0x1 != 0:
		status = "Marked for removal"
	case flags&0x2 != 0:
		status = "Damaged"
	case flags&0x3 != 0:
		status = "Damaged, marked for removal"
	case flags&0x6 != 0 || flags&0x4 != 0:
		status = "Scanning"
	case flags&0x7 != 0 || flags&0x5 != 0:
		status = "Scanning, marked for removal"
	}

	var errChunkID uint64
	var errTime uint32
	if lastErr != nil {
		errChunkID = lastErr.ChunkID
		errTime = uint32(lastErr.Timestamp)
	}
	lastError = "No errors"
	if errTime > 0 {
		lastError = fmt.Sprintf("%d on chunk: %d", errTime, errChunkID)
		if status == defaultStatus {
			status = "Errors reported"
		}
	} else if flags&0x2 != 0 {
		lastError = "Read/Write error"
	}
	return status, lastError
}

func (c *Client) GetDisks() ([]models.Disk, error) {
	var ds []diskDTO
	if err := c.get("/api/v1/disks?verbose=true&resolve=true", &ds); err != nil {
		return nil, err
	}
	out := make([]models.Disk, 0, len(ds))
	for _, d := range ds {
		status, lastError := diskStatusAndError(d.Flags, d.LastError)
		out = append(out, models.Disk{
			Path:        d.Chunkserver + ":" + d.Path,
			Status:      status,
			LastError:   lastError,
			TotalSpace:  d.TotalSpaceBytes,
			UsedSpace:   d.UsedSpaceBytes,
			Chunks:      uint32(d.Chunks),
			MinuteStats: mapDiskStats(d.Stats.Minute),
			HourStats:   mapDiskStats(d.Stats.Hour),
			DayStats:    mapDiskStats(d.Stats.Day),
		})
	}
	return out, nil
}

// --- GET /metaloggers, /inotifiers -> []Metalogger/[]INotifier ------------

type nodeDTO struct {
	ID       uint32 `json:"id"`
	IP       string `json:"ip"`
	Hostname string `json:"hostname"`
	Version  string `json:"version"`
}

func (c *Client) GetMetaloggers() ([]models.Metalogger, error) {
	var ds []nodeDTO
	if err := c.get("/api/v1/metaloggers?resolve=true", &ds); err != nil {
		return nil, err
	}
	out := make([]models.Metalogger, 0, len(ds))
	for _, d := range ds {
		out = append(out, models.Metalogger{ID: int(d.ID), Hostname: d.Hostname, IPAddress: d.IP, Version: d.Version})
	}
	return out, nil
}

func (c *Client) GetInotifiers() ([]models.INotifier, error) {
	var ds []nodeDTO
	if err := c.get("/api/v1/inotifiers?resolve=true", &ds); err != nil {
		return nil, err
	}
	out := make([]models.INotifier, 0, len(ds))
	for _, d := range ds {
		out = append(out, models.INotifier{ID: int(d.ID), Hostname: d.Hostname, IPAddress: d.IP, Version: d.Version})
	}
	return out, nil
}

// --- GET /mounts -> []Mount ------------------------------------------------

type opStatsDTO struct {
	Statfs   uint64 `json:"statfs"`
	Getattr  uint64 `json:"getattr"`
	Setattr  uint64 `json:"setattr"`
	Lookup   uint64 `json:"lookup"`
	Mkdir    uint64 `json:"mkdir"`
	Rmdir    uint64 `json:"rmdir"`
	Symlink  uint64 `json:"symlink"`
	Readlink uint64 `json:"readlink"`
	Mknod    uint64 `json:"mknod"`
	Unlink   uint64 `json:"unlink"`
	Rename   uint64 `json:"rename"`
	Link     uint64 `json:"link"`
	Readdir  uint64 `json:"readdir"`
	Open     uint64 `json:"open"`
	Read     uint64 `json:"read"`
	Write    uint64 `json:"write"`
	Total    uint64 `json:"total"`
}

func mapOpStats(d opStatsDTO) *models.OperationStats {
	return &models.OperationStats{
		Statfs: uint32(d.Statfs), Getattr: uint32(d.Getattr), Setattr: uint32(d.Setattr),
		Lookup: uint32(d.Lookup), Mkdir: uint32(d.Mkdir), Rmdir: uint32(d.Rmdir),
		Symlink: uint32(d.Symlink), Readlink: uint32(d.Readlink), Mknod: uint32(d.Mknod),
		Unlink: uint32(d.Unlink), Rename: uint32(d.Rename), Link: uint32(d.Link),
		Readdir: uint32(d.Readdir), Open: uint32(d.Open), Read: uint32(d.Read),
		Write: uint32(d.Write), Total: d.Total,
	}
}

type mountDTO struct {
	ID              uint32     `json:"id"`
	SessionID       uint32     `json:"sessionId"`
	IP              string     `json:"ip"`
	Hostname        string     `json:"hostname"`
	Version         string     `json:"version"`
	RootPath        string     `json:"rootPath"`
	MountedPath     string     `json:"mountedPath"`
	MountInfo       string     `json:"mountInfo"`
	Flags           []string   `json:"flags"`
	RootUID         uint32     `json:"rootUid"`
	RootGID         uint32     `json:"rootGid"`
	MapAllUID       uint32     `json:"mapAllUid"`
	MapAllGID       uint32     `json:"mapAllGid"`
	MinGoal         uint8      `json:"minGoal"`
	MaxGoal         uint8      `json:"maxGoal"`
	MinTrashTime    uint32     `json:"minTrashTime"`
	MaxTrashTime    uint32     `json:"maxTrashTime"`
	CurrentOpStats  opStatsDTO `json:"currentOpStats"`
	LastHourOpStats opStatsDTO `json:"lastHourOpStats"`
}

func (c *Client) GetMounts() ([]models.Mount, error) {
	var ds []mountDTO
	if err := c.get("/api/v1/mounts?resolve=true", &ds); err != nil {
		return nil, err
	}
	out := make([]models.Mount, 0, len(ds))
	for _, d := range ds {
		minGoal, maxGoal := d.MinGoal, d.MaxGoal
		minTrash, maxTrash := d.MinTrashTime, d.MaxTrashTime
		out = append(out, models.Mount{
			ID:              int(d.ID),
			SessionID:       d.SessionID,
			Hostname:        d.Hostname,
			IPAddress:       d.IP,
			MountedPath:     d.MountedPath,
			Version:         d.Version,
			RootPath:        d.RootPath,
			MountInfo:       d.MountInfo,
			Flags:           strings.Join(d.Flags, ", "),
			RootUID:         d.RootUID,
			RootGID:         d.RootGID,
			MapAllUID:       d.MapAllUID,
			MapAllGID:       d.MapAllGID,
			MinGoal:         &minGoal,
			MaxGoal:         &maxGoal,
			MinTrashTime:    &minTrash,
			MaxTrashTime:    &maxTrash,
			CurrentOpStats:  mapOpStats(d.CurrentOpStats),
			LastHourOpStats: mapOpStats(d.LastHourOpStats),
		})
	}
	return out, nil
}

// --- GET /metadata-servers -> []MetadataServer ----------------------------

type metadataServerDTO struct {
	ID              uint32 `json:"id"`
	IP              string `json:"ip"`
	Port            uint16 `json:"port"`
	Hostname        string `json:"hostname"`
	Version         string `json:"version"`
	Personality     string `json:"personality"`
	State           string `json:"state"`
	MetadataVersion int64  `json:"metadataVersion"`
}

func (c *Client) GetMetadataServers() ([]models.MetadataServer, error) {
	var ds []metadataServerDTO
	if err := c.get("/api/v1/metadata-servers?resolve=true", &ds); err != nil {
		return nil, err
	}
	out := make([]models.MetadataServer, 0, len(ds))
	for _, d := range ds {
		out = append(out, models.MetadataServer{
			ID:              int(d.ID),
			Hostname:        d.Hostname,
			IPAddress:       d.IP,
			Port:            d.Port,
			Version:         d.Version,
			Personality:     d.Personality,
			State:           d.State,
			MetadataVersion: d.MetadataVersion,
		})
	}
	return out, nil
}

// --- GET /cluster/fs-check -> FsCheckInfo ----------------------------------

type fsCheckDTO struct {
	LoopStart       int64  `json:"loopStart"`
	LoopEnd         int64  `json:"loopEnd"`
	Files           uint64 `json:"files"`
	UnderGoalFiles  uint64 `json:"underGoalFiles"`
	MissingFiles    uint64 `json:"missingFiles"`
	Chunks          uint64 `json:"chunks"`
	UnderGoalChunks uint64 `json:"underGoalChunks"`
	MissingChunks   uint64 `json:"missingChunks"`
	Message         string `json:"message"`
}

func (c *Client) GetFsCheckInfo() (models.FsCheckInfo, error) {
	var d fsCheckDTO
	if err := c.get("/api/v1/cluster/fs-check", &d); err != nil {
		return models.FsCheckInfo{}, err
	}
	return models.FsCheckInfo{
		LoopStart:       uint32(d.LoopStart),
		LoopEnd:         uint32(d.LoopEnd),
		Files:           uint32(d.Files),
		UnderGoalFiles:  uint32(d.UnderGoalFiles),
		MissingFiles:    uint32(d.MissingFiles),
		Chunks:          uint32(d.Chunks),
		UnderGoalChunks: uint32(d.UnderGoalChunks),
		MissingChunks:   uint32(d.MissingChunks),
		Message:         d.Message,
	}, nil
}

// --- GET /cluster/chunk-operations -> ChunkOperationsInfo ------------------

type chunkOpsDTO struct {
	LoopStart             int64  `json:"loopStart"`
	LoopEnd               int64  `json:"loopEnd"`
	DeleteInvalid         uint64 `json:"deleteInvalid"`
	NotDeleteInvalid      uint64 `json:"notDeleteInvalid"`
	DeleteUnused          uint64 `json:"deleteUnused"`
	NotDeleteUnused       uint64 `json:"notDeleteUnused"`
	DeleteDiskClean       uint64 `json:"deleteDiskClean"`
	NotDeleteDiskClean    uint64 `json:"notDeleteDiskClean"`
	DeleteOverGoal        uint64 `json:"deleteOverGoal"`
	NotDeleteOverGoal     uint64 `json:"notDeleteOverGoal"`
	ReplicateUnderGoal    uint64 `json:"replicateUnderGoal"`
	NotReplicateUnderGoal uint64 `json:"notReplicateUnderGoal"`
	Rebalance             uint64 `json:"rebalance"`
}

func (c *Client) GetChunkOperationsInfo() (models.ChunkOperationsInfo, error) {
	var d chunkOpsDTO
	if err := c.get("/api/v1/cluster/chunk-operations", &d); err != nil {
		return models.ChunkOperationsInfo{}, err
	}
	return models.ChunkOperationsInfo{
		LoopStart:             uint32(d.LoopStart),
		LoopEnd:               uint32(d.LoopEnd),
		DeleteInvalid:         uint32(d.DeleteInvalid),
		NotDeleteInvalid:      uint32(d.NotDeleteInvalid),
		DeleteUnused:          uint32(d.DeleteUnused),
		NotDeleteUnused:       uint32(d.NotDeleteUnused),
		DeleteDiskClean:       uint32(d.DeleteDiskClean),
		NotDeleteDiskClean:    uint32(d.NotDeleteDiskClean),
		DeleteOverGoal:        uint32(d.DeleteOverGoal),
		NotDeleteOverGoal:     uint32(d.NotDeleteOverGoal),
		ReplicateUnderGoal:    uint32(d.ReplicateUnderGoal),
		NotReplicateUnderGoal: uint32(d.NotReplicateUnderGoal),
		Rebalance:             uint32(d.Rebalance),
	}, nil
}

// --- GET /cluster/chunk-matrix -> ChunkMatrix ------------------------------

func (c *Client) GetChunkMatrix() (models.ChunkMatrix, error) {
	var d struct {
		Matrix [][]uint64 `json:"matrix"`
	}
	if err := c.get("/api/v1/cluster/chunk-matrix", &d); err != nil {
		return models.ChunkMatrix{}, err
	}
	out := make([][]uint32, len(d.Matrix))
	for i, row := range d.Matrix {
		r := make([]uint32, len(row))
		for j, v := range row {
			r[j] = uint32(v)
		}
		out[i] = r
	}
	return models.ChunkMatrix{Matrix: out}, nil
}

// --- GET /goals -> []Goal --------------------------------------------------

func (c *Client) GetGoals() ([]models.Goal, error) {
	var ds []struct {
		ID         uint16 `json:"id"`
		Name       string `json:"name"`
		Definition string `json:"definition"`
	}
	if err := c.get("/api/v1/goals", &ds); err != nil {
		return nil, err
	}
	out := make([]models.Goal, 0, len(ds))
	for _, d := range ds {
		out = append(out, models.Goal{ID: d.ID, Name: d.Name, Definition: d.Definition})
	}
	return out, nil
}

// --- GET /exports -> []Export ----------------------------------------------

func (c *Client) GetExports() ([]models.Export, error) {
	var ds []struct {
		ID     uint32   `json:"id"`
		IPFrom string   `json:"ipFrom"`
		IPTo   string   `json:"ipTo"`
		Path   string   `json:"path"`
		Flags  []string `json:"flags"`
	}
	if err := c.get("/api/v1/exports", &ds); err != nil {
		return nil, err
	}
	out := make([]models.Export, 0, len(ds))
	for _, d := range ds {
		out = append(out, models.Export{
			ID:     int(d.ID),
			IPFrom: d.IPFrom,
			IPTo:   d.IPTo,
			Path:   d.Path,
			Flags:  strings.Join(d.Flags, ", "),
		})
	}
	return out, nil
}

// --- GET /cluster/chunk-health -> ChunkHealth ------------------------------

func (c *Client) GetChunkHealth() (models.ChunkHealth, error) {
	var d struct {
		RegularOnly bool `json:"regularOnly"`
		Goals       []struct {
			GoalID      uint16   `json:"goalId"`
			Safe        uint64   `json:"safe"`
			Endangered  uint64   `json:"endangered"`
			Lost        uint64   `json:"lost"`
			Replication []uint64 `json:"replication"`
			Deletion    []uint64 `json:"deletion"`
		} `json:"goals"`
	}
	if err := c.get("/api/v1/cluster/chunk-health", &d); err != nil {
		return models.ChunkHealth{}, err
	}
	out := models.ChunkHealth{
		RegularOnly: d.RegularOnly,
		Safe:        map[uint8]uint64{},
		Endangered:  map[uint8]uint64{},
		Lost:        map[uint8]uint64{},
		Replication: map[uint8][]uint64{},
		Deletion:    map[uint8][]uint64{},
	}
	for _, g := range d.Goals {
		k := uint8(g.GoalID)
		out.Safe[k] = g.Safe
		out.Endangered[k] = g.Endangered
		out.Lost[k] = g.Lost
		out.Replication[k] = g.Replication
		out.Deletion[k] = g.Deletion
	}
	return out, nil
}
