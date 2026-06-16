package models

import (
	"fmt"

	"github.com/leil-io/saunafs-monitoring/go/leilfs/internal/wire"
)

func formatLastError(errTime uint32, errChunkID uint64) string {
	return fmt.Sprintf("%d on chunk: %d", errTime, errChunkID)
}

// DiskStats mirrors models.DiskStats. The averages/per-second fields are
// computed exactly as in the Python from_buffer.
type DiskStats struct {
	ReadBytes          uint64  `json:"read_bytes"`
	ReadBytesPersecond float64 `json:"read_bytes_persecond"`
	ReadOps            uint32  `json:"read_ops"`
	ReadUsec           uint64  `json:"read_usec"`
	ReadUsecAvg        float64 `json:"read_usec_avg"`
	ReadUsecMax        uint32  `json:"read_usec_max"`
	ReadBlockSizeAvg   float64 `json:"read_block_size_avg"`

	WrittenBytes          uint64  `json:"written_bytes"`
	WrittenBytesPersecond float64 `json:"written_bytes_persecond"`
	WriteOps              uint32  `json:"write_ops"`
	WrittenUsec           uint64  `json:"written_usec"`
	WrittenUsecAvg        float64 `json:"written_usec_avg"`
	WrittenUsecMax        uint32  `json:"written_usec_max"`
	WrittenBlockSizeAvg   float64 `json:"written_block_size_avg"`

	FsyncOps     uint32  `json:"fsync_ops"`
	FsyncUsec    uint64  `json:"fsync_usec"`
	FsyncUsecAvg float64 `json:"fsync_usec_avg"`
	FsyncUsecMax uint32  `json:"fsync_usec_max"`
}

// DiskStatsFromBuffer reads ">QQQQQ" then ">LLLLLL" and derives the rates.
func DiskStatsFromBuffer(r *wire.Reader) (DiskStats, error) {
	var d DiskStats
	rbytes, err := r.U64()
	if err != nil {
		return d, wrap("DiskStats", err)
	}
	wbytes, err := r.U64()
	if err != nil {
		return d, wrap("DiskStats", err)
	}
	usecreadsum, err := r.U64()
	if err != nil {
		return d, wrap("DiskStats", err)
	}
	usecwritesum, err := r.U64()
	if err != nil {
		return d, wrap("DiskStats", err)
	}
	usecfsyncsum, err := r.U64()
	if err != nil {
		return d, wrap("DiskStats", err)
	}
	rops, err := r.U32()
	if err != nil {
		return d, wrap("DiskStats", err)
	}
	wops, err := r.U32()
	if err != nil {
		return d, wrap("DiskStats", err)
	}
	fsyncops, err := r.U32()
	if err != nil {
		return d, wrap("DiskStats", err)
	}
	usecreadmax, err := r.U32()
	if err != nil {
		return d, wrap("DiskStats", err)
	}
	usecwritemax, err := r.U32()
	if err != nil {
		return d, wrap("DiskStats", err)
	}
	usecfsyncmax, err := r.U32()
	if err != nil {
		return d, wrap("DiskStats", err)
	}

	var readPerSec, writePerSec float64
	if usecreadsum > 0 {
		readPerSec = float64(rbytes) * 1_000_000 / float64(usecreadsum)
	}
	if usecwritesum+usecfsyncsum > 0 {
		writePerSec = float64(wbytes) * 1_000_000 / float64(usecwritesum+usecfsyncsum)
	}
	var readUsecAvg, readBlock float64
	if rops > 0 {
		readUsecAvg = float64(usecreadsum) / float64(rops)
		readBlock = float64(rbytes) / float64(rops)
	}
	var writeUsecAvg, writeBlock float64
	if wops > 0 {
		writeUsecAvg = float64(usecwritesum) / float64(wops)
		writeBlock = float64(wbytes) / float64(wops)
	}
	var fsyncUsecAvg float64
	if fsyncops > 0 {
		fsyncUsecAvg = float64(usecfsyncsum) / float64(fsyncops)
	}

	d = DiskStats{
		ReadBytes:             rbytes,
		ReadBytesPersecond:    readPerSec,
		ReadOps:               rops,
		ReadUsec:              usecreadsum,
		ReadUsecAvg:           readUsecAvg,
		ReadUsecMax:           usecreadmax,
		ReadBlockSizeAvg:      readBlock,
		WrittenBytes:          wbytes,
		WrittenBytesPersecond: writePerSec,
		WriteOps:              wops,
		WrittenUsec:           usecwritesum,
		WrittenUsecAvg:        writeUsecAvg,
		WrittenUsecMax:        usecwritemax,
		WrittenBlockSizeAvg:   writeBlock,
		FsyncOps:              fsyncops,
		FsyncUsec:             usecfsyncsum,
		FsyncUsecAvg:          fsyncUsecAvg,
		FsyncUsecMax:          usecfsyncmax,
	}
	return d, nil
}

// Disk mirrors models.Disk.
type Disk struct {
	Path        string    `json:"path"`
	Status      string    `json:"status"`
	LastError   string    `json:"last_error"`
	TotalSpace  uint64    `json:"total_space"`
	UsedSpace   uint64    `json:"used_space"`
	Chunks      uint32    `json:"chunks"`
	MinuteStats DiskStats `json:"minute_stats"`
	HourStats   DiskStats `json:"hour_stats"`
	DayStats    DiskStats `json:"day_stats"`
}

// DiskFromBuffer parses a single length-prefixed disk entry.
func DiskFromBuffer(r *wire.Reader) (Disk, error) {
	var d Disk
	entrySize, err := r.U16()
	if err != nil {
		return d, wrap("Disk", err)
	}
	entry, err := r.Raw(int(entrySize))
	if err != nil {
		return d, wrap("Disk", err)
	}
	er := wire.NewReader(entry)

	pathLen, err := er.U8()
	if err != nil {
		return d, wrap("Disk", err)
	}
	pathBytes, err := er.Raw(int(pathLen))
	if err != nil {
		return d, wrap("Disk", err)
	}
	path := string(pathBytes)

	flags, err := er.U8()
	if err != nil {
		return d, wrap("Disk", err)
	}
	errChunkID, err := er.U64()
	if err != nil {
		return d, wrap("Disk", err)
	}
	errTime, err := er.U32()
	if err != nil {
		return d, wrap("Disk", err)
	}
	used, err := er.U64()
	if err != nil {
		return d, wrap("Disk", err)
	}
	total, err := er.U64()
	if err != nil {
		return d, wrap("Disk", err)
	}
	chunks, err := er.U32()
	if err != nil {
		return d, wrap("Disk", err)
	}

	const defaultStatus = "OK"
	status := defaultStatus
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

	lastError := "No errors"
	if errTime > 0 {
		lastError = formatLastError(errTime, errChunkID)
		if status == defaultStatus {
			status = "Errors reported"
		}
	} else if flags&0x2 != 0 {
		lastError = "Read/Write error"
	}

	minute, err := DiskStatsFromBuffer(er)
	if err != nil {
		return d, err
	}
	hour, err := DiskStatsFromBuffer(er)
	if err != nil {
		return d, err
	}
	day, err := DiskStatsFromBuffer(er)
	if err != nil {
		return d, err
	}

	d = Disk{
		Path:        path,
		Status:      status,
		LastError:   lastError,
		TotalSpace:  total,
		UsedSpace:   used,
		Chunks:      chunks,
		MinuteStats: minute,
		HourStats:   hour,
		DayStats:    day,
	}
	return d, nil
}

// DiskList mirrors Disk.get_list: reads entries until the buffer is exhausted.
func DiskList(r *wire.Reader) ([]Disk, error) {
	disks := []Disk{}
	for r.Remaining() > 0 {
		d, err := DiskFromBuffer(r)
		if err != nil {
			return nil, err
		}
		disks = append(disks, d)
	}
	return disks, nil
}
