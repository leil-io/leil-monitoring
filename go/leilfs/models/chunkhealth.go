package models

import "github.com/leil-io/saunafs-monitoring/go/leilfs/internal/wire"

// ChunkHealth mirrors models.ChunkHealth. The integer-keyed maps marshal to JSON
// objects with string keys, matching Pydantic's Dict[int, ...] output.
type ChunkHealth struct {
	RegularOnly bool               `json:"regular_only"`
	Safe        map[uint8]uint64   `json:"safe"`
	Endangered  map[uint8]uint64   `json:"endangered"`
	Lost        map[uint8]uint64   `json:"lost"`
	Replication map[uint8][]uint64 `json:"replication"`
	Deletion    map[uint8][]uint64 `json:"deletion"`
}

func readSimpleDict(r *wire.Reader) (map[uint8]uint64, error) {
	result := map[uint8]uint64{}
	count, err := r.U32()
	if err != nil {
		return nil, err
	}
	for i := uint32(0); i < count; i++ {
		goalID, err := r.U8()
		if err != nil {
			return nil, err
		}
		value, err := r.U64()
		if err != nil {
			return nil, err
		}
		result[goalID] = value
	}
	return result, nil
}

func readComplexDict(r *wire.Reader) (map[uint8][]uint64, error) {
	result := map[uint8][]uint64{}
	count, err := r.U32()
	if err != nil {
		return nil, err
	}
	for i := uint32(0); i < count; i++ {
		goalID, err := r.U8()
		if err != nil {
			return nil, err
		}
		values := make([]uint64, 11)
		for j := 0; j < 11; j++ {
			v, err := r.U64()
			if err != nil {
				return nil, err
			}
			values[j] = v
		}
		result[goalID] = values
	}
	return result, nil
}

// ChunkHealthFromBuffer mirrors ChunkHealth.from_buffer.
func ChunkHealthFromBuffer(r *wire.Reader) (ChunkHealth, error) {
	var c ChunkHealth
	regularOnly, err := r.U8()
	if err != nil {
		return c, wrap("ChunkHealth", err)
	}
	safe, err := readSimpleDict(r)
	if err != nil {
		return c, wrap("ChunkHealth", err)
	}
	endangered, err := readSimpleDict(r)
	if err != nil {
		return c, wrap("ChunkHealth", err)
	}
	lost, err := readSimpleDict(r)
	if err != nil {
		return c, wrap("ChunkHealth", err)
	}
	replication, err := readComplexDict(r)
	if err != nil {
		return c, wrap("ChunkHealth", err)
	}
	deletion, err := readComplexDict(r)
	if err != nil {
		return c, wrap("ChunkHealth", err)
	}
	c = ChunkHealth{
		RegularOnly: regularOnly != 0,
		Safe:        safe,
		Endangered:  endangered,
		Lost:        lost,
		Replication: replication,
		Deletion:    deletion,
	}
	return c, nil
}
