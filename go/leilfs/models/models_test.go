package models

import (
	"bytes"
	"encoding/binary"
	"encoding/json"
	"strings"
	"testing"

	"github.com/leil-io/saunafs-monitoring/go/leilfs/internal/wire"
)

type bw struct{ b bytes.Buffer }

func (x *bw) u8(v uint8)   { x.b.WriteByte(v) }
func (x *bw) u32(v uint32) { binary.Write(&x.b, binary.BigEndian, v) }
func (x *bw) u64(v uint64) { binary.Write(&x.b, binary.BigEndian, v) }
func (x *bw) r() *wire.Reader {
	return wire.NewReader(x.b.Bytes())
}

func TestChunkOperationsInfoFromBuffer(t *testing.T) {
	w := &bw{}
	for i := uint32(1); i <= 13; i++ {
		w.u32(i)
	}
	got, err := ChunkOperationsInfoFromBuffer(w.r())
	if err != nil {
		t.Fatal(err)
	}
	if got.LoopStart != 1 || got.Rebalance != 13 || got.ReplicateUnderGoal != 11 {
		t.Errorf("unexpected: %+v", got)
	}
}

// TestChunkHealthJSONKeys validates the one flagged compatibility risk: Go's
// integer-keyed maps must marshal to string-keyed JSON objects, matching
// Pydantic's Dict[int, ...] output.
func TestChunkHealthJSONKeys(t *testing.T) {
	w := &bw{}
	w.u8(1)  // regular_only
	w.u32(1) // safe: count
	w.u8(2)  // goal_id
	w.u64(100)
	w.u32(0) // endangered: count
	w.u32(0) // lost: count
	w.u32(1) // replication: count
	w.u8(2)  // goal_id
	for i := 0; i < 11; i++ {
		w.u64(uint64(i))
	}
	w.u32(0) // deletion: count

	ch, err := ChunkHealthFromBuffer(w.r())
	if err != nil {
		t.Fatal(err)
	}
	if !ch.RegularOnly || ch.Safe[2] != 100 || len(ch.Replication[2]) != 11 {
		t.Fatalf("unexpected ChunkHealth: %+v", ch)
	}

	out, err := json.Marshal(ch)
	if err != nil {
		t.Fatal(err)
	}
	s := string(out)
	for _, want := range []string{`"regular_only":true`, `"safe":{"2":100}`, `"endangered":{}`, `"replication":{"2":[0,1,2,3,4,5,6,7,8,9,10]}`} {
		if !strings.Contains(s, want) {
			t.Errorf("JSON missing %s\ngot: %s", want, s)
		}
	}
}

func TestGoalList(t *testing.T) {
	w := &bw{}
	w.u32(1) // count
	binary.Write(&w.b, binary.BigEndian, uint16(7))
	w.u32(3) // name length (incl NUL): "ec\x00"
	w.b.WriteString("ec\x00")
	w.u32(5) // definition length (incl NUL): "$ec3\x00"
	w.b.WriteString("$ec3\x00")

	goals, err := GoalList(w.r())
	if err != nil {
		t.Fatal(err)
	}
	if len(goals) != 1 || goals[0].ID != 7 || goals[0].Name != "ec" || goals[0].Definition != "$ec3" {
		t.Fatalf("unexpected goals: %+v", goals)
	}
}
