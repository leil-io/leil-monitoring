package models

import (
	"strings"

	"github.com/leil-io/saunafs-monitoring/go/leilfs/internal/wire"
)

// OperationStats mirrors models.OperationStats. Total is the sum of all stats
// in the source list (get_from_list sums the entire vector).
type OperationStats struct {
	Statfs   uint32 `json:"statfs"`
	Getattr  uint32 `json:"getattr"`
	Setattr  uint32 `json:"setattr"`
	Lookup   uint32 `json:"lookup"`
	Mkdir    uint32 `json:"mkdir"`
	Rmdir    uint32 `json:"rmdir"`
	Symlink  uint32 `json:"symlink"`
	Readlink uint32 `json:"readlink"`
	Mknod    uint32 `json:"mknod"`
	Unlink   uint32 `json:"unlink"`
	Rename   uint32 `json:"rename"`
	Link     uint32 `json:"link"`
	Readdir  uint32 `json:"readdir"`
	Open     uint32 `json:"open"`
	Read     uint32 `json:"read"`
	Write    uint32 `json:"write"`
	Total    uint64 `json:"total"`
}

func operationStatsFromList(list []uint32) OperationStats {
	var total uint64
	for _, v := range list {
		total += uint64(v)
	}
	get := func(i int) uint32 {
		if i < len(list) {
			return list[i]
		}
		return 0
	}
	return OperationStats{
		Statfs: get(0), Getattr: get(1), Setattr: get(2), Lookup: get(3),
		Mkdir: get(4), Rmdir: get(5), Symlink: get(6), Readlink: get(7),
		Mknod: get(8), Unlink: get(9), Rename: get(10), Link: get(11),
		Readdir: get(12), Open: get(13), Read: get(14), Write: get(15),
		Total: total,
	}
}

// Mount mirrors models.Mount. With vmode=1 all optional fields are present.
type Mount struct {
	ID              int             `json:"id"`
	SessionID       uint32          `json:"session_id"`
	Hostname        string          `json:"hostname"`
	IPAddress       string          `json:"ip_address"`
	MountedPath     string          `json:"mounted_path"`
	Version         string          `json:"version"`
	RootPath        string          `json:"root_path"`
	MountInfo       string          `json:"mount_info"`
	Flags           string          `json:"flags"`
	RootUID         uint32          `json:"root_uid"`
	RootGID         uint32          `json:"root_gid"`
	MapAllUID       uint32          `json:"map_all_uid"`
	MapAllGID       uint32          `json:"map_all_gid"`
	MinGoal         *uint8          `json:"min_goal"`
	MaxGoal         *uint8          `json:"max_goal"`
	MinTrashTime    *uint32         `json:"min_trash_time"`
	MaxTrashTime    *uint32         `json:"max_trash_time"`
	CurrentOpStats  *OperationStats `json:"current_op_stats"`
	LastHourOpStats *OperationStats `json:"last_hour_op_stats"`
}

// MountFromBuffer mirrors Mount.from_buffer with the vmode=1 layout.
func MountFromBuffer(r *wire.Reader, statsCount int) (Mount, error) {
	var m Mount
	sessionID, err := r.U32()
	if err != nil {
		return m, wrap("Mount", err)
	}
	ip1, err := r.U8()
	if err != nil {
		return m, wrap("Mount", err)
	}
	ip2, err := r.U8()
	if err != nil {
		return m, wrap("Mount", err)
	}
	ip3, err := r.U8()
	if err != nil {
		return m, wrap("Mount", err)
	}
	ip4, err := r.U8()
	if err != nil {
		return m, wrap("Mount", err)
	}
	v1, err := r.U16()
	if err != nil {
		return m, wrap("Mount", err)
	}
	v2, err := r.U8()
	if err != nil {
		return m, wrap("Mount", err)
	}
	v3, err := r.U8()
	if err != nil {
		return m, wrap("Mount", err)
	}

	rootPath, err := r.String(true)
	if err != nil {
		return m, wrap("Mount", err)
	}
	mountedPath, err := r.String(true)
	if err != nil {
		return m, wrap("Mount", err)
	}

	sesflags, err := r.U8()
	if err != nil {
		return m, wrap("Mount", err)
	}
	rootuid, err := r.U32()
	if err != nil {
		return m, wrap("Mount", err)
	}
	rootgid, err := r.U32()
	if err != nil {
		return m, wrap("Mount", err)
	}
	mapalluid, err := r.U32()
	if err != nil {
		return m, wrap("Mount", err)
	}
	mapallgid, err := r.U32()
	if err != nil {
		return m, wrap("Mount", err)
	}

	mingoal, err := r.U8()
	if err != nil {
		return m, wrap("Mount", err)
	}
	maxgoal, err := r.U8()
	if err != nil {
		return m, wrap("Mount", err)
	}
	mintrash, err := r.U32()
	if err != nil {
		return m, wrap("Mount", err)
	}
	maxtrash, err := r.U32()
	if err != nil {
		return m, wrap("Mount", err)
	}

	readStats := func() (OperationStats, error) {
		list := make([]uint32, statsCount)
		for i := 0; i < statsCount; i++ {
			v, err := r.U32()
			if err != nil {
				return OperationStats{}, wrap("Mount", err)
			}
			list[i] = v
		}
		return operationStatsFromList(list), nil
	}
	current, err := readStats()
	if err != nil {
		return m, err
	}
	lastHour, err := readStats()
	if err != nil {
		return m, err
	}

	ip := ipv4(ip1, ip2, ip3, ip4)
	var flags []string
	if sesflags&1 != 0 {
		flags = append(flags, "ro")
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

	m = Mount{
		SessionID:       sessionID,
		Hostname:        wire.Resolve(ip),
		IPAddress:       ip,
		MountedPath:     mountedPath,
		Version:         version(v1, v2, v3),
		RootPath:        rootPath,
		MountInfo:       "",
		Flags:           strings.Join(flags, ", "),
		RootUID:         rootuid,
		RootGID:         rootgid,
		MapAllUID:       mapalluid,
		MapAllGID:       mapallgid,
		MinGoal:         &mingoal,
		MaxGoal:         &maxgoal,
		MinTrashTime:    &mintrash,
		MaxTrashTime:    &maxtrash,
		CurrentOpStats:  &current,
		LastHourOpStats: &lastHour,
	}
	return m, nil
}

// mountExtraInfo mirrors Mount.get_mounts_info: a session_id -> info-string map.
// Any parse error yields an empty map (the Python code logs and returns {}).
func mountExtraInfo(r *wire.Reader) map[uint32]string {
	info := map[uint32]string{}
	vectorSize, err := r.U32()
	if err != nil {
		return map[uint32]string{}
	}
	for i := uint32(0); i < vectorSize; i++ {
		sessionID, err := r.U32()
		if err != nil {
			return map[uint32]string{}
		}
		s, err := r.String(false)
		if err != nil {
			return map[uint32]string{}
		}
		info[sessionID] = s
	}
	return info
}

// MountList mirrors Mount.get_list: a stats-count header (uint16) followed by
// mount entries until exhaustion, merged with the extra mount-info buffer.
func MountList(r *wire.Reader, extra *wire.Reader) ([]Mount, error) {
	extraInfo := mountExtraInfo(extra)
	statsCount, err := r.U16()
	if err != nil {
		return nil, wrap("Mount", err)
	}
	mounts := []Mount{}
	for r.Remaining() > 0 {
		m, err := MountFromBuffer(r, int(statsCount))
		if err != nil {
			return nil, err
		}
		m.ID = len(mounts) + 1
		if v, ok := extraInfo[m.SessionID]; ok {
			m.MountInfo = "\n" + v
		}
		mounts = append(mounts, m)
	}
	return mounts, nil
}
