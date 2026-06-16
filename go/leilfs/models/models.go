// Package models holds the data structures returned by the LeilFS/SaunaFS
// client, ported from src/leil_client/models.py. JSON tags match the Pydantic
// field names exactly so the Go API is drop-in compatible with the FastAPI one.
package models

import (
	"fmt"

	"github.com/leil-io/saunafs-monitoring/go/leilfs/internal/wire"
)

func version(v1 uint16, v2, v3 uint8) string {
	return fmt.Sprintf("%d.%d.%d", v1, v2, v3)
}

func ipv4(a, b, c, d uint8) string {
	return fmt.Sprintf("%d.%d.%d.%d", a, b, c, d)
}

// SystemInfo mirrors models.SystemInfo (struct ">HBBQQQQLQLLLLLLLL").
type SystemInfo struct {
	Version       string `json:"version"`
	RAMUsed       uint64 `json:"ram_used"`
	TotalSpace    uint64 `json:"total_space"`
	AvailSpace    uint64 `json:"avail_space"`
	TrashSpace    uint64 `json:"trash_space"`
	TrashFiles    uint32 `json:"trash_files"`
	ReservedSpace uint64 `json:"reserved_space"`
	ReservedFiles uint32 `json:"reserved_files"`
	TotalObjects  uint32 `json:"total_objects"`
	Directories   uint32 `json:"directories"`
	Files         uint32 `json:"files"`
	Symlinks      uint32 `json:"symlinks"`
	Chunks        uint32 `json:"chunks"`
	AllCopies     uint32 `json:"all_copies"`
	RegularCopies uint32 `json:"regular_copies"`
}

func SystemInfoFromBuffer(r *wire.Reader) (SystemInfo, error) {
	var s SystemInfo
	v1, err := r.U16()
	if err != nil {
		return s, wrap("SystemInfo", err)
	}
	v2, err := r.U8()
	if err != nil {
		return s, wrap("SystemInfo", err)
	}
	v3, err := r.U8()
	if err != nil {
		return s, wrap("SystemInfo", err)
	}
	q := func(dst *uint64) error { v, e := r.U64(); *dst = v; return e }
	l := func(dst *uint32) error { v, e := r.U32(); *dst = v; return e }
	for _, step := range []func() error{
		func() error { return q(&s.RAMUsed) },
		func() error { return q(&s.TotalSpace) },
		func() error { return q(&s.AvailSpace) },
		func() error { return q(&s.TrashSpace) },
		func() error { return l(&s.TrashFiles) },
		func() error { return q(&s.ReservedSpace) },
		func() error { return l(&s.ReservedFiles) },
		func() error { return l(&s.TotalObjects) },
		func() error { return l(&s.Directories) },
		func() error { return l(&s.Files) },
		func() error { return l(&s.Symlinks) },
		func() error { return l(&s.Chunks) },
		func() error { return l(&s.AllCopies) },
		func() error { return l(&s.RegularCopies) },
	} {
		if err := step(); err != nil {
			return s, wrap("SystemInfo", err)
		}
	}
	s.Version = version(v1, v2, v3)
	return s, nil
}

// FsCheckInfo mirrors models.FsCheckInfo (struct ">LLLLLLLL" + legacy string).
type FsCheckInfo struct {
	LoopStart       uint32 `json:"loop_start"`
	LoopEnd         uint32 `json:"loop_end"`
	Files           uint32 `json:"files"`
	UnderGoalFiles  uint32 `json:"under_goal_files"`
	MissingFiles    uint32 `json:"missing_files"`
	Chunks          uint32 `json:"chunks"`
	UnderGoalChunks uint32 `json:"under_goal_chunks"`
	MissingChunks   uint32 `json:"missing_chunks"`
	Message         string `json:"message"`
}

func FsCheckInfoFromBuffer(r *wire.Reader) (FsCheckInfo, error) {
	var f FsCheckInfo
	dst := []*uint32{
		&f.LoopStart, &f.LoopEnd, &f.Files, &f.UnderGoalFiles,
		&f.MissingFiles, &f.Chunks, &f.UnderGoalChunks, &f.MissingChunks,
	}
	for _, d := range dst {
		v, err := r.U32()
		if err != nil {
			return f, wrap("FsCheckInfo", err)
		}
		*d = v
	}
	msg, err := r.String(true)
	if err != nil {
		return f, wrap("FsCheckInfo", err)
	}
	f.Message = msg
	return f, nil
}

// ChunkOperationsInfo mirrors models.ChunkOperationsInfo (13 × uint32).
type ChunkOperationsInfo struct {
	LoopStart             uint32 `json:"loop_start"`
	LoopEnd               uint32 `json:"loop_end"`
	DeleteInvalid         uint32 `json:"delete_invalid"`
	NotDeleteInvalid      uint32 `json:"not_delete_invalid"`
	DeleteUnused          uint32 `json:"delete_unused"`
	NotDeleteUnused       uint32 `json:"not_delete_unused"`
	DeleteDiskClean       uint32 `json:"delete_disk_clean"`
	NotDeleteDiskClean    uint32 `json:"not_delete_disk_clean"`
	DeleteOverGoal        uint32 `json:"delete_over_goal"`
	NotDeleteOverGoal     uint32 `json:"not_delete_over_goal"`
	ReplicateUnderGoal    uint32 `json:"replicate_under_goal"`
	NotReplicateUnderGoal uint32 `json:"not_replicate_under_goal"`
	Rebalance             uint32 `json:"rebalance"`
}

func ChunkOperationsInfoFromBuffer(r *wire.Reader) (ChunkOperationsInfo, error) {
	var c ChunkOperationsInfo
	dst := []*uint32{
		&c.LoopStart, &c.LoopEnd, &c.DeleteInvalid, &c.NotDeleteInvalid,
		&c.DeleteUnused, &c.NotDeleteUnused, &c.DeleteDiskClean, &c.NotDeleteDiskClean,
		&c.DeleteOverGoal, &c.NotDeleteOverGoal, &c.ReplicateUnderGoal,
		&c.NotReplicateUnderGoal, &c.Rebalance,
	}
	for _, d := range dst {
		v, err := r.U32()
		if err != nil {
			return c, wrap("ChunkOperationsInfo", err)
		}
		*d = v
	}
	return c, nil
}

// ChunkMatrix mirrors models.ChunkMatrix: an 11x11 grid of uint32 read by the
// client directly (no per-row helper in Python).
type ChunkMatrix struct {
	Matrix [][]uint32 `json:"matrix"`
}

// Goal mirrors models.Goal (id uint16 + two V2 strings).
type Goal struct {
	ID         uint16 `json:"id"`
	Name       string `json:"name"`
	Definition string `json:"definition"`
}

func GoalFromBuffer(r *wire.Reader) (Goal, error) {
	var g Goal
	id, err := r.U16()
	if err != nil {
		return g, wrap("Goal", err)
	}
	name, err := r.String(false)
	if err != nil {
		return g, wrap("Goal", err)
	}
	def, err := r.String(false)
	if err != nil {
		return g, wrap("Goal", err)
	}
	g.ID, g.Name, g.Definition = id, name, def
	return g, nil
}

// GoalList mirrors Goal.get_list: count-prefixed (uint32) list.
func GoalList(r *wire.Reader) ([]Goal, error) {
	count, err := r.U32()
	if err != nil {
		return nil, wrap("Goal", err)
	}
	goals := make([]Goal, 0, count)
	for i := uint32(0); i < count; i++ {
		g, err := GoalFromBuffer(r)
		if err != nil {
			return nil, err
		}
		goals = append(goals, g)
	}
	return goals, nil
}

func wrap(name string, err error) error {
	return &wire.Error{Msg: fmt.Sprintf("Failed to deserialize %s: %v", name, err)}
}
