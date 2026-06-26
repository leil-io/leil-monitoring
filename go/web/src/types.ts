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

export interface DiskError {
  chunkId: number;
  timestamp: number;
}

export interface DiskStats {
  readBytes: number;
  readOps: number;
  readUsec: number;
  readUsecMax: number;
  writeBytes: number;
  writeOps: number;
  writeUsec: number;
  writeUsecMax: number;
  fsyncOps: number;
  fsyncUsec: number;
  fsyncUsecMax: number;
  // verbose=true only (may be null):
  readBytesPerSecond: number | null;
  writeBytesPerSecond: number | null;
  readUsecAvg: number | null;
  writeUsecAvg: number | null;
  fsyncUsecAvg: number | null;
  readBlockSizeAvg: number | null;
  writeBlockSizeAvg: number | null;
}

export interface DiskStatsTriple {
  minute: DiskStats;
  hour: DiskStats;
  day: DiskStats;
}

export interface Disk {
  chunkserver: string;
  path: string;
  status: string;  // enum: "ok" | "marked_for_removal" | "damaged" | ...
  flags: number;
  lastError: DiskError | null;
  totalSpaceBytes: number;
  usedSpaceBytes: number;
  chunks: number;
  stats: DiskStatsTriple;
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
  sessionId: number;
  ip: string;
  hostname?: string;
  version: string;
  rootPath: string;
  mountedPath: string;
  mountInfo: string;
  flags: string[];
  rootUid: number;
  rootGid: number;
  mapAllUid: number;
  mapAllGid: number;
  minGoal: number;
  maxGoal: number;
  minTrashTime: number;
  maxTrashTime: number;
  currentOpStats: OperationStats;
  lastHourOpStats: OperationStats;
}

export interface Export {
  id: number;
  ipFrom: string;
  ipTo: string;
  path: string;
  flags: string[];
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
