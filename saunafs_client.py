import socket
import struct
import select
import logging
from typing import List, Tuple, Dict
from models import (SystemInfo,
                    Server,
                    Disk,
                    Metalogger,
                    Mount,
                    Export,
                    MetadataServer,
                    FsCheckInfo,
                    ChunkOperationsInfo,
                    OperationStats,
                    ChunkMatrix)


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
CLTOMA_EXPORTS_INFO = (PROTO_BASE + 520)
MATOCL_EXPORTS_INFO = (PROTO_BASE + 521)
CLTOMA_FSTEST_INFO = (PROTO_BASE + 512)
MATOCL_FSTEST_INFO = (PROTO_BASE + 513)
CLTOMA_CHUNKSTEST_INFO = (PROTO_BASE + 514)
MATOCL_CHUNKSTEST_INFO = (PROTO_BASE + 515)
CLTOMA_CHUNKS_MATRIX = (PROTO_BASE + 516)
MATOCL_CHUNKS_MATRIX = (PROTO_BASE + 517)


CUTOAN_CHART = (PROTO_BASE + 504)
ANTOCU_CHART = (PROTO_BASE + 505)

SAU_CLTOMA_CSERV_LIST = 1549
SAU_MATOCL_CSERV_LIST = 1550
SAU_CLTOMA_METADATASERVERS_LIST = 1522
SAU_MATOCL_METADATASERVERS_LIST = 1523
SAU_CLTOMA_METADATASERVER_STATUS = 1545
SAU_MATOCL_METADATASERVER_STATUS = 1546
SAU_CLTOMA_HOSTNAME = 1551
SAU_MATOCL_HOSTNAME = 1552
SAU_CLTOMA_MOUNT_INFO_LIST = 1609
SAU_MATOCL_MOUNT_INFO_LIST = 1610


# Message type constants
INFO = (CLTOMA_INFO, MATOCL_INFO)
CSERV_LIST = (CLTOMA_CSERV_LIST, MATOCL_CSERV_LIST)
SAU_CSERV_LIST = (SAU_CLTOMA_CSERV_LIST, SAU_MATOCL_CSERV_LIST)
HDD_LIST = (CLTOCS_HDD_LIST_V2, MATOCL_HDD_LIST_V2)
MLOG_LIST = (CLTOMA_MLOG_LIST, MATOCL_MLOG_LIST)
SESSION_LIST = (CLTOMA_SESSION_LIST, MATOCL_SESSION_LIST)
CHART = (CUTOAN_CHART, ANTOCU_CHART)
EXPORTS_INFO = (CLTOMA_EXPORTS_INFO, MATOCL_EXPORTS_INFO)
MOUNT_INFO_LIST = (SAU_CLTOMA_MOUNT_INFO_LIST, SAU_MATOCL_MOUNT_INFO_LIST)

class SaunaFSClient:
    def __init__(self, masterHost: str, masterPort: int):
        self.masterHost = masterHost
        self.masterPort = masterPort
        self.masterVersion = self._GetMasterVersion()

    def _MySend(self, sock: socket.socket, msg: bytes):
        totalsent = 0
        logging.debug(f"Sending message: {msg}")
        while totalsent < len(msg):
            sent = sock.send(msg[totalsent:])
            if sent == 0:
                raise RuntimeError("Socket connection broken")
            totalsent += sent

    def _MyRecv(self, sock: socket.socket, length: int) -> bytes:
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

    def _SendAndReceive(self, host: str, port: int, msg: Tuple[int, int], payload: bytes = b'', version: int = 0) -> bytes:
        cmd, expected = msg
        isV2 = cmd > 1000

        if isV2:
            length = 4 + len(payload)
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
            self._MySend(s, request)
            header = self._MyRecv(s, 8)
            respCmd, respLength = struct.unpack(">LL", header)
            logging.debug(f"Header received: cmd={respCmd}, length={respLength}")

            if respCmd != expected:
                raise RuntimeError(f"Received wrong response command: {respCmd}, expected {expected}")

            respPayload = self._MyRecv(s, respLength)
            if isV2:
                if len(respPayload) < 4:
                    raise ValueError("V2 response payload is too short for version field")
                respVersion = struct.unpack(">L", respPayload[:4])[0]
                logging.debug(f"V2 response version: {respVersion}")
                return respPayload[4:]
            else:
                return respPayload

    def _DeserializeString(self, buffer: bytearray, legacy: bool = False) -> str:
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

    def _GetMasterVersion(self) -> Tuple[int, int, int]:
        try:
            data = self._SendAndReceive(self.masterHost, self.masterPort, INFO)
            if len(data) >= 4:
                v1, v2, v3 = struct.unpack(">HBB", data[:4])
                return (v1, v2, v3)
            return (0, 0, 0)
        except Exception:
            return (0, 0, 0)

    def GetSystemInfo(self) -> SystemInfo:
        data = self._SendAndReceive(self.masterHost, self.masterPort, INFO)
        if len(data) == 80:
            v1, v2, v3, mem, total, avail, trspace, trfiles, respace, refiles, nodes, dirs, files, symlinks, chunks, allcopies, tdcopies = struct.unpack(">HBBQQQQLQLLLLLLLL", data)
            return SystemInfo(
                version=f"{v1}.{v2}.{v3}", ram_used=mem, total_space=total, avail_space=avail,
                trash_space=trspace, trash_files=trfiles, reserved_space=respace, reserved_files=refiles,
                total_objects=nodes, directories=dirs, files=files, symlinks=symlinks, chunks=chunks,
                all_copies=allcopies, regular_copies=tdcopies,
            )
        raise RuntimeError("Could not decode system info from master.")

    def GetServers(self) -> List[Server]:
        servers = []
        cmd = SAU_CSERV_LIST
        payload = b'\x00'

        data = self._SendAndReceive(self.masterHost, self.masterPort, cmd, payload)

        buffer = bytearray(data)
        if len(buffer) < 4:
            return []
        vectorSize, = struct.unpack(">L", buffer[:4])
        logging.debug(f"GetServers vector_size: {vectorSize}")
        del buffer[:4]

        for i in range(int(vectorSize)):
            if len(buffer) < 58:
                break
            disconnected, v1, v2, v3, ip1, ip2, ip3, ip4, port, used, total, chunks, tdused, tdtotal, tdchunks, errcnt = struct.unpack(">BBBBBBBBHQQLQQLL", buffer[:54])
            del buffer[:54]
            label = self._DeserializeString(buffer)

            ipAddress = f"{ip1}.{ip2}.{ip3}.{ip4}"
            try:
                hostname = socket.gethostbyaddr(ipAddress)[0]
            except socket.herror:
                hostname = "(unresolved)"

            servers.append(Server(
                id=i + 1, hostname=hostname, ip_address=ipAddress, port=port,
                version=f"{v1}.{v2}.{v3}", is_disconnected=bool(disconnected),
                label=label, used_space=used, total_space=total, chunks=chunks,
                used_space_tobedeleted=tdused, total_space_tobedeleted=tdtotal,
                chunks_tobedeleted=tdchunks, error_count=errcnt
            ))
        return servers

    def GetDisks(self) -> List[Disk]:
        allDisks = []
        for server in self.GetServers():
            if server.is_disconnected: continue
            try:
                data = self._SendAndReceive(server.ip_address, server.port, HDD_LIST)
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

                    lastError = "no errors"
                    if errtime > 0:
                        lastError = f"{errtime} on chunk: {errchunkid}"

                    allDisks.append(Disk(
                        path=f"{server.hostname}:{path}", status=status, last_error=lastError,
                        total_space=total, used_space=used, chunks=chunkscnt
                    ))
            except Exception:
                continue
        return allDisks

    def GetChart(self, host: str, port: int, chart_id: int) -> bytes:
        payload = struct.pack(">L", chart_id)
        return self._SendAndReceive(host, port, CHART, payload)

    def GetMetaloggers(self) -> List[Metalogger]:
        allLoggers = []
        data = self._SendAndReceive(self.masterHost, self.masterPort, MLOG_LIST)
        buffer = bytearray(data)
        while len(buffer) >= 8:
            v1, v2, v3, ip1, ip2, ip3, ip4 = struct.unpack(">HBBBBBB", buffer[:8])
            del buffer[:8]
            ipAddress = f"{ip1}.{ip2}.{ip3}.{ip4}"
            try:
                hostname = socket.gethostbyaddr(ipAddress)[0]
            except socket.herror:
                hostname = "(unresolved)"
            allLoggers.append(Metalogger(
                id=len(allLoggers) + 1, hostname=hostname,
                ip_address=ipAddress, version=f"{v1}.{v2}.{v3}"
            ))
        return allLoggers

    def _get_mounts_info(self) -> Dict[int, str]:
        mounts_info = {}
        try:
            data = self._SendAndReceive(self.masterHost, self.masterPort, MOUNT_INFO_LIST)
            buffer = bytearray(data)
            vector_size, = struct.unpack(">L", buffer[:4])
            del buffer[:4]
            for _ in range(vector_size):
                session_id, = struct.unpack(">L", buffer[:4])
                del buffer[:4]
                mount_info = self._DeserializeString(buffer)
                mounts_info[session_id] = mount_info
        except Exception as e:
            logging.warning(f"Could not get extra mount info: {e}")
        return mounts_info

    def GetMounts(self) -> List[Mount]:
        allMounts = []
        extra_mount_info = self._get_mounts_info()
        # Send vmode=1 to request extended information
        payload = struct.pack(">B", 1)
        data = self._SendAndReceive(self.masterHost, self.masterPort, SESSION_LIST, payload)
        buffer = bytearray(data)

        statsCount, = struct.unpack(">H", buffer[:2])
        del buffer[:2]

        while len(buffer) > 0:
            sessionId, ip1, ip2, ip3, ip4, v1, v2, v3 = struct.unpack(">LBBBBHBB", buffer[:12])
            del buffer[:12]

            root_path = self._DeserializeString(buffer, legacy=True)
            mountedPath = self._DeserializeString(buffer, legacy=True)

            sesflags, rootuid, rootgid, mapalluid, mapallgid = struct.unpack(">BLLLL", buffer[:17])
            del buffer[:17]

            mingoal, maxgoal, mintrashtime, maxtrashtime = None, None, None, None
            # The vmode we sent means these fields should be present
            mingoal, maxgoal, mintrashtime, maxtrashtime = struct.unpack(">BBLL", buffer[:10])
            del buffer[:10]

            current_op_stats_list = []
            for _ in range(statsCount):
                stat, = struct.unpack(">L", buffer[:4])
                current_op_stats_list.append(stat)
                del buffer[:4]

            current_op_stats = self.getOperationStatsFromList(current_op_stats_list)

            last_hour_op_stats_list = []
            for _ in range(statsCount):
                stat, = struct.unpack(">L", buffer[:4])
                last_hour_op_stats_list.append(stat)
                del buffer[:4]

            last_hour_op_stats = self.getOperationStatsFromList(current_op_stats_list)


            ipAddress = f"{ip1}.{ip2}.{ip3}.{ip4}"
            try:
                hostname = socket.gethostbyaddr(ipAddress)[0]
            except socket.herror:
                hostname = "(unresolved)"

            flags = []
            if sesflags & 1: flags.append("ro")
            if sesflags & 2: flags.append("dynamic_ip")
            if sesflags & 4: flags.append("ignore_gid")
            if sesflags & 8: flags.append("quota_admin")
            if sesflags & 16: flags.append("map_all")

            mount_info = ""
            if sessionId in extra_mount_info:
                mount_info = "\n" + extra_mount_info[sessionId]

            allMounts.append(Mount(
                id=len(allMounts) + 1, session_id=sessionId, hostname=hostname,
                ip_address=ipAddress, root_path=root_path, mounted_path=mountedPath, version=f"{v1}.{v2}.{v3}",
                mount_info=mount_info, flags=", ".join(flags), root_uid=rootuid, root_gid=rootgid,
                map_all_uid=mapalluid, map_all_gid=mapallgid, min_goal=mingoal, max_goal=maxgoal,
                min_trash_time=mintrashtime, max_trash_time=maxtrashtime,
                current_op_stats=current_op_stats, last_hour_op_stats=last_hour_op_stats
            ))
        return allMounts

    def GetExports(self) -> List[Export]:
        allExports = []
        data = self._SendAndReceive(self.masterHost, self.masterPort, EXPORTS_INFO)
        buffer = bytearray(data)

        i = 1
        while len(buffer) >= 12:
            fip1, fip2, fip3, fip4, tip1, tip2, tip3, tip4, pleng = struct.unpack(">BBBBBBBBL", buffer[:12])
            del buffer[:12]

            path = buffer[:pleng].decode('utf-8', errors='replace')
            del buffer[:pleng]

            # This part of the protocol seems to have many versions.
            # This is a simplified parser for a common version.
            if len(buffer) >= 22:
                v1, v2, v3, exportflags, sesflags, rootuid, rootgid, mapalluid, mapallgid = struct.unpack(">HBBBBLLLL", buffer[:22])
                del buffer[:22]
            else:
                break

            ipFrom = f"{fip1}.{fip2}.{fip3}.{fip4}"
            ipTo = f"{tip1}.{tip2}.{tip3}.{tip4}"

            flags = []
            if sesflags & 1: flags.append("ro")
            else: flags.append("rw")
            if sesflags & 2: flags.append("dynamic_ip")
            if sesflags & 4: flags.append("ignore_gid")
            if sesflags & 8: flags.append("quota_admin")
            if sesflags & 16: flags.append("map_all")

            allExports.append(Export(
                id=i,
                ip_from=ipFrom,
                ip_to=ipTo,
                path=path,
                flags=", ".join(flags)
            ))
            i += 1
        return allExports

    def GetFsCheckInfo(self) -> FsCheckInfo:
        data = self._SendAndReceive(self.masterHost, self.masterPort, (CLTOMA_FSTEST_INFO, MATOCL_FSTEST_INFO))
        buffer = bytearray(data)
        loop_start, loop_end, files, ugfiles, mfiles, chunks, ugchunks, mchunks, msgbuffleng = struct.unpack(">LLLLLLLLL", buffer[:36])
        del buffer[:36]
        message = buffer.decode('utf-8', errors='replace')
        
        return FsCheckInfo(
            loop_start=loop_start,
            loop_end=loop_end,
            files=files,
            under_goal_files=ugfiles,
            missing_files=mfiles,
            chunks=chunks,
            under_goal_chunks=ugchunks,
            missing_chunks=mchunks,
            message=message
        )

    def GetChunkOperationsInfo(self) -> ChunkOperationsInfo:
        data = self._SendAndReceive(self.masterHost, self.masterPort, (CLTOMA_CHUNKSTEST_INFO, MATOCL_CHUNKSTEST_INFO))
        buffer = bytearray(data)
        loop_start, loop_end, del_invalid, ndel_invalid, del_unused, ndel_unused, del_dclean, ndel_dclean, del_ogoal, ndel_ogoal, rep_ugoal, nrep_ugoal, rebalnce = struct.unpack(">LLLLLLLLLLLLL", buffer[:52])
        
        return ChunkOperationsInfo(
            loop_start=loop_start,
            loop_end=loop_end,
            delete_invalid=del_invalid,
            not_delete_invalid=ndel_invalid,
            delete_unused=del_unused,
            not_delete_unused=ndel_unused,
            delete_disk_clean=del_dclean,
            not_delete_disk_clean=ndel_dclean,
            delete_over_goal=del_ogoal,
            not_delete_over_goal=ndel_ogoal,
            replicate_under_goal=rep_ugoal,
            not_replicate_under_goal=nrep_ugoal,
            rebalance=rebalnce
        )

    def GetChunkMatrix(self) -> ChunkMatrix:
        payload = struct.pack(">B", 0)
        data = self._SendAndReceive(self.masterHost, self.masterPort, (CLTOMA_CHUNKS_MATRIX, MATOCL_CHUNKS_MATRIX), payload)
        buffer = bytearray(data)
        
        matrix = []
        for _ in range(11):
            row = list(struct.unpack(">LLLLLLLLLLL", buffer[:44]))
            matrix.append(row)
            del buffer[:44]
            
        return ChunkMatrix(matrix=matrix)

    def GetMetadataServers(self) -> List[MetadataServer]:
        servers = []
        
        # Add the master server
        master_ip = socket.gethostbyname(self.masterHost)
        master_v1, master_v2, master_v3 = self.masterVersion
        master_personality, master_state, master_metadata_version = self.GetMetadataServerStatus(self.masterHost, self.masterPort)
        
        servers.append(MetadataServer(
            id=1,
            hostname=self.masterHost,
            ip_address=master_ip,
            port=self.masterPort,
            version=f"{master_v1}.{master_v2}.{master_v3}",
            personality=master_personality,
            state=master_state,
            metadata_version=master_metadata_version
        ))

        # Get shadow servers
        request = struct.pack(">LLL", SAU_CLTOMA_METADATASERVERS_LIST, 4, 0)
        data = self._SendAndReceive(self.masterHost, self.masterPort, (SAU_CLTOMA_METADATASERVERS_LIST, SAU_MATOCL_METADATASERVERS_LIST), b"")
        buffer = bytearray(data)
        master_version, = struct.unpack(">L", buffer[:4])
        del buffer[:4]
        vector_size, = struct.unpack(">L", buffer[:4])
        del buffer[:4]
        logging.debug(f"GetMetadataServers vector_size: {vector_size}")

        for i in range(vector_size):
            ip, port, v1, v2, v3 = struct.unpack(">LHHBB", buffer[:10])
            del buffer[:10]
            ip_str = socket.inet_ntoa(struct.pack(">L", ip))
            try:
                hostname = socket.gethostbyaddr(ip_str)[0]
            except socket.herror:
                hostname = "(unresolved)"
            
            personality, state, metadata_version = self.GetMetadataServerStatus(ip_str, port)

            servers.append(MetadataServer(
                id=i + 2,
                hostname=hostname,
                ip_address=ip_str,
                port=port,
                version=f"{v1}.{v2}.{v3}",
                personality=personality,
                state=state,
                metadata_version=metadata_version
            ))
        
        return servers

    def GetMetadataServerStatus(self, host: str, port: int) -> Tuple[str, str, int]:
        payload = struct.pack(">L", 0)
        data = self._SendAndReceive(host, port, (SAU_CLTOMA_METADATASERVER_STATUS, SAU_MATOCL_METADATASERVER_STATUS), payload)
        buffer = bytearray(data)
        _, status, metadata_version = struct.unpack(">LBQ", buffer)

        if status == 1:
            return ("master", "running", metadata_version)
        elif status == 2:
            return ("shadow", "connected", metadata_version)
        elif status == 3:
            return ("shadow", "disconnected", metadata_version)
        else:
            return ("(unknown)", "(unknown)", metadata_version)

    def getOperationStatsFromList(self, list: List[int]) -> OperationStats:
        stats = OperationStats(
            statfs=list[0],
            getattr=list[1],
            setattr=list[2],
            lookup=list[3],
            mkdir=list[4],
            rmdir=list[5],
            symlink=list[6],
            readlink=list[7],
            mknod=list[8],
            unlink=list[9],
            rename=list[10],
            link=list[11],
            readdir=list[12],
            open=list[13],
            read=list[14],
            write=list[15],
            total=sum(list)
        )
        return stats
