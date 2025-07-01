import socket
import struct
import select
import logging
from typing import List, Tuple, Dict, Any
from models import SystemInfo, Server, Disk, Metalogger, Mount

# Protocol constants
PROTO_BASE = 0
CLTOMA_INFO = (PROTO_BASE + 510)
MATOCL_INFO = (PROTO_BASE + 511)
CLTOMA_CSERV_LIST = (PROTO_BASE + 500)
MATOCL_CSERV_LIST = (PROTO_BASE + 501)
CLTOCS_HDD_LIST_V2 = (PROTO_BASE + 600)
MATOCL_HDD_LIST_V2 = (PROTO_BASE + 601)
CLTOMA_MLOG_LIST = (PROTO_BASE + 522)
MATOCL_MLOG_LIST = (PROTO_BASE + 523)
CLTOMA_SESSION_LIST = (PROTO_BASE + 508)
MATOCL_SESSION_LIST = (PROTO_BASE + 509)
CUTOAN_CHART = (PROTO_BASE + 504)
ANTOCU_CHART = (PROTO_BASE + 505)

SAU_CLTOMA_CSERV_LIST = 1549
SAU_MATOCL_CSERV_LIST = 1550
SAU_CLTOMA_MOUNT_INFO_LIST = 1609
SAU_MATOCL_MOUNT_INFO_LIST = 1610

class SaunaFSClient:
    def __init__(self, master_host: str, master_port: int):
        self.master_host = master_host
        self.master_port = master_port
        self.master_version = self._get_master_version()

    def _mysend(self, sock: socket.socket, msg: bytes):
        totalsent = 0
        logging.debug(f"Sending message: {msg}")
        while totalsent < len(msg):
            sent = sock.send(msg[totalsent:])
            if sent == 0:
                raise RuntimeError("Socket connection broken")
            totalsent += sent

    def _myrecv(self, sock: socket.socket, length: int) -> bytes:
        msg = b''
        logging.debug(f"Receiving message with length {length}")
        while len(msg) < length:
            ready = select.select([sock], [], [], 5)
            if not ready[0]:
                raise RuntimeError("Socket connection timed out")
            chunk = sock.recv(length - len(msg))
            if not chunk:
                raise RuntimeError("Socket connection broken")
            msg += chunk
        return msg

    def _send_and_receive(self, host: str, port: int, cmd: int, expected: int, payload: bytes = b'', version: int = 0) -> bytes:
        is_v2 = cmd > 1000

        if is_v2:
            length = 4 + len(payload)  # version field + data
            request = struct.pack(">LLL", cmd, length, version) + payload
            logging.debug(f"Sending V2 request: cmd={cmd}, length={length}, version={version}, payload={payload}")
        else:
            length = len(payload)
            request = struct.pack(">LL", cmd, length) + payload
            logging.debug(f"Sending V1 request: cmd={cmd}, length={length}, payload={payload}")

        with socket.socket() as s:
            s.settimeout(5)
            logging.debug(f"Connecting to {host}:{port}")
            s.connect((host, port))
            self._mysend(s, request)
            header = self._myrecv(s, 8)
            resp_cmd, resp_length = struct.unpack(">LL", header)
            logging.debug(f"Header received: cmd={resp_cmd}, length={resp_length}")

            if resp_cmd != expected:
                if cmd == CUTOAN_CHART and resp_cmd == ANTOCU_CHART:
                    pass
                else:
                    raise RuntimeError(f"Received wrong response command: {resp_cmd}, expected {expected}")

            resp_payload = self._myrecv(s, resp_length)
            if is_v2:
                if len(resp_payload) < 4:
                    raise ValueError("V2 response payload is too short for version field")
                resp_version = struct.unpack(">L", resp_payload[:4])[0]
                logging.debug(f"V2 response version: {resp_version}")
                return resp_payload[4:]
            else:
                return resp_payload

    def _deserialize_string(self, buffer: bytearray, legacy: bool = False) -> str:
        if legacy:
            if not buffer: raise ValueError("Legacy string buffer is empty")
            length, = struct.unpack(">L", buffer[:4])
            logging.debug(f"Deserializing legacy string with length: {length}")
            del buffer[:4]
            if len(buffer) < length: raise ValueError("Buffer too short for legacy string")
            value = buffer[:length].decode('utf-8', errors='replace')
            del buffer[:length]
            return value
        else:
            if len(buffer) < 4: raise ValueError("Buffer too short for V2 string length")
            length, = struct.unpack(">L", buffer[:4])
            del buffer[:4]
            if len(buffer) < length: raise ValueError(f"Buffer too short for V2 string data. Expected {length}, got {len(buffer)}")
            value = buffer[:length-1].decode('utf-8', errors='replace')
            del buffer[:length]
            return value

    def _get_master_version(self) -> Tuple[int, int, int]:
        try:
            data = self._send_and_receive(self.master_host, self.master_port, CLTOMA_INFO, MATOCL_INFO)
            if len(data) >= 4:
                v1, v2, v3 = struct.unpack(">HBB", data[:4])
                return (v1, v2, v3)
            return (0, 0, 0)
        except Exception:
            return (0, 0, 0)

    def get_system_info(self) -> SystemInfo:
        data = self._send_and_receive(self.master_host, self.master_port, CLTOMA_INFO, MATOCL_INFO)
        if len(data) == 80:
            v1, v2, v3, mem, total, avail, trspace, trfiles, respace, refiles, nodes, dirs, files, symlinks, chunks, allcopies, tdcopies = struct.unpack(">HBBQQQQLQLLLLLLLL", data)
            return SystemInfo(
                version=f"{v1}.{v2}.{v3}", ram_used=mem, total_space=total, avail_space=avail,
                trash_space=trspace, trash_files=trfiles, reserved_space=respace, reserved_files=refiles,
                total_objects=nodes, directories=dirs, files=files, symlinks=symlinks, chunks=chunks,
                all_copies=allcopies, regular_copies=tdcopies,
            )
        raise RuntimeError("Could not decode system info from master.")

    def get_servers(self) -> List[Server]:
        servers = []
        cmd = SAU_CLTOMA_CSERV_LIST
        payload = b'\x00'

        data = self._send_and_receive(self.master_host, self.master_port, cmd, SAU_MATOCL_CSERV_LIST, payload)

        buffer = bytearray(data)
        if len(buffer) < 4:
            return []
        vector_size, = struct.unpack(">L", buffer[:4])
        logging.debug(f"get_servers vector_size: {vector_size}")
        del buffer[:4]

        for i in range(int(vector_size)):
            if len(buffer) < 58:
                break
            disconnected, v1, v2, v3, ip1, ip2, ip3, ip4, port, used, total, chunks, tdused, tdtotal, tdchunks, errcnt = struct.unpack(">BBBBBBBBHQQLQQLL", buffer[:54])
            del buffer[:54]
            label = self._deserialize_string(buffer)

            ip_address = f"{ip1}.{ip2}.{ip3}.{ip4}"
            try:
                hostname = socket.gethostbyaddr(ip_address)[0]
            except socket.herror:
                hostname = "(unresolved)"

            servers.append(Server(
                id=i + 1, hostname=hostname, ip_address=ip_address, port=port,
                version=f"{v1}.{v2}.{v3}", is_disconnected=bool(disconnected),
                label=label, used_space=used, total_space=total, chunks=chunks,
                used_space_tobedeleted=tdused, total_space_tobedeleted=tdtotal,
                chunks_tobedeleted=tdchunks, error_count=errcnt
            ))
        return servers

    def get_disks(self) -> List[Disk]:
        all_disks = []
        for server in self.get_servers():
            if server.is_disconnected: continue
            try:
                data = self._send_and_receive(server.ip_address, server.port, CLTOCS_HDD_LIST_V2, MATOCL_HDD_LIST_V2)
                buffer = bytearray(data)
                while len(buffer) > 2:
                    entrysize, = struct.unpack(">H", buffer[:2])
                    del buffer[:2]
                    if len(buffer) < entrysize: break
                    entry = buffer[:entrysize]
                    del buffer[:entrysize]

                    plen = entry[0]
                    path = entry[1:1+plen].decode('utf-8', errors='replace')

                    flags, errchunkid, errtime, used, total, chunkscnt = struct.unpack(">BQLQQL", entry[plen+1:plen+34])

                    status = "ok"
                    if flags == 1: status = 'marked for removal'
                    elif flags == 2: status = 'damaged'
                    elif flags == 3: status = 'damaged, marked for removal'

                    last_error = "no errors"
                    if errtime > 0:
                        last_error = f"{errtime} on chunk: {errchunkid}"

                    all_disks.append(Disk(
                        path=f"{server.hostname}:{path}", status=status, last_error=last_error,
                        total_space=total, used_space=used, chunks=chunkscnt
                    ))
            except Exception:
                continue
        return all_disks

    def get_chart(self, host: str, port: int, chart_id: int) -> bytes:
        payload = struct.pack(">L", chart_id)
        return self._send_and_receive(host, port, CUTOAN_CHART, ANTOCU_CHART, payload)

    def get_metaloggers(self) -> List[Metalogger]:
        all_loggers = []
        data = self._send_and_receive(self.master_host, self.master_port, CLTOMA_MLOG_LIST, MATOCL_MLOG_LIST)
        buffer = bytearray(data)
        while len(buffer) >= 8:
            v1, v2, v3, ip1, ip2, ip3, ip4 = struct.unpack(">HBBBBBB", buffer[:8])
            del buffer[:8]
            ip_address = f"{ip1}.{ip2}.{ip3}.{ip4}"
            try:
                hostname = socket.gethostbyaddr(ip_address)[0]
            except socket.herror:
                hostname = "(unresolved)"
            all_loggers.append(Metalogger(
                id=len(all_loggers) + 1, hostname=hostname,
                ip_address=ip_address, version=f"{v1}.{v2}.{v3}"
            ))
        return all_loggers

    def get_mounts(self) -> List[Mount]:
        all_mounts = []
        data = self._send_and_receive(self.master_host, self.master_port, CLTOMA_SESSION_LIST, MATOCL_SESSION_LIST)
        buffer = bytearray(data)

        stats_count, = struct.unpack(">H", data[:2])
        del buffer[:2]
        while len(buffer) >= 12:
            session_id, ip1, ip2, ip3, ip4, v1, v2, v3 = struct.unpack(">LBBBBHBB", buffer[:12])
            del buffer[:12]
            # Skip info
            logging.debug(f"get_mounts buffer length before info string deserialization: {len(buffer)}")
            mounted_path = self._deserialize_string(buffer, legacy=True)
            logging.debug(f"get_mounts buffer length after info string deserialization: {len(buffer)}")
            logging.debug(f"get_mounts buffer length before path string deserialization: {len(buffer)}")
            root_dir = self._deserialize_string(buffer, legacy=True)
            logging.debug(f"get_mounts buffer length after path string deserialization: {len(buffer)}")

            # TODO: Do the stats and rest of info as well
            del buffer[:27]  # Things like session flags, map root uid etc.
            stats_to_skip = 8 * stats_count
            del buffer[:stats_to_skip]

            ip_address = f"{ip1}.{ip2}.{ip3}.{ip4}"
            try:
                hostname = socket.gethostbyaddr(ip_address)[0]
            except socket.herror:
                hostname = "(unresolved)"
            all_mounts.append(Mount(
                id=len(all_mounts) + 1, session_id=session_id, hostname=hostname,
                ip_address=ip_address, mounted_path=mounted_path, version=f"{v1}.{v2}.{v3}",
                mount_info=""
            ))
            

        # info_data = self._send_and_receive(self.master_host, self.master_port, SAU_CLTOMA_MOUNT_INFO_LIST, SAU_MATOCL_MOUNT_INFO_LIST)
        # info_buffer = bytearray(info_data)
        # mount_info_map = {}

        # if len(info_buffer) < 4: return all_mounts
        # num_entries, = struct.unpack(">L", info_buffer[:4])
        # del info_buffer[:4]

        # for _ in range(num_entries):
        #     if len(info_buffer) < 4: break
        #     session_id, = struct.unpack(">L", info_buffer[:4])
        #     del info_buffer[:4]
        #     info_str = self._deserialize_string(info_buffer)
        #     mount_info_map[session_id] = info_str

        # for mount in all_mounts:
        #     mount.mount_info = mount_info_map.get(mount.session_id, "")
        return all_mounts
