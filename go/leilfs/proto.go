// Package proto implements the LeilFS/SaunaFS master wire protocol and the
// high-level client, ported from src/leil_client/leil_client.py.
package leilfs

import (
	"encoding/binary"
	"fmt"
	"io"
	"net"
	"strconv"
	"time"
)

const ioTimeout = 5 * time.Second

// cmdPair is a (request, expected-response) command id pair. Commands greater
// than 1000 use the V2 framing (an extra 4-byte version field).
type cmdPair struct{ cmd, expected uint32 }

// Command pairs, mirroring leil_client.py:42-121.
var (
	cmdInfo                 = cmdPair{510, 511}
	cmdFstestInfo           = cmdPair{512, 513}
	cmdChunksMatrix         = cmdPair{516, 517}
	cmdChunkstestInfo       = cmdPair{514, 515}
	cmdSauCservList         = cmdPair{1549, 1550}
	cmdMetadataserversList  = cmdPair{1522, 1523}
	cmdInotifiersList       = cmdPair{1524, 1525}
	cmdMetadataserverStatus = cmdPair{1545, 1546}
	cmdHddList              = cmdPair{600, 601}
	cmdMlogList             = cmdPair{522, 523}
	cmdChart                = cmdPair{504, 505}
	cmdMountInfoList        = cmdPair{1609, 1610}
	cmdSessionList          = cmdPair{508, 509}
	cmdExportsInfo          = cmdPair{520, 521}
	cmdListGoals            = cmdPair{1547, 1548}
	cmdChunksHealth         = cmdPair{1526, 1527}
	cmdMetadataHostname     = cmdPair{1551, 1552}
	cmdCsservRemoveserv     = cmdPair{524, 525}
)

// VersionWithInotifiersSupport mirrors SAUNAFS_VERSION_WITH_INOTIFIERS_SUPPORT.
var VersionWithInotifiersSupport = [3]int{5, 4, 0}

// DialFunc dials a master/chunkserver. It is injectable for testing.
type DialFunc func(host string, port int) (net.Conn, error)

func defaultDial(host string, port int) (net.Conn, error) {
	return net.DialTimeout("tcp", net.JoinHostPort(host, strconv.Itoa(port)), ioTimeout)
}

// sendAndReceive performs one request/response exchange, mirroring
// SaunaFSClient.send_and_receive (leil_client.py:152-192). For V2 commands the
// leading 4-byte version field of the response payload is stripped.
func (c *Client) sendAndReceive(msg cmdPair, payload []byte, version uint32, host string, port int) ([]byte, error) {
	if host == "" {
		host = c.masterHost
	}
	if port == 0 {
		port = c.masterPort
	}
	isV2 := msg.cmd > 1000

	var req []byte
	if isV2 {
		length := uint32(4 + len(payload))
		req = make([]byte, 12+len(payload))
		binary.BigEndian.PutUint32(req[0:], msg.cmd)
		binary.BigEndian.PutUint32(req[4:], length)
		binary.BigEndian.PutUint32(req[8:], version)
		copy(req[12:], payload)
	} else {
		length := uint32(len(payload))
		req = make([]byte, 8+len(payload))
		binary.BigEndian.PutUint32(req[0:], msg.cmd)
		binary.BigEndian.PutUint32(req[4:], length)
		copy(req[8:], payload)
	}

	conn, err := c.dial(host, port)
	if err != nil {
		return nil, err
	}
	defer conn.Close()

	conn.SetWriteDeadline(time.Now().Add(ioTimeout))
	if _, err := conn.Write(req); err != nil {
		return nil, err
	}

	header := make([]byte, 8)
	conn.SetReadDeadline(time.Now().Add(ioTimeout))
	if _, err := io.ReadFull(conn, header); err != nil {
		return nil, err
	}
	respCmd := binary.BigEndian.Uint32(header[0:])
	respLen := binary.BigEndian.Uint32(header[4:])
	if respCmd != msg.expected {
		return nil, fmt.Errorf("Received wrong response command: %d, expected %d", respCmd, msg.expected)
	}

	respPayload := make([]byte, respLen)
	conn.SetReadDeadline(time.Now().Add(ioTimeout))
	if _, err := io.ReadFull(conn, respPayload); err != nil {
		return nil, err
	}

	if isV2 {
		if len(respPayload) < 4 {
			return nil, fmt.Errorf("V2 response payload is too short for version field")
		}
		return respPayload[4:], nil
	}
	return respPayload, nil
}
