// Package wire implements the low-level binary deserialization primitives used
// to parse responses from the LeilFS/SaunaFS master. It is a direct port of the
// Python src/leil_client/deserializer.py: big-endian, cursor-based destructive
// reads.
package wire

import (
	"encoding/binary"
	"fmt"
)

// Error mirrors the Python DeserializationError.
type Error struct{ Msg string }

func (e *Error) Error() string { return e.Msg }

func errf(format string, a ...any) error { return &Error{Msg: fmt.Sprintf(format, a...)} }

// Reader consumes a byte slice from front to back, mirroring the Python code's
// `del buffer[:n]` destructive reads.
type Reader struct {
	buf []byte
	pos int
}

// NewReader wraps b. b is not copied; the caller must not mutate it concurrently.
func NewReader(b []byte) *Reader { return &Reader{buf: b} }

// Remaining returns the number of unconsumed bytes.
func (r *Reader) Remaining() int { return len(r.buf) - r.pos }

// Rest returns the unconsumed bytes without advancing.
func (r *Reader) Rest() []byte { return r.buf[r.pos:] }

func (r *Reader) need(n int) error {
	if r.Remaining() < n {
		return errf("buffer too short: need %d, have %d", n, r.Remaining())
	}
	return nil
}

// U8 reads a uint8 (Python struct 'B').
func (r *Reader) U8() (uint8, error) {
	if err := r.need(1); err != nil {
		return 0, err
	}
	v := r.buf[r.pos]
	r.pos++
	return v, nil
}

// U16 reads a big-endian uint16 (Python struct 'H').
func (r *Reader) U16() (uint16, error) {
	if err := r.need(2); err != nil {
		return 0, err
	}
	v := binary.BigEndian.Uint16(r.buf[r.pos:])
	r.pos += 2
	return v, nil
}

// U32 reads a big-endian uint32 (Python struct 'L').
func (r *Reader) U32() (uint32, error) {
	if err := r.need(4); err != nil {
		return 0, err
	}
	v := binary.BigEndian.Uint32(r.buf[r.pos:])
	r.pos += 4
	return v, nil
}

// U64 reads a big-endian uint64 (Python struct 'Q').
func (r *Reader) U64() (uint64, error) {
	if err := r.need(8); err != nil {
		return 0, err
	}
	v := binary.BigEndian.Uint64(r.buf[r.pos:])
	r.pos += 8
	return v, nil
}

// Raw reads n bytes, advancing the cursor. The returned slice aliases the
// underlying buffer; callers that retain it should copy.
func (r *Reader) Raw(n int) ([]byte, error) {
	if err := r.need(n); err != nil {
		return nil, err
	}
	b := r.buf[r.pos : r.pos+n]
	r.pos += n
	return b, nil
}

// String reads a length-prefixed string. It mirrors deserializer.unpack_string:
//   - legacy strings are not null-terminated; the full length is decoded.
//   - V2 strings carry a trailing NUL counted in the length; length-1 is decoded.
//
// In both cases the cursor advances by the full prefixed length.
func (r *Reader) String(legacy bool) (string, error) {
	length, err := r.U32()
	if err != nil {
		return "", err
	}
	n := int(length)
	if err := r.need(n); err != nil {
		return "", errf("buffer too short for string: need %d, have %d", n, r.Remaining())
	}
	take := n
	if !legacy && n > 0 {
		take = n - 1 // drop the NUL terminator
	}
	s := string(r.buf[r.pos : r.pos+take])
	r.pos += n
	return s, nil
}
