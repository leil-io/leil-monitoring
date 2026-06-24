package leilfs

import (
	"bytes"
	"encoding/binary"
	"fmt"
	"net"
	"sort"
	"strings"

	"github.com/leil-io/saunafs-monitoring/go/leilfs/internal/wire"
	"github.com/leil-io/saunafs-monitoring/go/leilfs/models"
)

// Client speaks the LeilFS/SaunaFS master protocol. Construct it with NewClient.
type Client struct {
	masterHost    string
	masterPort    int
	masterVersion [3]int
	dial          DialFunc
}

// NewClient connects lazily (per request) but immediately probes the master
// version, mirroring SaunaFSClient.__init__. A failed probe yields version
// {0,0,0} rather than an error, exactly like the Python client.
func NewClient(host string, port int) *Client {
	return NewClientWithDial(host, port, defaultDial)
}

// NewClientWithDial is NewClient with an injectable dialer (used by tests).
func NewClientWithDial(host string, port int, dial DialFunc) *Client {
	c := &Client{masterHost: host, masterPort: port, dial: dial}
	c.masterVersion = c.getMasterVersion()
	return c
}

// NewChartClient builds a client for the chart endpoint WITHOUT the eager
// master-version probe. GetChart does not need the version, and the probe sends
// an INFO (510) message — a master/CLI command. A chart target may be a
// chunkserver (the SPA requests per-chunkserver charts at its ip:9422), and a
// chunkserver mishandles an unexpected INFO on its client port: it aborts the
// connection's net worker (SIGABRT) and the chunkserver drops off the cluster.
// Skipping the probe means charts only ever send the chart command (504).
func NewChartClient(host string, port int) *Client {
	return &Client{masterHost: host, masterPort: port, dial: defaultDial}
}

// MasterVersion returns the cached master version triple.
func (c *Client) MasterVersion() [3]int { return c.masterVersion }

func (c *Client) getMasterVersion() [3]int {
	data, err := c.sendAndReceive(cmdInfo, nil, 0, "", 0)
	if err != nil || len(data) < 4 {
		return [3]int{0, 0, 0}
	}
	return [3]int{
		int(binary.BigEndian.Uint16(data[0:])),
		int(data[2]),
		int(data[3]),
	}
}

func (c *Client) GetInfo() (models.SystemInfo, error) {
	data, err := c.sendAndReceive(cmdInfo, nil, 0, "", 0)
	if err != nil {
		return models.SystemInfo{}, err
	}
	return models.SystemInfoFromBuffer(wire.NewReader(data))
}

func (c *Client) GetChart(host string, port int, chartID uint32) ([]byte, error) {
	payload := make([]byte, 4)
	binary.BigEndian.PutUint32(payload, chartID)
	return c.sendAndReceive(cmdChart, payload, 0, host, port)
}

func (c *Client) GetServers() ([]models.Server, error) {
	data, err := c.sendAndReceive(cmdSauCservList, []byte{0}, 0, "", 0)
	if err != nil {
		return nil, err
	}
	servers, err := models.ServerList(wire.NewReader(data))
	if err != nil {
		return nil, err
	}
	sort.SliceStable(servers, func(i, j int) bool {
		if servers[i].Hostname != servers[j].Hostname {
			return servers[i].Hostname < servers[j].Hostname
		}
		if cmp := compareIP(servers[i].IPAddress, servers[j].IPAddress); cmp != 0 {
			return cmp < 0
		}
		return servers[i].Port < servers[j].Port
	})
	return servers, nil
}

func (c *Client) GetDisks() ([]models.Disk, error) {
	servers, err := c.GetServers()
	if err != nil {
		return nil, err
	}
	all := []models.Disk{}
	for _, server := range servers {
		if server.IsDisconnected {
			continue
		}
		data, err := c.sendAndReceive(cmdHddList, nil, 0, server.IPAddress, int(server.Port))
		if err != nil {
			return nil, err
		}
		disks, err := models.DiskList(wire.NewReader(data))
		if err != nil {
			return nil, err
		}
		for i := range disks {
			disks[i].Path = fmt.Sprintf("%s:%s", server.Hostname, disks[i].Path)
		}
		all = append(all, disks...)
	}
	return all, nil
}

func (c *Client) GetMetaloggers() ([]models.Metalogger, error) {
	data, err := c.sendAndReceive(cmdMlogList, nil, 0, "", 0)
	if err != nil {
		return nil, err
	}
	loggers, err := models.MetaloggerList(wire.NewReader(data))
	if err != nil {
		return nil, err
	}
	sort.SliceStable(loggers, func(i, j int) bool { return loggers[i].Hostname < loggers[j].Hostname })
	return loggers, nil
}

func (c *Client) GetInotifiers() ([]models.INotifier, error) {
	if versionLess(c.masterVersion, VersionWithInotifiersSupport) {
		v := VersionWithInotifiersSupport
		return nil, fmt.Errorf("INotifiers are not supported in LeilFS versions below %d.%d.%d", v[0], v[1], v[2])
	}
	data, err := c.sendAndReceive(cmdInotifiersList, nil, 0, "", 0)
	if err != nil {
		return nil, err
	}
	notifiers, err := models.INotifierList(wire.NewReader(data))
	if err != nil {
		return nil, err
	}
	sort.SliceStable(notifiers, func(i, j int) bool { return notifiers[i].Hostname < notifiers[j].Hostname })
	return notifiers, nil
}

func (c *Client) GetMounts() ([]models.Mount, error) {
	extra, err := c.sendAndReceive(cmdMountInfoList, nil, 0, "", 0)
	if err != nil {
		return nil, err
	}
	data, err := c.sendAndReceive(cmdSessionList, []byte{1}, 0, "", 0)
	if err != nil {
		return nil, err
	}
	return models.MountList(wire.NewReader(data), wire.NewReader(extra))
}

func (c *Client) GetExports() ([]models.Export, error) {
	data, err := c.sendAndReceive(cmdExportsInfo, nil, 0, "", 0)
	if err != nil {
		return nil, err
	}
	return models.ExportList(wire.NewReader(data))
}

func (c *Client) GetFsCheckInfo() (models.FsCheckInfo, error) {
	data, err := c.sendAndReceive(cmdFstestInfo, nil, 0, "", 0)
	if err != nil {
		return models.FsCheckInfo{}, err
	}
	return models.FsCheckInfoFromBuffer(wire.NewReader(data))
}

func (c *Client) GetChunkOperationsInfo() (models.ChunkOperationsInfo, error) {
	data, err := c.sendAndReceive(cmdChunkstestInfo, nil, 0, "", 0)
	if err != nil {
		return models.ChunkOperationsInfo{}, err
	}
	return models.ChunkOperationsInfoFromBuffer(wire.NewReader(data))
}

func (c *Client) GetChunkMatrix() (models.ChunkMatrix, error) {
	data, err := c.sendAndReceive(cmdChunksMatrix, []byte{0}, 0, "", 0)
	if err != nil {
		return models.ChunkMatrix{}, err
	}
	r := wire.NewReader(data)
	matrix := make([][]uint32, 0, 11)
	for i := 0; i < 11; i++ {
		row := make([]uint32, 11)
		for j := 0; j < 11; j++ {
			v, err := r.U32()
			if err != nil {
				return models.ChunkMatrix{}, err
			}
			row[j] = v
		}
		matrix = append(matrix, row)
	}
	return models.ChunkMatrix{Matrix: matrix}, nil
}

func (c *Client) GetGoals() ([]models.Goal, error) {
	data, err := c.sendAndReceive(cmdListGoals, nil, 0, "", 0)
	if err != nil {
		return nil, err
	}
	return models.GoalList(wire.NewReader(data))
}

func (c *Client) GetChunkHealth() (models.ChunkHealth, error) {
	data, err := c.sendAndReceive(cmdChunksHealth, []byte{0}, 0, "", 0)
	if err != nil {
		return models.ChunkHealth{}, err
	}
	return models.ChunkHealthFromBuffer(wire.NewReader(data))
}

func (c *Client) GetHostname(host string, port int) (string, error) {
	data, err := c.sendAndReceive(cmdMetadataHostname, nil, 0, host, port)
	if err != nil {
		return "", err
	}
	return wire.NewReader(data).String(false)
}

func (c *Client) RemoveChunkserver(ip string, port uint16) error {
	parts := strings.Split(ip, ".")
	if len(parts) != 4 {
		return fmt.Errorf("Invalid ip: %s", ip)
	}
	payload := make([]byte, 6)
	for i, p := range parts {
		var n int
		if _, err := fmt.Sscanf(p, "%d", &n); err != nil || n < 0 || n > 255 {
			return fmt.Errorf("Invalid ip: %s", ip)
		}
		payload[i] = byte(n)
	}
	binary.BigEndian.PutUint16(payload[4:], port)
	data, err := c.sendAndReceive(cmdCsservRemoveserv, payload, 0, "", 0)
	if err != nil {
		return err
	}
	if len(data) != 0 {
		return fmt.Errorf("Buffer not empty for CSSERV_REMOVESERV!")
	}
	return nil
}

// GetMetadataServers mirrors the multi-round-trip get_metadata_servers.
func (c *Client) GetMetadataServers() ([]models.MetadataServer, error) {
	masterIP, err := net.ResolveIPAddr("ip4", c.masterHost)
	if err != nil {
		return nil, err
	}
	masterHostname, err := c.GetHostname(c.masterHost, c.masterPort)
	if err != nil {
		return nil, err
	}
	v := c.masterVersion
	master := models.MetadataServer{
		ID:              1,
		Hostname:        masterHostname,
		IPAddress:       masterIP.String(),
		Port:            uint16(c.masterPort),
		Version:         fmt.Sprintf("%d.%d.%d", v[0], v[1], v[2]),
		MetadataVersion: -1,
	}
	servers := []models.MetadataServer{master}

	statusBuf, err := c.sendAndReceive(cmdMetadataserverStatus, make([]byte, 4), 0, "", 0)
	if err != nil {
		return nil, err
	}
	if err := servers[0].ApplyStatus(statusBuf); err != nil {
		return nil, err
	}

	listBuf, err := c.sendAndReceive(cmdMetadataserversList, nil, 0, "", 0)
	if err != nil {
		return nil, err
	}
	shadows, err := models.MetadataServerList(wire.NewReader(listBuf))
	if err != nil {
		return nil, err
	}
	servers = append(servers, shadows...)

	for i := range servers {
		buf, err := c.sendAndReceive(cmdMetadataserverStatus, make([]byte, 4), 0, servers[i].IPAddress, int(servers[i].Port))
		if err != nil {
			return nil, err
		}
		if err := servers[i].ApplyStatus(buf); err != nil {
			return nil, err
		}
		hostname, err := c.GetHostname(servers[i].IPAddress, int(servers[i].Port))
		if err != nil {
			return nil, err
		}
		servers[i].Hostname = hostname
	}

	// Master stays first; shadows sorted by hostname.
	rest := servers[1:]
	sort.SliceStable(rest, func(i, j int) bool { return rest[i].Hostname < rest[j].Hostname })
	return servers, nil
}

func compareIP(a, b string) int {
	ipA, ipB := net.ParseIP(a), net.ParseIP(b)
	if ipA == nil || ipB == nil {
		return strings.Compare(a, b)
	}
	return bytes.Compare(ipA.To16(), ipB.To16())
}

func versionLess(a, b [3]int) bool {
	for i := 0; i < 3; i++ {
		if a[i] != b[i] {
			return a[i] < b[i]
		}
	}
	return false
}
