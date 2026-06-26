# Phase 2 Field Map: Legacy SPA shapes → Canonical leilfs-api shapes

Generated: 2026-06-26
Sources:
- Legacy models: `~/Work/leilfs-monitoring/go/leilfs/models/`
- Adapter: `~/Work/leilfs-monitoring/go/internal/apiclient/apiclient.go`
- Canonical models: `~/Work/leilfs-api/internal/service/models.go`
- SPA types: `~/Work/leilfs-monitoring/go/web/src/types.ts`
- SPA API calls: `~/Work/leilfs-monitoring/go/web/src/api.ts`
- SPA components: `~/Work/leilfs-monitoring/go/web/src/components/`

---

## Endpoint Path Map

| SPA legacy call (api.ts) | Go handler path | Canonical leilfs-api path |
|--------------------------|-----------------|---------------------------|
| `/api/info`              | `GET /api/info` | `GET /api/v1/cluster`     |
| `/api/chunkservers`      | `GET /api/chunkservers` | `GET /api/v1/chunkservers` |
| `/api/disks`             | `GET /api/disks` | `GET /api/v1/disks?verbose=true` |
| `/api/mounts`            | `GET /api/mounts` | `GET /api/v1/mounts` |
| `/api/metadataservers`   | `GET /api/metadataservers` | `GET /api/v1/metadata-servers` |
| `/api/inotifiers`        | `GET /api/inotifiers` | `GET /api/v1/inotifiers` |
| `/api/fscheckinfo`       | `GET /api/fscheckinfo` | `GET /api/v1/cluster/fs-check` |
| `/api/chunkoperationsinfo` | `GET /api/chunkoperationsinfo` | `GET /api/v1/cluster/chunk-operations` |
| `/api/chunkmatrix`       | `GET /api/chunkmatrix` | `GET /api/v1/cluster/chunk-matrix` |
| `/api/goals`             | `GET /api/goals` | `GET /api/v1/goals` |
| `/api/chunkhealth`       | `GET /api/chunkhealth` | `GET /api/v1/cluster/chunk-health` |
| `/api/metaloggers`       | `GET /api/metaloggers` | `GET /api/v1/metaloggers` |
| `/api/exports`           | `GET /api/exports` | `GET /api/v1/exports` |

Notes:
- `/api/disks` must be called with `?verbose=true` to get the derived stats fields the SPA relies on
  (readBytesPerSecond, writeBytesPerSecond, readUsecAvg, writeUsecAvg, fsyncUsecAvg, readBlockSizeAvg, writeBlockSizeAvg).
  Without `?verbose=true` those fields are absent/null and the SPA will break.
- Hostname resolution: append `?resolve=true` when LEILFS_RESOLVE_HOSTNAMES is set (same semantics as apiclient.resolve).

---

## Global JSON Casing Difference

**Legacy shape** (what the SPA currently consumes): **snake_case** JSON tags.
**Canonical shape** (leilfs-api): **camelCase** JSON tags.

This affects every field in every interface in `types.ts`. Renaming is not
selective — it is a wholesale casing migration across the entire SPA type layer.

---

## 1. /api/v1/cluster → SystemInfo / ClusterSummary

### Legacy shape (`go/leilfs/models/models.go:21-37`, JSON tags)

```
SystemInfo {
  version         string   json:"version"
  ram_used        uint64   json:"ram_used"
  total_space     uint64   json:"total_space"
  avail_space     uint64   json:"avail_space"
  trash_space     uint64   json:"trash_space"
  trash_files     uint32   json:"trash_files"
  reserved_space  uint64   json:"reserved_space"
  reserved_files  uint32   json:"reserved_files"
  total_objects   uint32   json:"total_objects"
  directories     uint32   json:"directories"
  files           uint32   json:"files"
  symlinks        uint32   json:"symlinks"
  chunks          uint32   json:"chunks"
  all_copies      uint32   json:"all_copies"
  regular_copies  uint32   json:"regular_copies"
}
```

### Canonical shape (`leilfs-api/internal/service/models.go:24-40`, JSON tags)

```
ClusterSummary {
  version              string   json:"version"
  memoryUsedBytes      uint64   json:"memoryUsedBytes"
  totalSpaceBytes      uint64   json:"totalSpaceBytes"
  availableSpaceBytes  uint64   json:"availableSpaceBytes"
  trashSpaceBytes      uint64   json:"trashSpaceBytes"
  trashFiles           uint64   json:"trashFiles"
  reservedSpaceBytes   uint64   json:"reservedSpaceBytes"
  reservedFiles        uint64   json:"reservedFiles"
  totalObjects         uint64   json:"totalObjects"
  directories          uint64   json:"directories"
  files                uint64   json:"files"
  symlinks             uint64   json:"symlinks"
  chunks               uint64   json:"chunks"
  allCopies            uint64   json:"allCopies"
  regularCopies        uint64   json:"regularCopies"
}
```

### Field mapping (legacy ← canonical)

| Legacy field (snake_case) | Canonical field (camelCase) | Notes |
|---------------------------|-----------------------------|-------|
| `version`                 | `version`                   | Same value, no conversion |
| `ram_used`                | `memoryUsedBytes`           | RENAMED; bytes uint64 (legacy was also uint64) |
| `total_space`             | `totalSpaceBytes`           | RENAMED |
| `avail_space`             | `availableSpaceBytes`       | RENAMED |
| `trash_space`             | `trashSpaceBytes`           | RENAMED |
| `trash_files`             | `trashFiles`                | RENAMED; was uint32, canonical is uint64 (range compatible) |
| `reserved_space`          | `reservedSpaceBytes`        | RENAMED |
| `reserved_files`          | `reservedFiles`             | RENAMED; was uint32, canonical is uint64 |
| `total_objects`           | `totalObjects`              | RENAMED; was uint32, canonical is uint64 |
| `directories`             | `directories`               | RENAMED (casing); was uint32, canonical is uint64 |
| `files`                   | `files`                     | RENAMED (casing); was uint32, canonical is uint64 |
| `symlinks`                | `symlinks`                  | RENAMED (casing); was uint32, canonical is uint64 |
| `chunks`                  | `chunks`                    | RENAMED (casing); was uint32, canonical is uint64 |
| `all_copies`              | `allCopies`                 | RENAMED |
| `regular_copies`          | `regularCopies`             | RENAMED |

**Gaps**: None. All 15 legacy fields have canonical sources.
**Dropped canonical fields**: None.

### SPA consumption

- TS type: `types.ts:4-20` — `interface SystemInfo`
- Component: `InfoSection.tsx:54-68` — accesses all 15 fields directly
  - `d.info.version`, `d.info.ram_used`, `d.info.total_space`, `d.info.avail_space`,
    `d.info.trash_space`, `d.info.trash_files`, `d.info.reserved_space`,
    `d.info.reserved_files`, `d.info.total_objects`, `d.info.directories`,
    `d.info.files`, `d.info.symlinks`, `d.info.chunks`, `d.info.all_copies`,
    `d.info.regular_copies`

**SPA changes required**: All 14 fields with snake_case must be renamed to camelCase in `types.ts` and `InfoSection.tsx`. `ram_used` also needs special rename to `memoryUsedBytes`, `total_space`→`totalSpaceBytes`, `avail_space`→`availableSpaceBytes`, `trash_space`→`trashSpaceBytes`, `reserved_space`→`reservedSpaceBytes`.

---

## 2. /api/v1/chunkservers → Server / Chunkserver

### Legacy shape (`go/leilfs/models/servers.go:5-21`, JSON tags)

```
Server {
  id                      int     json:"id"
  hostname                string  json:"hostname"
  ip_address              string  json:"ip_address"
  port                    uint16  json:"port"
  version                 string  json:"version"
  is_disconnected         bool    json:"is_disconnected"
  label                   string  json:"label"
  used_space              uint64  json:"used_space"
  total_space             uint64  json:"total_space"
  chunks                  uint32  json:"chunks"
  used_space_tobedeleted  uint64  json:"used_space_tobedeleted"
  total_space_tobedeleted uint64  json:"total_space_tobedeleted"
  chunks_tobedeleted      uint32  json:"chunks_tobedeleted"
  error_count             uint32  json:"error_count"
}
```

### Canonical shape (`leilfs-api/internal/service/models.go:287-302`, JSON tags)

```
Chunkserver {
  id                       uint32  json:"id"
  ip                       string  json:"ip"
  port                     uint16  json:"port"
  hostname                 string  json:"hostname,omitempty"
  version                  string  json:"version"
  connected                bool    json:"connected"
  label                    string  json:"label"
  usedSpaceBytes           uint64  json:"usedSpaceBytes"
  totalSpaceBytes          uint64  json:"totalSpaceBytes"
  chunks                   uint64  json:"chunks"
  usedSpaceToDeleteBytes   uint64  json:"usedSpaceToDeleteBytes"
  totalSpaceToDeleteBytes  uint64  json:"totalSpaceToDeleteBytes"
  chunksToDelete           uint64  json:"chunksToDelete"
  errorCount               uint32  json:"errorCount"
}
```

### Field mapping (legacy ← canonical)

| Legacy field             | Canonical field           | Notes |
|--------------------------|---------------------------|-------|
| `id`                     | `id`                      | RENAMED (casing only); uint32→int, safe |
| `hostname`               | `hostname`                | Same; omitempty on canonical (empty string when resolve=false) |
| `ip_address`             | `ip`                      | RENAMED: `ip_address` → `ip` |
| `port`                   | `port`                    | Same |
| `version`                | `version`                 | Same |
| `is_disconnected`        | `connected`               | INVERTED: `is_disconnected = !connected` |
| `label`                  | `label`                   | Same |
| `used_space`             | `usedSpaceBytes`          | RENAMED |
| `total_space`            | `totalSpaceBytes`         | RENAMED |
| `chunks`                 | `chunks`                  | RENAMED (casing); canonical is uint64, legacy was uint32 |
| `used_space_tobedeleted` | `usedSpaceToDeleteBytes`  | RENAMED |
| `total_space_tobedeleted`| `totalSpaceToDeleteBytes` | RENAMED |
| `chunks_tobedeleted`     | `chunksToDelete`          | RENAMED |
| `error_count`            | `errorCount`              | RENAMED |

**Gaps**: None.
**Dropped canonical fields**: None (canonical has same 14 fields).

### SPA consumption

- TS type: `types.ts:22-37` — `interface Server`
- Component: `ServersSection.tsx:68-98` — accesses:
  - `s.is_disconnected`, `s.id`, `s.hostname`, `s.ip_address`, `s.port`,
    `s.version`, `s.label`, `s.chunks`, `s.used_space`, `s.total_space`,
    `s.chunks_tobedeleted`, `s.used_space_tobedeleted`, `s.total_space_tobedeleted`
  - Note: `error_count` is in the type but NOT rendered in the current component template

**SPA changes required**: Rename `ip_address`→`ip`, invert `is_disconnected`→use `!connected` or rename to `connected` and negate checks, rename all space/count fields to camelCase. `error_count`→`errorCount`.

---

## 3. /api/v1/disks → Disk / Disk

### Legacy shape

**Disk** (`go/leilfs/models/disk.go:132-142`)
```
Disk {
  path          string    json:"path"        -- NOTE: legacy = "<chunkserver>:<path>"
  status        string    json:"status"      -- human strings: "OK", "Marked for removal", "Damaged", etc.
  last_error    string    json:"last_error"  -- human string: "No errors" / "NNN on chunk: MMM" / "Read/Write error"
  total_space   uint64    json:"total_space"
  used_space    uint64    json:"used_space"
  chunks        uint32    json:"chunks"
  minute_stats  DiskStats json:"minute_stats"
  hour_stats    DiskStats json:"hour_stats"
  day_stats     DiskStats json:"day_stats"
}
```

**DiskStats** (`go/leilfs/models/disk.go:14-36`)
```
DiskStats {
  read_bytes              uint64  json:"read_bytes"
  read_bytes_persecond    float64 json:"read_bytes_persecond"
  read_ops                uint32  json:"read_ops"
  read_usec               uint64  json:"read_usec"
  read_usec_avg           float64 json:"read_usec_avg"
  read_usec_max           uint32  json:"read_usec_max"
  read_block_size_avg     float64 json:"read_block_size_avg"
  written_bytes           uint64  json:"written_bytes"
  written_bytes_persecond float64 json:"written_bytes_persecond"
  write_ops               uint32  json:"write_ops"
  written_usec            uint64  json:"written_usec"
  written_usec_avg        float64 json:"written_usec_avg"
  written_usec_max        uint32  json:"written_usec_max"
  written_block_size_avg  float64 json:"written_block_size_avg"
  fsync_ops               uint32  json:"fsync_ops"
  fsync_usec              uint64  json:"fsync_usec"
  fsync_usec_avg          float64 json:"fsync_usec_avg"
  fsync_usec_max          uint32  json:"fsync_usec_max"
}
```

### Canonical shape (`leilfs-api/internal/service/models.go:304-358`)

**Disk**
```
Disk {
  chunkserver      string          json:"chunkserver"
  path             string          json:"path"       -- just the path, NO chunkserver prefix
  status           string          json:"status"     -- enum: "ok","marked_for_removal","damaged",
                                                     --   "damaged_marked_for_removal","scanning",
                                                     --   "scanning_marked_for_removal","errors_reported"
  flags            uint8           json:"flags"
  lastError        *DiskError      json:"lastError"  -- null OR {chunkId, timestamp}
  totalSpaceBytes  uint64          json:"totalSpaceBytes"
  usedSpaceBytes   uint64          json:"usedSpaceBytes"
  chunks           uint64          json:"chunks"
  stats            DiskStatsTriple json:"stats"      -- {minute, hour, day}
}
```

**DiskError** (`leilfs-api/internal/service/models.go:304-309`)
```
DiskError {
  chunkId    uint64  json:"chunkId"
  timestamp  int64   json:"timestamp"
}
```

**DiskStats** (`leilfs-api/internal/service/models.go:316-336`)
```
DiskStats {
  readBytes            uint64   json:"readBytes"
  readOps              uint64   json:"readOps"
  readUsec             uint64   json:"readUsec"
  readUsecMax          uint64   json:"readUsecMax"
  writeBytes           uint64   json:"writeBytes"
  writeOps             uint64   json:"writeOps"
  writeUsec            uint64   json:"writeUsec"
  writeUsecMax         uint64   json:"writeUsecMax"
  fsyncOps             uint64   json:"fsyncOps"
  fsyncUsec            uint64   json:"fsyncUsec"
  fsyncUsecMax         uint64   json:"fsyncUsecMax"
  -- verbose=true only (omitempty when absent):
  readBytesPerSecond   *float64 json:"readBytesPerSecond,omitempty"
  writeBytesPerSecond  *float64 json:"writeBytesPerSecond,omitempty"
  readUsecAvg          *float64 json:"readUsecAvg,omitempty"
  writeUsecAvg         *float64 json:"writeUsecAvg,omitempty"
  fsyncUsecAvg         *float64 json:"fsyncUsecAvg,omitempty"
  readBlockSizeAvg     *float64 json:"readBlockSizeAvg,omitempty"
  writeBlockSizeAvg    *float64 json:"writeBlockSizeAvg,omitempty"
}
```

**DiskStatsTriple** (`leilfs-api/internal/service/models.go:338-343`)
```
DiskStatsTriple {
  minute  DiskStats json:"minute"
  hour    DiskStats json:"hour"
  day     DiskStats json:"day"
}
```

### Field mapping (legacy ← canonical)

**Disk-level:**

| Legacy field  | Canonical field      | Notes |
|---------------|----------------------|-------|
| `path`        | `chunkserver` + `path` | COMPOSITE: legacy = `d.Chunkserver + ":" + d.Path`. SPA must join or use two fields. **STRUCTURAL CHANGE** |
| `status`      | `status`             | VALUE CHANGED: legacy humanized ("OK", "Marked for removal", "Damaged") → canonical enum ("ok", "marked_for_removal", "damaged", "damaged_marked_for_removal", "scanning", "scanning_marked_for_removal", "errors_reported"). SPA `statusClass()` uses `.toLowerCase().includes()` so lowercase canonical values still work, BUT the SPA renders `disk.status` as text directly — users will see enum values instead of human strings |
| `last_error`  | `lastError` (object or null) | STRUCTURAL CHANGE: legacy = human string ("No errors", "NNN on chunk: MMM", "Read/Write error") → canonical = `null` or `{chunkId, timestamp}`. SPA checks `disk.last_error.toLowerCase().includes("no errors")` — this will break. SPA must reconstruct: null→"No errors", object→format timestamp+chunkId |
| `total_space` | `totalSpaceBytes`    | RENAMED |
| `used_space`  | `usedSpaceBytes`     | RENAMED |
| `chunks`      | `chunks`             | RENAMED (casing) |
| `minute_stats`| `stats.minute`       | RESTRUCTURED: legacy = flat on Disk, canonical = nested under `stats.minute` |
| `hour_stats`  | `stats.hour`         | RESTRUCTURED: nested under `stats.hour` |
| `day_stats`   | `stats.day`          | RESTRUCTURED: nested under `stats.day` |
| (none)        | `flags`              | NEW in canonical — not in legacy shape. SPA can ignore |

**DiskStats-level:**

| Legacy field              | Canonical field       | Notes |
|---------------------------|-----------------------|-------|
| `read_bytes`              | `readBytes`           | RENAMED |
| `read_bytes_persecond`    | `readBytesPerSecond`  | RENAMED; always float64 in legacy, pointer/omitempty in canonical (needs `verbose=true`) |
| `read_ops`                | `readOps`             | RENAMED; legacy uint32, canonical uint64 |
| `read_usec`               | `readUsec`            | RENAMED |
| `read_usec_avg`           | `readUsecAvg`         | RENAMED; always float64 in legacy, pointer in canonical (verbose=true) |
| `read_usec_max`           | `readUsecMax`         | RENAMED; legacy uint32, canonical uint64 |
| `read_block_size_avg`     | `readBlockSizeAvg`    | RENAMED; always float64 in legacy, pointer in canonical (verbose=true) |
| `written_bytes`           | `writeBytes`          | RENAMED: `written_bytes` → `writeBytes` |
| `written_bytes_persecond` | `writeBytesPerSecond` | RENAMED; `written_bytes_persecond` → `writeBytesPerSecond`; pointer in canonical |
| `write_ops`               | `writeOps`            | RENAMED |
| `written_usec`            | `writeUsec`           | RENAMED: `written_usec` → `writeUsec` |
| `written_usec_avg`        | `writeUsecAvg`        | RENAMED; pointer in canonical |
| `written_usec_max`        | `writeUsecMax`        | RENAMED: `written_usec_max` → `writeUsecMax` |
| `written_block_size_avg`  | `writeBlockSizeAvg`   | RENAMED; pointer in canonical |
| `fsync_ops`               | `fsyncOps`            | RENAMED |
| `fsync_usec`              | `fsyncUsec`           | RENAMED |
| `fsync_usec_avg`          | `fsyncUsecAvg`        | RENAMED; pointer in canonical |
| `fsync_usec_max`          | `fsyncUsecMax`        | RENAMED |

**Gaps / structural changes flagged:**

1. **[GAP/STRUCTURAL] `path`**: Legacy concatenated "chunkserver:path". Canonical has two fields. SPA must either concatenate client-side or use `chunkserver` + `path` separately.
2. **[STRUCTURAL] `last_error`**: Legacy = flat string ("No errors" / error string). Canonical = null or `{chunkId: number, timestamp: number}`. SPA `DisksSection.tsx:80` checks `.toLowerCase().includes("no errors")` — must change to `lastError === null`.
3. **[VALUE CHANGE] `status`**: Legacy humanized strings vs canonical lowercase enum values. `statusClass()` in `DisksSection.tsx:8-12` uses `includes("damaged")` and `includes("scanning")` — these still work against canonical enum values. But the displayed text changes from "OK" to "ok", from "Damaged" to "damaged", etc.
4. **[VERBOSE] derived stats fields**: `readBytesPerSecond`, `writeBytesPerSecond`, `readUsecAvg`, `writeUsecAvg`, `fsyncUsecAvg`, `readBlockSizeAvg`, `writeBlockSizeAvg` — only present with `?verbose=true`. Must always call `/api/v1/disks?verbose=true`. In canonical they are `*float64` (nullable) even when verbose=true if the ops count is 0 — SPA should handle `null` (TS: `number | null`).
5. **[RESTRUCTURE] stats nesting**: `disk.minute_stats` → `disk.stats.minute`, `disk.hour_stats` → `disk.stats.hour`, `disk.day_stats` → `disk.stats.day`. `DisksSection.tsx:31` uses `` const key = `${range}_stats` as const `` — must change accessor pattern.

### SPA consumption

- TS types: `types.ts:39-70` — `interface DiskStats`, `interface Disk`
- Component: `DisksSection.tsx`
  - `disk.path` (line 78, 34)
  - `disk.status` (line 79) — `statusClass(disk.status)`
  - `disk.last_error` (line 80) — checks `"no errors"` string
  - `disk.chunks`, `disk.used_space`, `disk.total_space` (lines 81-84)
  - `disk[key]` where key = `minute_stats`/`hour_stats`/`day_stats` (line 31)
  - `st.read_bytes_persecond`, `st.written_bytes_persecond` (lines 35-36)
  - `st.read_usec`, `st.read_usec_avg`, `st.read_usec_max` (lines 37-38)
  - `st.written_usec`, `st.written_usec_avg`, `st.written_usec_max` (lines 39-40)
  - `st.fsync_usec`, `st.fsync_usec_avg`, `st.fsync_usec_max` (lines 41-42)
  - `st.read_block_size_avg`, `st.written_block_size_avg` (lines 43-44)
  - `st.read_ops`, `st.write_ops`, `st.fsync_ops` (lines 43-45)

---

## 4. /api/v1/mounts → Mount / Mount

### Legacy shape (`go/leilfs/models/mount.go:52-72`)

```
Mount {
  id               int             json:"id"
  session_id       uint32          json:"session_id"
  hostname         string          json:"hostname"
  ip_address       string          json:"ip_address"
  mounted_path     string          json:"mounted_path"
  version          string          json:"version"
  root_path        string          json:"root_path"
  mount_info       string          json:"mount_info"
  flags            string          json:"flags"       -- joined array: "ro, dynamic_ip"
  root_uid         uint32          json:"root_uid"
  root_gid         uint32          json:"root_gid"
  map_all_uid      uint32          json:"map_all_uid"
  map_all_gid      uint32          json:"map_all_gid"
  min_goal         *uint8          json:"min_goal"
  max_goal         *uint8          json:"max_goal"
  min_trash_time   *uint32         json:"min_trash_time"
  max_trash_time   *uint32         json:"max_trash_time"
  current_op_stats  *OperationStats json:"current_op_stats"
  last_hour_op_stats *OperationStats json:"last_hour_op_stats"
}
```

**OperationStats** (`go/leilfs/models/mount.go:11-29`)
```
OperationStats {
  statfs   uint32  json:"statfs"
  getattr  uint32  json:"getattr"
  setattr  uint32  json:"setattr"
  lookup   uint32  json:"lookup"
  mkdir    uint32  json:"mkdir"
  rmdir    uint32  json:"rmdir"
  symlink  uint32  json:"symlink"
  readlink uint32  json:"readlink"
  mknod    uint32  json:"mknod"
  unlink   uint32  json:"unlink"
  rename   uint32  json:"rename"
  link     uint32  json:"link"
  readdir  uint32  json:"readdir"
  open     uint32  json:"open"
  read     uint32  json:"read"
  write    uint32  json:"write"
  total    uint64  json:"total"
}
```

### Canonical shape (`leilfs-api/internal/service/models.go:644-665`)

```
Mount {
  id               uint32         json:"id"
  sessionId        uint32         json:"sessionId"
  ip               string         json:"ip"
  hostname         string         json:"hostname,omitempty"
  version          string         json:"version"
  rootPath         string         json:"rootPath"
  mountedPath      string         json:"mountedPath"
  mountInfo        string         json:"mountInfo"
  flags            []string       json:"flags"          -- array, NOT joined string
  rootUid          uint32         json:"rootUid"
  rootGid          uint32         json:"rootGid"
  mapAllUid        uint32         json:"mapAllUid"
  mapAllGid        uint32         json:"mapAllGid"
  minGoal          uint8          json:"minGoal"         -- value, NOT pointer
  maxGoal          uint8          json:"maxGoal"         -- value, NOT pointer
  minTrashTime     uint32         json:"minTrashTime"    -- value, NOT pointer
  maxTrashTime     uint32         json:"maxTrashTime"    -- value, NOT pointer
  currentOpStats   OperationStats json:"currentOpStats"  -- value, NOT pointer
  lastHourOpStats  OperationStats json:"lastHourOpStats" -- value, NOT pointer
}
```

**OperationStats** (`leilfs-api/internal/service/models.go:577-595`)
```
OperationStats {
  statfs   uint64  json:"statfs"
  getattr  uint64  json:"getattr"
  setattr  uint64  json:"setattr"
  lookup   uint64  json:"lookup"
  mkdir    uint64  json:"mkdir"
  rmdir    uint64  json:"rmdir"
  symlink  uint64  json:"symlink"
  readlink uint64  json:"readlink"
  mknod    uint64  json:"mknod"
  unlink   uint64  json:"unlink"
  rename   uint64  json:"rename"
  link     uint64  json:"link"
  readdir  uint64  json:"readdir"
  open     uint64  json:"open"
  read     uint64  json:"read"
  write    uint64  json:"write"
  total    uint64  json:"total"
}
```

### Field mapping (legacy ← canonical)

| Legacy field        | Canonical field     | Notes |
|---------------------|---------------------|-------|
| `id`                | `id`                | RENAMED (casing) |
| `session_id`        | `sessionId`         | RENAMED |
| `hostname`          | `hostname`          | omitempty in canonical |
| `ip_address`        | `ip`                | RENAMED: `ip_address` → `ip` |
| `mounted_path`      | `mountedPath`       | RENAMED |
| `version`           | `version`           | Same |
| `root_path`         | `rootPath`          | RENAMED |
| `mount_info`        | `mountInfo`         | RENAMED |
| `flags`             | `flags`             | STRUCTURAL CHANGE: legacy = joined string, canonical = `[]string`. SPA must join or handle array |
| `root_uid`          | `rootUid`           | RENAMED |
| `root_gid`          | `rootGid`           | RENAMED |
| `map_all_uid`       | `mapAllUid`         | RENAMED |
| `map_all_gid`       | `mapAllGid`         | RENAMED |
| `min_goal`          | `minGoal`           | RENAMED; legacy *uint8 (pointer), canonical uint8 (value) |
| `max_goal`          | `maxGoal`           | RENAMED; pointer→value |
| `min_trash_time`    | `minTrashTime`      | RENAMED; pointer→value |
| `max_trash_time`    | `maxTrashTime`      | RENAMED; pointer→value |
| `current_op_stats`  | `currentOpStats`    | RENAMED; pointer→value |
| `last_hour_op_stats`| `lastHourOpStats`   | RENAMED; pointer→value |

**OperationStats fields** — all have identical names but uint32→uint64 widening (not breaking for JS numbers).

**Gaps / structural changes flagged:**

1. **[STRUCTURAL] `flags`**: Legacy = string (`"ro, dynamic_ip"`). Canonical = `[]string` (`["ro","dynamic_ip"]`). SPA `MountsSection.tsx` does NOT display `flags` in the current implementation (it's listed in the type but not rendered), but type must change from `string` to `string[]`.
2. **[POINTER→VALUE] `min_goal`, `max_goal`, `min_trash_time`, `max_trash_time`**: Legacy uses pointers (nullable), canonical uses values (always present). TS type goes from `number | null` to `number`.
3. **[POINTER→VALUE] `current_op_stats`, `last_hour_op_stats`**: Legacy is `*OperationStats` (nullable), canonical is `OperationStats` (always present, non-null). TS type goes from `OperationStats | null` to `OperationStats`. `MountsSection.tsx:23` does `const stats = m[which] as OperationStats | null` — this null check becomes unnecessary.

### SPA consumption

- TS types: `types.ts:81-127` — `interface OperationStats`, `OP_NAMES`, `interface Mount`
- Component: `MountsSection.tsx`
  - `m.id` (lines 71, 73, 76), `m.session_id` (74), `m.hostname` (75), `m.ip_address` (76)
  - `m.version` (77), `m.mounted_path` (78), `m.root_uid` (79), `m.root_gid` (80)
  - `m.map_all_uid` (81), `m.map_all_gid` (82), `m.min_goal` (83), `m.max_goal` (84)
  - `m.min_trash_time` (85), `m.max_trash_time` (86), `m.mount_info` (93)
  - `m[which]` where which = `"current_op_stats"` | `"last_hour_op_stats"` (line 23)
  - `stats[op]` for each op in OP_NAMES (line 30)

---

## 5. /api/v1/metadata-servers → MetadataServer / MetadataServer

### Legacy shape (`go/leilfs/models/metadataserver.go:12-21`)

```
MetadataServer {
  id               int    json:"id"
  hostname         string json:"hostname"
  ip_address       string json:"ip_address"
  port             uint16 json:"port"
  version          string json:"version"
  personality      string json:"personality"
  state            string json:"state"
  metadata_version int64  json:"metadata_version"
}
```

### Canonical shape (`leilfs-api/internal/service/models.go:539-548`)

```
MetadataServer {
  id               uint32  json:"id"
  ip               string  json:"ip"
  port             uint16  json:"port"
  hostname         string  json:"hostname,omitempty"
  version          string  json:"version"
  personality      string  json:"personality"
  state            string  json:"state"
  metadataVersion  int64   json:"metadataVersion"
}
```

### Field mapping

| Legacy field        | Canonical field    | Notes |
|---------------------|--------------------|-------|
| `id`                | `id`               | uint32→int (safe) |
| `hostname`          | `hostname`         | omitempty in canonical |
| `ip_address`        | `ip`               | RENAMED |
| `port`              | `port`             | Same |
| `version`           | `version`          | Same |
| `personality`       | `personality`      | Same values: "master"/"shadow"/"unknown" |
| `state`             | `state`            | Same values: "running"/"connected"/"disconnected"/"unknown" |
| `metadata_version`  | `metadataVersion`  | RENAMED |

**Gaps**: None. Personality/state values are identical between legacy and canonical.

**Note**: Legacy `personality` for unknown codes produced `"(unknown: code N)"` strings (`metadataserver.go:72-73`). Canonical produces `"unknown"` (models.go:528). Slight behavioral difference, but canonical is cleaner.

### SPA consumption

- TS type: `types.ts:137-146` — `interface MetadataServer`
- Component: `ServersSection.tsx:16-24` — column definitions access:
  - `s.id`, `s.hostname`, `s.ip_address`, `s.port`, `s.version`, `s.personality`, `s.state`, `s.metadata_version`

---

## 6. /api/v1/metaloggers → Metalogger / Metalogger

### Legacy shape (`go/leilfs/models/servers.go:143-148`)

```
Metalogger {
  id         int    json:"id"
  hostname   string json:"hostname"
  ip_address string json:"ip_address"
  version    string json:"version"
}
```

### Canonical shape (`leilfs-api/internal/service/models.go:163-169`)

```
Metalogger {
  id       uint32  json:"id"
  ip       string  json:"ip"
  hostname string  json:"hostname,omitempty"
  version  string  json:"version"
}
```

### Field mapping

| Legacy field  | Canonical field | Notes |
|---------------|-----------------|-------|
| `id`          | `id`            | RENAMED (casing) |
| `hostname`    | `hostname`      | omitempty |
| `ip_address`  | `ip`            | RENAMED |
| `version`     | `version`       | Same |

**Gaps**: None.

### SPA consumption

- TS type: `types.ts:72-77` — `interface Metalogger`
- Component: `ServersSection.tsx:27-33` — `loggerCols()` accesses `l.id`, `l.hostname`, `l.ip_address`, `l.version`

---

## 7. /api/v1/inotifiers → INotifier / INotifier

### Legacy shape (`go/leilfs/models/servers.go:202-207`)

```
INotifier {
  id         int    json:"id"
  hostname   string json:"hostname"
  ip_address string json:"ip_address"
  version    string json:"version"
}
```

### Canonical shape (`leilfs-api/internal/service/models.go:495-499`)

```
INotifier {
  id       uint32  json:"id"
  ip       string  json:"ip"
  hostname string  json:"hostname,omitempty"
  version  string  json:"version"
}
```

### Field mapping

Identical to Metalogger: `ip_address`→`ip`, `id` casing, `hostname` omitempty.

**Gaps**: None.

### SPA consumption

- TS type: `types.ts:79` — `export type INotifier = Metalogger`
- Component: `ServersSection.tsx:102-104` — uses the same `loggerCols()` as Metalogger, accesses `l.id`, `l.hostname`, `l.ip_address`, `l.version`

---

## 8. /api/v1/cluster/fs-check → FsCheckInfo / FsCheckInfo

### Legacy shape (`go/leilfs/models/models.go:80-90`)

```
FsCheckInfo {
  loop_start        uint32 json:"loop_start"
  loop_end          uint32 json:"loop_end"
  files             uint32 json:"files"
  under_goal_files  uint32 json:"under_goal_files"
  missing_files     uint32 json:"missing_files"
  chunks            uint32 json:"chunks"
  under_goal_chunks uint32 json:"under_goal_chunks"
  missing_chunks    uint32 json:"missing_chunks"
  message           string json:"message"
}
```

### Canonical shape (`leilfs-api/internal/service/models.go:66-76`)

```
FsCheckInfo {
  loopStart       int64   json:"loopStart"
  loopEnd         int64   json:"loopEnd"
  files           uint64  json:"files"
  underGoalFiles  uint64  json:"underGoalFiles"
  missingFiles    uint64  json:"missingFiles"
  chunks          uint64  json:"chunks"
  underGoalChunks uint64  json:"underGoalChunks"
  missingChunks   uint64  json:"missingChunks"
  message         string  json:"message"
}
```

### Field mapping

| Legacy field       | Canonical field   | Notes |
|--------------------|-------------------|-------|
| `loop_start`       | `loopStart`       | RENAMED; uint32→int64 (wider type) |
| `loop_end`         | `loopEnd`         | RENAMED; uint32→int64 |
| `files`            | `files`           | RENAMED (casing) |
| `under_goal_files` | `underGoalFiles`  | RENAMED |
| `missing_files`    | `missingFiles`    | RENAMED |
| `chunks`           | `chunks`          | RENAMED (casing) |
| `under_goal_chunks`| `underGoalChunks` | RENAMED |
| `missing_chunks`   | `missingChunks`   | RENAMED |
| `message`          | `message`         | Same |

**Gaps**: None.

### SPA consumption

- TS type: `types.ts:148-158` — `interface FsCheckInfo`
- Component: `InfoSection.tsx:126-152` — accesses:
  - `d.fsCheck.loop_start`, `d.fsCheck.loop_end`, `d.fsCheck.files`
  - `d.fsCheck.under_goal_files`, `d.fsCheck.missing_files`, `d.fsCheck.chunks`
  - `d.fsCheck.under_goal_chunks`, `d.fsCheck.missing_chunks`, `d.fsCheck.message`
  - Also `d.fsCheck.loop_start > 0` guard (line 126)

---

## 9. /api/v1/cluster/chunk-operations → ChunkOperationsInfo / ChunkOperationsInfo

### Legacy shape (`go/leilfs/models/models.go:113-128`)

```
ChunkOperationsInfo {
  loop_start              uint32 json:"loop_start"
  loop_end                uint32 json:"loop_end"
  delete_invalid          uint32 json:"delete_invalid"
  not_delete_invalid      uint32 json:"not_delete_invalid"
  delete_unused           uint32 json:"delete_unused"
  not_delete_unused       uint32 json:"not_delete_unused"
  delete_disk_clean       uint32 json:"delete_disk_clean"
  not_delete_disk_clean   uint32 json:"not_delete_disk_clean"
  delete_over_goal        uint32 json:"delete_over_goal"
  not_delete_over_goal    uint32 json:"not_delete_over_goal"
  replicate_under_goal    uint32 json:"replicate_under_goal"
  not_replicate_under_goal uint32 json:"not_replicate_under_goal"
  rebalance               uint32 json:"rebalance"
}
```

### Canonical shape (`leilfs-api/internal/service/models.go:95-109`)

```
ChunkOperationsInfo {
  loopStart              int64   json:"loopStart"
  loopEnd                int64   json:"loopEnd"
  deleteInvalid          uint64  json:"deleteInvalid"
  notDeleteInvalid       uint64  json:"notDeleteInvalid"
  deleteUnused           uint64  json:"deleteUnused"
  notDeleteUnused        uint64  json:"notDeleteUnused"
  deleteDiskClean        uint64  json:"deleteDiskClean"
  notDeleteDiskClean     uint64  json:"notDeleteDiskClean"
  deleteOverGoal         uint64  json:"deleteOverGoal"
  notDeleteOverGoal      uint64  json:"notDeleteOverGoal"
  replicateUnderGoal     uint64  json:"replicateUnderGoal"
  notReplicateUnderGoal  uint64  json:"notReplicateUnderGoal"
  rebalance              uint64  json:"rebalance"
}
```

### Field mapping

All 13 fields map 1:1, snake_case→camelCase rename only. `loopStart`/`loopEnd` widen from uint32 to int64 (compatible range for timestamps).

**Gaps**: None.

### SPA consumption

- TS type: `types.ts:160-174` — `interface ChunkOperationsInfo`
- Component: `InfoSection.tsx:74-97` — accesses all 13 fields:
  - `d.ops.loop_start`, `d.ops.loop_end`
  - `d.ops.delete_invalid`, `d.ops.not_delete_invalid`
  - `d.ops.delete_unused`, `d.ops.not_delete_unused`
  - `d.ops.delete_disk_clean`, `d.ops.not_delete_disk_clean`
  - `d.ops.delete_over_goal`, `d.ops.not_delete_over_goal`
  - `d.ops.replicate_under_goal`, `d.ops.not_replicate_under_goal`
  - `d.ops.rebalance`
  - Guard: `d.ops.loop_start > 0` (line 74)

---

## 10. /api/v1/cluster/chunk-matrix → ChunkMatrix / ChunkMatrix

### Legacy shape (`go/leilfs/models/models.go:148-152`)

```
ChunkMatrix {
  matrix [][]uint32 json:"matrix"    -- variable-length rows (slices)
}
```

### Canonical shape (`leilfs-api/internal/service/models.go:134-136`)

```
ChunkMatrix {
  matrix [11][11]uint64 json:"matrix"  -- fixed 11×11 array, uint64
}
```

### Field mapping

| Legacy field | Canonical field | Notes |
|--------------|-----------------|-------|
| `matrix`     | `matrix`        | RENAMED (casing — JSON tag is `matrix` in both). Values widen uint32→uint64 (JS number compatible). Wire format: legacy `[][]uint32` vs canonical `[11][11]uint64` — both serialize as 2D JSON array, compatible |

**Gaps**: None. The JSON shape is a 2D array in both — the wire type difference (slice vs fixed array) is invisible to JSON.

### SPA consumption

- TS type: `types.ts:176-178` — `interface ChunkMatrix { matrix: number[][] }`
- Component: `InfoSection.tsx:111-123` — `d.matrix.matrix.map((row, i) => row.map(...))`
  - Access: `d.matrix.matrix` (the outer array), row values, `row.reduce()`

---

## 11. /api/v1/goals → Goal / Goal

### Legacy shape (`go/leilfs/models/models.go:154-159`)

```
Goal {
  id         uint16 json:"id"
  name       string json:"name"
  definition string json:"definition"
}
```

### Canonical shape (`leilfs-api/internal/service/models.go:144-148`)

```
Goal {
  id         uint16 json:"id"
  name       string json:"name"
  definition string json:"definition"
}
```

### Field mapping

All 3 fields identical. **No changes needed.**

### SPA consumption

- TS type: `types.ts:180-184` — `interface Goal`
- Used in: `ChunksSection.tsx:12` — passed to `mapGoalHealth(health, goals)`
- `chunkhealth.ts:18-33` — accesses `goal.id`, `goal.name`

---

## 12. /api/v1/exports → Export / Export

### Legacy shape (`go/leilfs/models/export.go:11-17`)

```
Export {
  id      int    json:"id"
  ip_from string json:"ip_from"
  ip_to   string json:"ip_to"
  path    string json:"path"
  flags   string json:"flags"   -- joined string: "rw, dynamic_ip"
}
```

### Canonical shape (`leilfs-api/internal/service/models.go:173-179`)

```
Export {
  id     uint32   json:"id"
  ipFrom string   json:"ipFrom"
  ipTo   string   json:"ipTo"
  path   string   json:"path"
  flags  []string json:"flags"  -- array: ["rw","dynamic_ip"]
}
```

### Field mapping

| Legacy field | Canonical field | Notes |
|--------------|-----------------|-------|
| `id`         | `id`            | uint32→int |
| `ip_from`    | `ipFrom`        | RENAMED |
| `ip_to`      | `ipTo`          | RENAMED |
| `path`       | `path`          | Same |
| `flags`      | `flags`         | STRUCTURAL: string→`[]string`. Must join client-side |

**Gaps**: None.
**Note**: No component currently renders exports directly — `ServersSection.tsx` and `MountsSection.tsx` don't include exports. The API call exists in `api.ts` but there's no matching component visible.

### SPA consumption

- TS type: `types.ts:129-135` — `interface Export`
- No component currently renders this (no `ExportsSection.tsx` found). The `api.exports` call exists in `api.ts:43` but is not consumed by any visible component.

---

## 13. /api/v1/cluster/chunk-health → ChunkHealth / ChunkHealth

### Legacy shape (`go/leilfs/models/chunkhealth.go:7-13`)

```
ChunkHealth {
  regular_only bool               json:"regular_only"
  safe         map[uint8]uint64   json:"safe"         -- int-keyed JSON object {"1": N, "2": N}
  endangered   map[uint8]uint64   json:"endangered"
  lost         map[uint8]uint64   json:"lost"
  replication  map[uint8][]uint64 json:"replication"
  deletion     map[uint8][]uint64 json:"deletion"
}
```

### Canonical shape (`leilfs-api/internal/service/models.go:226-251`)

```
ChunkHealth {
  regularOnly bool              json:"regularOnly"
  goals       []ChunkHealthGoal json:"goals"    -- ARRAY, not map
  totals      ChunkHealthTotals json:"totals"
}

ChunkHealthGoal {
  goalId      uint16   json:"goalId"
  name        string   json:"name"
  total       uint64   json:"total"
  safe        uint64   json:"safe"
  endangered  uint64   json:"endangered"
  lost        uint64   json:"lost"
  replication [11]uint64 json:"replication"
  deletion    [11]uint64 json:"deletion"
}

ChunkHealthTotals {
  replication [11]uint64 json:"replication"
  deletion    [11]uint64 json:"deletion"
}
```

### Field mapping

**[MAJOR STRUCTURAL CHANGE]**: Legacy = 5 maps keyed by goal ID (uint8 keys serialize as string). Canonical = array of goal objects with embedded safe/endangered/lost/replication/deletion + a separate totals object.

| Legacy field   | Canonical location               | Notes |
|----------------|----------------------------------|-------|
| `regular_only` | `regularOnly`                    | RENAMED |
| `safe`         | `goals[i].safe`                  | RESTRUCTURED: map→array |
| `endangered`   | `goals[i].endangered`            | RESTRUCTURED |
| `lost`         | `goals[i].lost`                  | RESTRUCTURED |
| `replication`  | `goals[i].replication`           | RESTRUCTURED; fixed [11]uint64 vs []uint64 |
| `deletion`     | `goals[i].deletion`              | RESTRUCTURED |
| (none)         | `goals[i].goalId`                | NEW: goal ID per entry (was the map key) |
| (none)         | `goals[i].name`                  | NEW: goal name embedded (was fetched separately) |
| (none)         | `goals[i].total`                 | NEW: pre-computed total |
| (none)         | `totals.replication`             | NEW: column-wise totals |
| (none)         | `totals.deletion`                | NEW: column-wise totals |

**Key impact on SPA**:

The `chunkhealth.ts` module currently:
1. Fetches `ChunkHealth` (maps) and `Goal[]` separately (`ChunksSection.tsx:12`)
2. `mapGoalHealth()` iterates goals, looks up `health.safe[String(goal.id)]`, etc.

With canonical:
1. `ChunkHealth.goals` already contains per-goal data with name and all counts
2. `mapGoalHealth()` can be simplified to just transform `health.goals` directly
3. The separate goals fetch for chunk health display is no longer needed (name is embedded)
4. `goalChunkSums()` can use `totals.replication` and `totals.deletion` instead of computing manually

The `goals` fetch is still needed for the Goals listing itself but not for mapping chunk health.

### SPA consumption

- TS type: `types.ts:186-193` — `interface ChunkHealth` (map-based)
- `chunkhealth.ts:18-33` — `mapGoalHealth()` accesses `health.safe[key]`, `health.endangered[key]`, `health.lost[key]`, `health.replication[key]`, `health.deletion[key]`
- `chunkhealth.ts:36-51` — `goalChunkSums()` iterates `goal.replication`/`goal.deletion`
- `ChunksSection.tsx:11-13` — fetches both `api.chunkHealth(master)` and `api.goals(master)`, passes to `mapGoalHealth()`

---

## Summary of Structural/Non-Trivial Changes (Flagged Gaps)

There are **no outright gaps** (legacy fields with zero canonical source). All legacy
fields have a canonical equivalent. However, there are **5 structural changes** that
require non-trivial SPA logic changes beyond simple field renames:

| # | Endpoint | Legacy | Canonical | Required SPA change |
|---|----------|--------|-----------|---------------------|
| 1 | disks | `path` = `"<cs>:<path>"` | `chunkserver` + `path` (separate) | Concatenate client-side in TS: `disk.chunkserver + ":" + disk.path` |
| 2 | disks | `last_error` = human string | `lastError` = `null \| {chunkId, timestamp}` | Replace null-check + format timestamp+chunkId. Change `DiskStats` `last_error: string` to `lastError: {chunkId: number; timestamp: number} \| null` |
| 3 | disks | `minute_stats`, `hour_stats`, `day_stats` flat on Disk | `stats.minute`, `stats.hour`, `stats.day` nested | Change `disk[range + "_stats"]` accessor to `disk.stats[range]` |
| 4 | mounts | `flags` = joined string | `flags` = `string[]` | TS: `flags: string[]`. Render as `m.flags.join(", ")` if displayed |
| 5 | chunk-health | `{safe,endangered,lost,replication,deletion}` as goal-keyed maps | `goals: ChunkHealthGoal[]` array with embedded name+total+totals | Rewrite `mapGoalHealth()` to use `health.goals` directly; `goalChunkSums()` can use `health.totals` |

### Disk `status` value change (non-structural but visible)

Legacy status strings: `"OK"`, `"Marked for removal"`, `"Damaged"`, `"Damaged, marked for removal"`, `"Scanning"`, `"Scanning, marked for removal"`, `"Errors reported"`

Canonical enum values: `"ok"`, `"marked_for_removal"`, `"damaged"`, `"damaged_marked_for_removal"`, `"scanning"`, `"scanning_marked_for_removal"`, `"errors_reported"`

`statusClass()` in `DisksSection.tsx:8-12` uses `s.includes("damaged")` and `s.includes("scanning")` — these still match canonical values. But the text rendered to users changes. Either accept the new enum strings or add a display-name map in the SPA.

---

## New TypeScript Types (Canonical)

These are the canonical TS interfaces needed to replace `types.ts`:

```typescript
// types.ts replacement (canonical camelCase shapes)

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

export interface Chunkserver {
  id: number;
  ip: string;
  port: number;
  hostname?: string;
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
  ip: string;
  hostname?: string;
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
  ip: string;
  port: number;
  hostname?: string;
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

export interface ChunkHealthGoal {
  goalId: number;
  name: string;
  total: number;
  safe: number;
  endangered: number;
  lost: number;
  replication: number[];
  deletion: number[];
}

export interface ChunkHealthTotals {
  replication: number[];
  deletion: number[];
}

export interface ChunkHealth {
  regularOnly: boolean;
  goals: ChunkHealthGoal[];
  totals: ChunkHealthTotals;
}
```

---

## api.ts Changes Required

```typescript
// New endpoint paths and typed returns (canonical):
export const api = {
  info:               (m: Master) => get<SystemInfo>("/api/v1/cluster", m),
  chunkHealth:        (m: Master) => get<ChunkHealth>("/api/v1/cluster/chunk-health", m),
  chunkservers:       (m: Master) => get<Chunkserver[]>("/api/v1/chunkservers", m),
  disks:              (m: Master) => get<Disk[]>("/api/v1/disks?verbose=true", m),
  mounts:             (m: Master) => get<Mount[]>("/api/v1/mounts", m),
  metadataServers:    (m: Master) => get<MetadataServer[]>("/api/v1/metadata-servers", m),
  inotifiers:         (m: Master) => get<INotifier[]>("/api/v1/inotifiers", m),
  fsCheckInfo:        (m: Master) => get<FsCheckInfo>("/api/v1/cluster/fs-check", m),
  chunkOperationsInfo:(m: Master) => get<ChunkOperationsInfo>("/api/v1/cluster/chunk-operations", m),
  goals:              (m: Master) => get<Goal[]>("/api/v1/goals", m),
  chunkMatrix:        (m: Master) => get<ChunkMatrix>("/api/v1/cluster/chunk-matrix", m),
  metaloggers:        (m: Master) => get<Metalogger[]>("/api/v1/metaloggers", m),
  exports:            (m: Master) => get<Export[]>("/api/v1/exports", m),
};
```

Note: The `get<T>()` helper currently passes `masterhost`/`masterport` as query params; these
are forwarded to the Go backend which uses them to select the cluster. When calling
`/api/v1/disks?verbose=true` the query string already has `?`, so the helper's
`searchParams.set()` calls will append correctly (URLSearchParams handles this).

---

## Component-by-Component Change Summary

### InfoSection.tsx

Fields to rename in component (d.info.*):
- `ram_used` → `memoryUsedBytes`
- `total_space` → `totalSpaceBytes`
- `avail_space` → `availableSpaceBytes`
- `trash_space` → `trashSpaceBytes`
- `trash_files` → `trashFiles`
- `reserved_space` → `reservedSpaceBytes`
- `reserved_files` → `reservedFiles`
- `total_objects` → `totalObjects`
- `directories` → `directories` (same string, just TS type changes from uint32 to uint64 — no JS change)
- `files` → `files` (same)
- `symlinks` → `symlinks` (same)
- `chunks` → `chunks` (same)
- `all_copies` → `allCopies`
- `regular_copies` → `regularCopies`

ChunkOperationsInfo fields (d.ops.*):
- `loop_start` → `loopStart`, `loop_end` → `loopEnd`
- `delete_invalid` → `deleteInvalid`, `not_delete_invalid` → `notDeleteInvalid`
- `delete_unused` → `deleteUnused`, `not_delete_unused` → `notDeleteUnused`
- `delete_disk_clean` → `deleteDiskClean`, `not_delete_disk_clean` → `notDeleteDiskClean`
- `delete_over_goal` → `deleteOverGoal`, `not_delete_over_goal` → `notDeleteOverGoal`
- `replicate_under_goal` → `replicateUnderGoal`, `not_replicate_under_goal` → `notReplicateUnderGoal`
- `rebalance` → `rebalance` (same)

FsCheckInfo fields (d.fsCheck.*):
- `loop_start` → `loopStart`, `loop_end` → `loopEnd`
- `under_goal_files` → `underGoalFiles`, `missing_files` → `missingFiles`
- `under_goal_chunks` → `underGoalChunks`, `missing_chunks` → `missingChunks`

### ServersSection.tsx

MetadataServer columns:
- `s.ip_address` → `s.ip`
- `s.metadata_version` → `s.metadataVersion`

Chunkserver rows:
- `s.is_disconnected` → `!s.connected`
- `s.ip_address` → `s.ip`
- `s.used_space` → `s.usedSpaceBytes`
- `s.total_space` → `s.totalSpaceBytes`
- `s.used_space_tobedeleted` → `s.usedSpaceToDeleteBytes`
- `s.total_space_tobedeleted` → `s.totalSpaceToDeleteBytes`
- `s.chunks_tobedeleted` → `s.chunksToDelete`

Metalogger/INotifier columns:
- `l.ip_address` → `l.ip`

### DisksSection.tsx

Disk row:
- `disk.path` → `disk.chunkserver + ":" + disk.path`
- `disk.status` displayed text changes (enum vs human)
- `disk.last_error` → reconstruct: `disk.lastError === null ? "No errors" : formatError(disk.lastError)`
- `disk.last_error.toLowerCase().includes("no errors")` → `disk.lastError === null`
- `disk.used_space` → `disk.usedSpaceBytes`
- `disk.total_space` → `disk.totalSpaceBytes`

DiskStats accessor:
- `const key = \`${range}_stats\` as const` → `disk.stats[range]` directly

DiskStats fields:
- `st.read_bytes_persecond` → `st.readBytesPerSecond ?? 0`
- `st.written_bytes_persecond` → `st.writeBytesPerSecond ?? 0`
- `st.read_usec` → `st.readUsec`, `st.read_usec_avg` → `st.readUsecAvg ?? 0`, `st.read_usec_max` → `st.readUsecMax`
- `st.written_usec` → `st.writeUsec`, `st.written_usec_avg` → `st.writeUsecAvg ?? 0`, `st.written_usec_max` → `st.writeUsecMax`
- `st.fsync_usec` → `st.fsyncUsec`, `st.fsync_usec_avg` → `st.fsyncUsecAvg ?? 0`, `st.fsync_usec_max` → `st.fsyncUsecMax`
- `st.read_block_size_avg` → `st.readBlockSizeAvg ?? 0`
- `st.written_block_size_avg` → `st.writeBlockSizeAvg ?? 0`
- `st.read_ops` → `st.readOps`, `st.write_ops` → `st.writeOps`, `st.fsync_ops` → `st.fsyncOps`

### MountsSection.tsx

Mount table row:
- `m.session_id` → `m.sessionId`
- `m.ip_address` → `m.ip`
- `m.mounted_path` → `m.mountedPath`
- `m.root_uid` → `m.rootUid`, `m.root_gid` → `m.rootGid`
- `m.map_all_uid` → `m.mapAllUid`, `m.map_all_gid` → `m.mapAllGid`
- `m.min_goal` → `m.minGoal`, `m.max_goal` → `m.maxGoal`
- `m.min_trash_time` → `m.minTrashTime`, `m.max_trash_time` → `m.maxTrashTime`
- `m.mount_info` → `m.mountInfo`

OpsTable:
- `which: "current_op_stats" | "last_hour_op_stats"` → `which: "currentOpStats" | "lastHourOpStats"`
- `m[which]` now always non-null (no null guard needed, but removing it is safe)

OP_NAMES in types.ts: all 17 op stat keys are identical between legacy and canonical (snake_case only for the op names themselves, which are: statfs, getattr, setattr, etc. — these are already lowercase single-word, no underscore). No change needed to `OP_NAMES`.

### chunkhealth.ts

`mapGoalHealth()` rewrite:

```typescript
// Old: takes ChunkHealth (maps) + Goal[] and cross-joins
// New: ChunkHealth.goals already has name+safe+endangered+lost+replication+deletion
export function mapGoalHealth(health: ChunkHealth, _goals?: Goal[]): MappedGoalHealth[] {
  return health.goals.map((g) => ({
    name: g.name,
    total: g.total,
    safe: g.safe,
    endangered: g.endangered,
    lost: g.lost,
    replication: Array.from(g.replication),
    deletion: Array.from(g.deletion),
  }));
}
```

`goalChunkSums()` can be simplified to use `health.totals`:
```typescript
export function goalChunkSums(
  _mapped: MappedGoalHealth[],
  attribute: "replication" | "deletion",
  health?: ChunkHealth,
): number[] {
  if (health) return Array.from(health.totals[attribute]);
  // fallback: compute manually (old behavior)
  ...
}
```

`ChunksSection.tsx`: the separate `api.goals(master)` call for chunk-health display can be dropped (name is embedded in `health.goals[i].name`). The `api.goals(master)` call for the goals *list* itself (if any component renders it) still needs to stay.
