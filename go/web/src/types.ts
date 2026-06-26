// TypeScript mirrors of the Go API models (go/internal/models). Field names
// match the JSON exactly.

export interface SystemInfo {
  version: string;
  memoryUsedBytes: number;
  totalSpaceBytes: number;
  availableSpaceBytes: number;
  trashSpaceBytes: number;
  trashFiles: number;
  reservedSpaceBytes: number;
  reservedFiles: number;
  totalObjects: number;
  directories: number;
  files: number;
  symlinks: number;
  chunks: number;
  allCopies: number;
  regularCopies: number;
}

export interface Server {
  id: number;
  hostname?: string;
  ip: string;
  port: number;
  version: string;
  connected: boolean;
  label: string;
  usedSpaceBytes: number;
  totalSpaceBytes: number;
  chunks: number;
  usedSpaceToDeleteBytes: number;
  totalSpaceToDeleteBytes: number;
  chunksToDelete: number;
  errorCount: number;
}

export interface DiskStats {
  read_bytes: number;
  read_bytes_persecond: number;
  read_ops: number;
  read_usec: number;
  read_usec_avg: number;
  read_usec_max: number;
  read_block_size_avg: number;
  written_bytes: number;
  written_bytes_persecond: number;
  write_ops: number;
  written_usec: number;
  written_usec_avg: number;
  written_usec_max: number;
  written_block_size_avg: number;
  fsync_ops: number;
  fsync_usec: number;
  fsync_usec_avg: number;
  fsync_usec_max: number;
}

export interface Disk {
  path: string;
  status: string;
  last_error: string;
  total_space: number;
  used_space: number;
  chunks: number;
  minute_stats: DiskStats;
  hour_stats: DiskStats;
  day_stats: DiskStats;
}

export interface Metalogger {
  id: number;
  hostname?: string;
  ip: string;
  version: string;
}

export type INotifier = Metalogger;

export interface OperationStats {
  statfs: number;
  getattr: number;
  setattr: number;
  lookup: number;
  mkdir: number;
  rmdir: number;
  symlink: number;
  readlink: number;
  mknod: number;
  unlink: number;
  rename: number;
  link: number;
  readdir: number;
  open: number;
  read: number;
  write: number;
  total: number;
}

export const OP_NAMES: (keyof OperationStats)[] = [
  "statfs", "getattr", "setattr", "lookup", "mkdir", "rmdir", "symlink",
  "readlink", "mknod", "unlink", "rename", "link", "readdir", "open",
  "read", "write", "total",
];

export interface Mount {
  id: number;
  session_id: number;
  hostname: string;
  ip_address: string;
  mounted_path: string;
  version: string;
  root_path: string;
  mount_info: string;
  flags: string;
  root_uid: number;
  root_gid: number;
  map_all_uid: number;
  map_all_gid: number;
  min_goal: number | null;
  max_goal: number | null;
  min_trash_time: number | null;
  max_trash_time: number | null;
  current_op_stats: OperationStats | null;
  last_hour_op_stats: OperationStats | null;
}

export interface Export {
  id: number;
  ip_from: string;
  ip_to: string;
  path: string;
  flags: string;
}

export interface MetadataServer {
  id: number;
  hostname?: string;
  ip: string;
  port: number;
  version: string;
  personality: string;
  state: string;
  metadataVersion: number;
}

export interface FsCheckInfo {
  loopStart: number;
  loopEnd: number;
  files: number;
  underGoalFiles: number;
  missingFiles: number;
  chunks: number;
  underGoalChunks: number;
  missingChunks: number;
  message: string;
}

export interface ChunkOperationsInfo {
  loopStart: number;
  loopEnd: number;
  deleteInvalid: number;
  notDeleteInvalid: number;
  deleteUnused: number;
  notDeleteUnused: number;
  deleteDiskClean: number;
  notDeleteDiskClean: number;
  deleteOverGoal: number;
  notDeleteOverGoal: number;
  replicateUnderGoal: number;
  notReplicateUnderGoal: number;
  rebalance: number;
}

export interface ChunkMatrix {
  matrix: number[][];
}

export interface Goal {
  id: number;
  name: string;
  definition: string;
}

export interface ChunkHealth {
  regular_only: boolean;
  safe: Record<string, number>;
  endangered: Record<string, number>;
  lost: Record<string, number>;
  replication: Record<string, number[]>;
  deletion: Record<string, number[]>;
}
