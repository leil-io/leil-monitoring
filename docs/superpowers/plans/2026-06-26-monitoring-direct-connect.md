# Monitoring Direct-Connect Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the intermediate `leil-api` Go service and the `apiclient` adapter so the monitoring SPA consumes leilfs-api's canonical `/api/v1/*` contract directly, served via `leil-monitoring`'s thin reverse proxy; replace the free-text host/port + "Go" control with a cluster-node dropdown that drives charts.

**Architecture:** `leil-monitoring` stays as the static SPA host + same-origin reverse proxy, repointed at leilfs-api. The SPA's data layer (`types.ts`, `api.ts`, components, `charts.ts`) migrates from the legacy snake_case shapes to leilfs-api's camelCase shapes. Charts move to leilfs-api's `GET /api/v1/charts?id=&node=` (Phase 1, already shipped). The `leil-api`/`apiclient`/`leilfs` Go packages are deleted; the surviving Go binary is just `cmd/leil-monitoring` + `internal/webui`.

**Tech Stack:** Go 1.22 (monitoring module `github.com/leil-io/saunafs-monitoring/go`), Preact + Vite + TypeScript SPA, Chart.js, docker-compose.

## Global Constraints

- **Authoritative field map:** `docs/superpowers/specs/2026-06-26-phase2-field-map.md` is the exact, complete legacy→canonical mapping for every endpoint, the full canonical `types.ts`, and per-component rename tables. Tasks below cite its sections; it is the source of truth for every field name. The design spec is `docs/superpowers/specs/2026-06-26-monitoring-direct-connect-design.md`.
- **Commits are PLAIN (unsigned)** in this repo — `git commit -F <file>` (NOT `-m`), end with the trailer `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`. (Do not SSH-sign; this repo's convention differs from leilfs-api.)
- **Go:** module Go directive stays 1.22; build with the repo's existing flags. Each Go task ends green: `cd go && go build ./... && go vet ./...`.
- **SPA:** each SPA task ends green: `cd go/web && npm run build` (Vite + tsc) with no type errors. Run `npm install` once first if `node_modules` is absent.
- **Preserve existing exported TS interface NAMES** (`SystemInfo`, `Server`, `Disk`, `DiskStats`, `Mount`, `OperationStats`, `Export`, `MetadataServer`, `Metalogger`, `INotifier`, `FsCheckInfo`, `ChunkOperationsInfo`, `ChunkMatrix`, `Goal`, `ChunkHealth`). Change only their FIELDS to canonical camelCase. This keeps `api.ts` return-type references stable and lets each section task build independently. (New helper types `DiskError`, `DiskStatsTriple`, `ChunkHealthGoal`, `ChunkHealthTotals` are additive.)
- **Canonical casing:** leilfs-api is camelCase; legacy was snake_case. Every field access in every touched component changes accordingly.
- **No behavior change to the cluster contract:** leilfs-api ignores unknown query params (so a stale `masterhost`/`masterport` is harmless), and `/api/v1/charts` forwards the same uint32 chart id to the same binary CHART command the legacy client used — so the chart catalog ids in `charts.ts` and the CSV parsing are unchanged.

## Design decisions baked into this plan

1. **Two chart pages, enumerated per page (CONFIRMED):** Keep the existing two chart nav entries — a **Masters** page and a **Chunkservers** page. Each page *enumerates* its nodes (one chart block per node), matching today's "Server Charts" behavior and scaling naturally to multiple masters in the future. The free-text host/port inputs + `Go` button are removed entirely; **no dropdown** and no `chartNode` state. Charts target a node via leilfs-api's `node` query param.
   - **Chunkservers page:** fetch `GET /api/v1/chunkservers`, render one chart block per connected chunkserver, `node=<canonical ip>`.
   - **Masters page:** fetch `GET /api/v1/metadata-servers`, render a chart block per master (today: the single configured master), labelled with its hostname/ip. **Targeting limitation (Phase 1):** leilfs-api's `/api/v1/charts` resolves `node` only to `""` (the configured master) or a known chunkserver id/ip — it cannot yet target an arbitrary master/shadow by ip. So today every master block uses `node=""` (the configured master). True multi-master chart targeting needs a future leilfs-api enhancement (resolve master/shadow ips in `chartTarget`); the page is structured to enumerate so it is ready when that lands. This is a noted follow-up, not implemented here.
2. **Data sections are cluster-bound:** leilfs-api is configured for one cluster and ignores per-request master selection, so the data sections (`Info`, `Chunks`, `Servers`, `Disks`, `Config`, `Mounts`) no longer depend on a selectable master. To minimize churn, their `master` prop is kept but fed a constant default `{ host: "sfsmaster", port: 9421 }` that never changes.
3. **`leilfs/` deletion:** investigation confirmed that after deleting `cmd/leil-api`, `internal/httpapi`, and `internal/apiclient`, nothing imports `leilfs/` — so it is deleted too. Task 1 re-verifies zero dangling imports before deleting.

---

## File Structure

| File | Action | Task |
|------|--------|------|
| `go/cmd/leil-api/` | delete | 1 |
| `go/internal/httpapi/` | delete | 1 |
| `go/internal/apiclient/` | delete | 1 |
| `go/leilfs/` | delete (after import check) | 1 |
| `go/cmd/leil-monitoring/main.go` | keep; proxy forwards `/api/v1/*` unchanged | 1 |
| `go/web/src/api.ts` | repoint paths → `/api/v1/*`, drop masterhost/masterport | 2 |
| `go/web/src/types.ts` | canonical fields, per section | 3–8 |
| `go/web/src/components/InfoSection.tsx` | field renames | 3 |
| `go/web/src/components/ServersSection.tsx` | field renames + `connected` inversion | 4 |
| `go/web/src/components/DisksSection.tsx` | structural (path/lastError/stats) | 5 |
| `go/web/src/components/MountsSection.tsx` | flags array, pointer→value | 6 |
| `go/web/src/components/ConfigSection.tsx` | exports flags array | 7 |
| `go/web/src/components/ChunksSection.tsx` + `go/web/src/chunkhealth.ts` | chunk-health map→array | 8 |
| `go/web/src/charts.ts` + `components/ChartsSection.tsx` + `app.tsx` | node-selector charts + dropdown | 9 |
| `go/web/vite.config.ts`, `compose.yaml` | repoint to leilfs-api | 10 |

---

## Task 1: Delete the intermediate leil-api service; repoint the proxy

**Files:**
- Delete: `go/cmd/leil-api/`, `go/internal/httpapi/`, `go/internal/apiclient/`, `go/leilfs/`
- Inspect/keep: `go/cmd/leil-monitoring/main.go`, `go/internal/webui/embed.go`

**Interfaces:**
- Produces: a two-package Go binary (`cmd/leil-monitoring` + `internal/webui`) that serves the SPA and reverse-proxies `/api/`, `/docs`, `/openapi.json` to `LEIL_API_URL` (to be pointed at leilfs-api). No path rewrite needed: the SPA (Task 2) will call `/api/v1/*`, which `httputil.NewSingleHostReverseProxy` forwards verbatim.

- [ ] **Step 1: Re-verify nothing outside the deleted packages imports them**

Run from repo root:
```bash
cd /home/jorge/Work/leilfs-monitoring/go
grep -rn --include=*.go 'saunafs-monitoring/go/internal/httpapi\|saunafs-monitoring/go/internal/apiclient\|saunafs-monitoring/go/leilfs' . | grep -v '^\./internal/httpapi/' | grep -v '^\./internal/apiclient/' | grep -v '^\./leilfs/' | grep -v '^\./cmd/leil-api/'
```
Expected: **no output** (every importer is itself inside a package being deleted). If any line appears from `cmd/leil-monitoring` or `internal/webui`, STOP and report — the deletion is not safe as planned.

- [ ] **Step 2: Delete the packages**

```bash
cd /home/jorge/Work/leilfs-monitoring/go
git rm -r cmd/leil-api internal/httpapi internal/apiclient leilfs
```

- [ ] **Step 3: Confirm the proxy needs no change**

Read `go/cmd/leil-monitoring/main.go`. Confirm it builds the proxy from `LEIL_API_URL` and routes `/api/`, `/docs`, `/openapi.json` → proxy and `/` → `webui.Handler()`. No code change is required (the SPA will call `/api/v1/*`, forwarded unchanged). If `main.go` imports any deleted package, that is a problem — report it.

- [ ] **Step 4: Build + vet**

Run: `cd /home/jorge/Work/leilfs-monitoring/go && go build ./... && go vet ./...`
Expected: clean. (The SPA `dist/` embed is unaffected; if `internal/webui/dist` is absent the build may need a prior `npm run build` — if so, note it; embedding an existing dist is fine.)

- [ ] **Step 5: Commit**

```bash
cd /home/jorge/Work/leilfs-monitoring
cat > /tmp/p2-task1.txt <<'EOF'
refactor(go): remove intermediate leil-api service and binary client

Delete cmd/leil-api, internal/httpapi (its JSON API), internal/apiclient (the
canonical->legacy adapter) and the leilfs binary-protocol client. The SPA now
talks leilfs-api's /api/v1/* directly through leil-monitoring's reverse proxy,
which forwards paths unchanged. Charts are served by leilfs-api as of Phase 1,
so the binary client has no remaining users.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
git commit -F /tmp/p2-task1.txt
```

---

## Task 2: Repoint the SPA data layer to `/api/v1/*`

**Files:**
- Modify: `go/web/src/api.ts`

**Interfaces:**
- Consumes: nothing new.
- Produces: `api.*` functions that fetch canonical `/api/v1/*` paths. Interface return-type NAMES are unchanged (their fields change in Tasks 3–8), so this task builds on its own.

- [ ] **Step 1: Rewrite the endpoint paths and drop the master query params**

In `go/web/src/api.ts`, change the `get()` helper to stop appending `masterhost`/`masterport` (leilfs-api is cluster-bound and ignores them), keeping the `master` parameter in the signature for now so call sites don't change:

```ts
async function get<T>(path: string, _master: Master): Promise<T> {
  const url = new URL(path, location.origin);
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}
```
(Preserve the existing error handling shape if it differs — keep whatever the current `get` does on `!res.ok`, just remove the two `searchParams.set` lines.)

Then repoint every endpoint to its canonical path (see field map "Endpoint Path Map", lines 16–30):

```ts
export const api = {
  info:                (m: Master) => get<SystemInfo>("/api/v1/cluster", m),
  chunkHealth:         (m: Master) => get<ChunkHealth>("/api/v1/cluster/chunk-health", m),
  chunkservers:        (m: Master) => get<Server[]>("/api/v1/chunkservers", m),
  disks:               (m: Master) => get<Disk[]>("/api/v1/disks?verbose=true", m),
  mounts:              (m: Master) => get<Mount[]>("/api/v1/mounts", m),
  metadataServers:     (m: Master) => get<MetadataServer[]>("/api/v1/metadata-servers", m),
  inotifiers:          (m: Master) => get<INotifier[]>("/api/v1/inotifiers", m),
  fsCheckInfo:         (m: Master) => get<FsCheckInfo>("/api/v1/cluster/fs-check", m),
  chunkOperationsInfo: (m: Master) => get<ChunkOperationsInfo>("/api/v1/cluster/chunk-operations", m),
  goals:               (m: Master) => get<Goal[]>("/api/v1/goals", m),
  chunkMatrix:         (m: Master) => get<ChunkMatrix>("/api/v1/cluster/chunk-matrix", m),
  metaloggers:         (m: Master) => get<Metalogger[]>("/api/v1/metaloggers", m),
  exports:             (m: Master) => get<Export[]>("/api/v1/exports", m),
};
```
Keep the existing `Master` type and the existing import list. Do not rename any interface here.

- [ ] **Step 2: Build**

Run: `cd /home/jorge/Work/leilfs-monitoring/go/web && npm run build`
Expected: success (types unchanged; only paths/strings changed).

- [ ] **Step 3: Commit**

```bash
cd /home/jorge/Work/leilfs-monitoring
cat > /tmp/p2-task2.txt <<'EOF'
feat(web): point the SPA data layer at leilfs-api /api/v1/*

Repoint every api.ts endpoint to leilfs-api's canonical paths (disks with
verbose=true) and stop sending masterhost/masterport — leilfs-api is bound to a
single cluster and ignores them. Response shapes are migrated per-section in
following commits.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
git commit -F /tmp/p2-task2.txt
```

---

## Task 3: InfoSection — canonical cluster/ops/fscheck/matrix shapes

**Files:**
- Modify: `go/web/src/types.ts` (`SystemInfo`, `ChunkOperationsInfo`, `FsCheckInfo`, `ChunkMatrix`)
- Modify: `go/web/src/components/InfoSection.tsx`

**Interfaces:**
- Consumes: `api.info`, `api.chunkOperationsInfo`, `api.fsCheckInfo`, `api.chunkMatrix` (Task 2 paths).
- Produces: nothing other tasks depend on.

- [ ] **Step 1: Replace the four interfaces with their canonical fields**

In `types.ts`, replace the bodies of `SystemInfo`, `ChunkOperationsInfo`, `FsCheckInfo`, `ChunkMatrix` with the canonical definitions from the field map (lines 1014–1030 for `SystemInfo`, 1176–1190 for `ChunkOperationsInfo`, 1164–1174 for `FsCheckInfo`, 1192–1194 for `ChunkMatrix`). Keep the interface names.

- [ ] **Step 2: Rename every field access in InfoSection.tsx**

Apply the renames from field map section "InfoSection.tsx" (lines 1257–1287). Specifically:
- `d.info.*`: `ram_used`→`memoryUsedBytes`, `total_space`→`totalSpaceBytes`, `avail_space`→`availableSpaceBytes`, `trash_space`→`trashSpaceBytes`, `trash_files`→`trashFiles`, `reserved_space`→`reservedSpaceBytes`, `reserved_files`→`reservedFiles`, `total_objects`→`totalObjects`, `all_copies`→`allCopies`, `regular_copies`→`regularCopies` (`directories`/`files`/`symlinks`/`chunks`/`version` unchanged).
- `d.ops.*`: `loop_start`→`loopStart`, `loop_end`→`loopEnd`, `delete_invalid`→`deleteInvalid`, `not_delete_invalid`→`notDeleteInvalid`, `delete_unused`→`deleteUnused`, `not_delete_unused`→`notDeleteUnused`, `delete_disk_clean`→`deleteDiskClean`, `not_delete_disk_clean`→`notDeleteDiskClean`, `delete_over_goal`→`deleteOverGoal`, `not_delete_over_goal`→`notDeleteOverGoal`, `replicate_under_goal`→`replicateUnderGoal`, `not_replicate_under_goal`→`notReplicateUnderGoal` (`rebalance` unchanged). Update the `d.ops.loop_start > 0` guard to `d.ops.loopStart > 0`.
- `d.fsCheck.*`: `loop_start`→`loopStart`, `loop_end`→`loopEnd`, `under_goal_files`→`underGoalFiles`, `missing_files`→`missingFiles`, `under_goal_chunks`→`underGoalChunks`, `missing_chunks`→`missingChunks` (`files`/`chunks`/`message` unchanged). Update the `d.fsCheck.loop_start > 0` guard to `loopStart`.
- `d.matrix.matrix` is unchanged (still a 2D array).

- [ ] **Step 3: Build**

Run: `cd /home/jorge/Work/leilfs-monitoring/go/web && npm run build`
Expected: success. (Other interfaces/components untouched and self-consistent.)

- [ ] **Step 4: Commit**

```bash
cd /home/jorge/Work/leilfs-monitoring
cat > /tmp/p2-task3.txt <<'EOF'
feat(web): migrate InfoSection to canonical cluster shapes

Switch SystemInfo, ChunkOperationsInfo, FsCheckInfo and ChunkMatrix to
leilfs-api's camelCase fields and update InfoSection field accesses.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
git commit -F /tmp/p2-task3.txt
```

---

## Task 4: ServersSection — chunkservers, metadata servers, metaloggers, inotifiers

**Files:**
- Modify: `go/web/src/types.ts` (`Server`, `MetadataServer`, `Metalogger`, `INotifier`)
- Modify: `go/web/src/components/ServersSection.tsx`

**Interfaces:**
- Consumes: `api.chunkservers`, `api.metadataServers`, `api.metaloggers`, `api.inotifiers`.
- Produces: the canonical `Server` interface (with `ip`, `connected`) that **Task 9** also relies on for the chart node dropdown and `ServerCharts`.

- [ ] **Step 1: Replace the four interfaces**

In `types.ts`, set the canonical fields from the field map: `Server` (lines 1032–1047 — note the type stays named `Server` though leilfs-api calls it `Chunkserver`), `MetadataServer` (1153–1162), `Metalogger` (1094–1099), `INotifier` (`= Metalogger`, line 1101). Key changes: `ip_address`→`ip`, `is_disconnected`→`connected` (inverted boolean), all space/count fields to camelCase, `metadata_version`→`metadataVersion`.

- [ ] **Step 2: Update ServersSection.tsx field accesses**

Apply field map "ServersSection.tsx" (lines 1289–1305):
- Chunkserver rows: `s.is_disconnected` → `!s.connected`; `s.ip_address`→`s.ip`; `s.used_space`→`s.usedSpaceBytes`; `s.total_space`→`s.totalSpaceBytes`; `s.used_space_tobedeleted`→`s.usedSpaceToDeleteBytes`; `s.total_space_tobedeleted`→`s.totalSpaceToDeleteBytes`; `s.chunks_tobedeleted`→`s.chunksToDelete`; `s.error_count`→`s.errorCount` (if referenced).
- MetadataServer columns: `s.ip_address`→`s.ip`; `s.metadata_version`→`s.metadataVersion`.
- Metalogger/INotifier columns: `l.ip_address`→`l.ip`.

- [ ] **Step 3: Build**

Run: `cd /home/jorge/Work/leilfs-monitoring/go/web && npm run build`
Expected: success.

- [ ] **Step 4: Commit**

```bash
cd /home/jorge/Work/leilfs-monitoring
cat > /tmp/p2-task4.txt <<'EOF'
feat(web): migrate ServersSection to canonical node shapes

Switch Server/MetadataServer/Metalogger/INotifier to camelCase fields
(ip_address->ip, is_disconnected->connected inverted, space/count renames) and
update ServersSection accordingly.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
git commit -F /tmp/p2-task4.txt
```

---

## Task 5: DisksSection — structural disk shape

**Files:**
- Modify: `go/web/src/types.ts` (`Disk`, `DiskStats`, add `DiskError`, `DiskStatsTriple`)
- Modify: `go/web/src/components/DisksSection.tsx`

**Interfaces:**
- Consumes: `api.disks` (already `?verbose=true` from Task 2).
- Produces: nothing other tasks depend on.

This task has the 4 structural changes flagged in the field map (lines 356–362, 989–995). Read field map section 3 (lines 212–379) in full before starting.

- [ ] **Step 1: Replace the disk interfaces**

In `types.ts`, replace `DiskStats` and `Disk` and add `DiskError`, `DiskStatsTriple` from the field map (lines 1049–1092). Note: the verbose-only stat fields are `number | null`.

- [ ] **Step 2: Path — concatenate chunkserver + path**

In `DisksSection.tsx`, the legacy `disk.path` was `"<chunkserver>:<path>"`. Canonical splits them. Render the path as `` `${disk.chunkserver}:${disk.path}` `` everywhere the old `disk.path` was shown.

- [ ] **Step 3: lastError — object/null instead of string**

Legacy `disk.last_error` was a human string and the component checks `disk.last_error.toLowerCase().includes("no errors")`. Replace with a null check and a formatted display:
```tsx
const errText = disk.lastError === null
  ? "No errors"
  : `chunk ${disk.lastError.chunkId} @ ${new Date(disk.lastError.timestamp * 1000).toLocaleString()}`;
const errClass = disk.lastError === null ? "" : "MISSING";
```
Use `errText`/`errClass` where `disk.last_error` was rendered/classed.

- [ ] **Step 4: stats nesting + field renames**

The legacy `disk[`${range}_stats`]` accessor becomes `disk.stats[range]` where `range` is `"minute" | "hour" | "day"`. Adjust the range keys accordingly (legacy used `minute_stats`/`hour_stats`/`day_stats`; new uses `minute`/`hour`/`day`). Apply the per-field renames from field map lines 1320–1328:
- `st.read_bytes_persecond`→`st.readBytesPerSecond ?? 0`, `st.written_bytes_persecond`→`st.writeBytesPerSecond ?? 0`
- `st.read_usec`→`st.readUsec`, `st.read_usec_avg`→`st.readUsecAvg ?? 0`, `st.read_usec_max`→`st.readUsecMax`
- `st.written_usec`→`st.writeUsec`, `st.written_usec_avg`→`st.writeUsecAvg ?? 0`, `st.written_usec_max`→`st.writeUsecMax`
- `st.fsync_usec`→`st.fsyncUsec`, `st.fsync_usec_avg`→`st.fsyncUsecAvg ?? 0`, `st.fsync_usec_max`→`st.fsyncUsecMax`
- `st.read_block_size_avg`→`st.readBlockSizeAvg ?? 0`, `st.written_block_size_avg`→`st.writeBlockSizeAvg ?? 0`
- `st.read_ops`→`st.readOps`, `st.write_ops`→`st.writeOps`, `st.fsync_ops`→`st.fsyncOps`

- [ ] **Step 5: status text**

Canonical `disk.status` is a lowercase enum (`"ok"`, `"marked_for_removal"`, `"damaged"`, …). The existing `statusClass()` uses `.includes("damaged")`/`.includes("scanning")`, which still matches. Disk space fields: `disk.used_space`→`disk.usedSpaceBytes`, `disk.total_space`→`disk.totalSpaceBytes`, `disk.chunks` unchanged. (Optional: add a display-name map so users see "OK" instead of "ok"; not required — note it as a follow-up.)

- [ ] **Step 6: Build**

Run: `cd /home/jorge/Work/leilfs-monitoring/go/web && npm run build`
Expected: success.

- [ ] **Step 7: Commit**

```bash
cd /home/jorge/Work/leilfs-monitoring
cat > /tmp/p2-task5.txt <<'EOF'
feat(web): migrate DisksSection to canonical disk shape

Adopt leilfs-api's disk model: split chunkserver/path (joined for display),
lastError object-or-null (was a string), nested stats.{minute,hour,day} (was
flat *_stats), nullable verbose stat fields, and camelCase renames throughout.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
git commit -F /tmp/p2-task5.txt
```

---

## Task 6: MountsSection — flags array, pointer→value

**Files:**
- Modify: `go/web/src/types.ts` (`Mount`, `OperationStats`)
- Modify: `go/web/src/components/MountsSection.tsx`

**Interfaces:**
- Consumes: `api.mounts`.

Read field map section 4 (lines 382–525) before starting.

- [ ] **Step 1: Replace `Mount` and `OperationStats`**

In `types.ts`, set the canonical fields from the field map (lines 1103–1143). Key changes: `flags` becomes `string[]`; `minGoal`/`maxGoal`/`minTrashTime`/`maxTrashTime` are values (not nullable); `currentOpStats`/`lastHourOpStats` are values (not nullable). `OP_NAMES` stays unchanged (op-stat keys are identical single words).

- [ ] **Step 2: Update MountsSection.tsx**

Apply field map "MountsSection.tsx" (lines 1330–1346): `session_id`→`sessionId`, `ip_address`→`ip`, `mounted_path`→`mountedPath`, `root_uid`→`rootUid`, `root_gid`→`rootGid`, `map_all_uid`→`mapAllUid`, `map_all_gid`→`mapAllGid`, `min_goal`→`minGoal`, `max_goal`→`maxGoal`, `min_trash_time`→`minTrashTime`, `max_trash_time`→`maxTrashTime`, `mount_info`→`mountInfo`. The ops accessor `which` literals become `"currentOpStats" | "lastHourOpStats"`; `m[which]` is now always non-null (the `as OperationStats | null` cast + null guard can be removed). If `flags` is displayed anywhere, render `m.flags.join(", ")`.

- [ ] **Step 3: Build**

Run: `cd /home/jorge/Work/leilfs-monitoring/go/web && npm run build`
Expected: success.

- [ ] **Step 4: Commit**

```bash
cd /home/jorge/Work/leilfs-monitoring
cat > /tmp/p2-task6.txt <<'EOF'
feat(web): migrate MountsSection to canonical mount shape

Adopt leilfs-api's mount model: flags as string[], goals/trash-times and op-stats
as non-null values, and camelCase field renames.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
git commit -F /tmp/p2-task6.txt
```

---

## Task 7: ConfigSection — exports flags array

**Files:**
- Modify: `go/web/src/types.ts` (`Export`)
- Modify: `go/web/src/components/ConfigSection.tsx`

**Interfaces:**
- Consumes: `api.exports`, `api.goals` (ConfigSection renders both; `Goal` is unchanged — field map section 11).

- [ ] **Step 1: Replace `Export`**

In `types.ts`, set `Export` to the canonical fields (field map lines 1145–1151): `ip_from`→`ipFrom`, `ip_to`→`ipTo`, `flags` becomes `string[]` (`path` unchanged).

- [ ] **Step 2: Update ConfigSection.tsx**

Rename `e.ip_from`→`e.ipFrom`, `e.ip_to`→`e.ipTo`. Wherever `flags` is displayed, render `e.flags.join(", ")`. `Goal` fields (`id`/`name`/`definition`) are unchanged.

- [ ] **Step 3: Build**

Run: `cd /home/jorge/Work/leilfs-monitoring/go/web && npm run build`
Expected: success.

- [ ] **Step 4: Commit**

```bash
cd /home/jorge/Work/leilfs-monitoring
cat > /tmp/p2-task7.txt <<'EOF'
feat(web): migrate ConfigSection exports to canonical shape

Export.ipFrom/ipTo renames and flags as string[] (joined for display).

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
git commit -F /tmp/p2-task7.txt
```

---

## Task 8: ChunksSection + chunkhealth — map→array restructure

**Files:**
- Modify: `go/web/src/types.ts` (`ChunkHealth`, add `ChunkHealthGoal`, `ChunkHealthTotals`)
- Modify: `go/web/src/chunkhealth.ts`
- Modify: `go/web/src/components/ChunksSection.tsx`

**Interfaces:**
- Consumes: `api.chunkHealth`, `api.goals`.

This is the biggest structural change. Read field map section 13 (lines 901–980) and the `chunkhealth.ts` rewrite (lines 1348–1381) before starting.

- [ ] **Step 1: Replace `ChunkHealth` and add the helper types**

In `types.ts`, replace the map-based `ChunkHealth` with the canonical array form and add `ChunkHealthGoal` and `ChunkHealthTotals` (field map lines 1202–1222).

- [ ] **Step 2: Rewrite `mapGoalHealth` and `goalChunkSums`**

`chunkhealth.ts` currently cross-joins the keyed maps with a separate `Goal[]`. Canonical `ChunkHealth.goals` already embeds `goalId`, `name`, `total`, `safe`, `endangered`, `lost`, `replication`, `deletion`, plus a `totals` object. Rewrite per field map lines 1352–1378:
```ts
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
Keep the existing `MappedGoalHealth` shape that `ChunksSection` consumes (adjust it only if the component needs it). For `goalChunkSums(..., attribute)`, prefer `health.totals[attribute]` when a `health` argument is available; otherwise retain the manual column-sum fallback. **Preserve the exact downstream shape `ChunksSection` reads** — confirm by reading `ChunksSection.tsx` and not changing its render contract beyond what these types force.

- [ ] **Step 3: Simplify ChunksSection fetch**

`ChunksSection.tsx` fetches both `api.chunkHealth(master)` and `api.goals(master)` and passes both to `mapGoalHealth`. The goal **names** are now embedded in `health.goals`, so the separate goals fetch is no longer needed for chunk-health mapping. Drop the `api.goals` call here if it is used *only* for chunk health; keep it if the component also renders a goals list. Verify by reading the component.

- [ ] **Step 4: Build**

Run: `cd /home/jorge/Work/leilfs-monitoring/go/web && npm run build`
Expected: success.

- [ ] **Step 5: Commit**

```bash
cd /home/jorge/Work/leilfs-monitoring
cat > /tmp/p2-task8.txt <<'EOF'
feat(web): migrate chunk health to canonical goals array

Replace the goal-keyed maps with leilfs-api's goals[] (name/total/safe/
endangered/lost/replication/deletion embedded) plus a totals object; rewrite
mapGoalHealth/goalChunkSums and drop the now-redundant goals fetch for chunk
health.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
git commit -F /tmp/p2-task8.txt
```

---

## Task 9: Charts via leilfs-api + node dropdown

**Files:**
- Modify: `go/web/src/charts.ts`
- Modify: `go/web/src/components/ChartsSection.tsx`
- Modify: `go/web/src/app.tsx`

**Interfaces:**
- Consumes: `api.chunkservers` (canonical `Server` with `ip`/`connected`, from Task 4); `api.metadataServers` (canonical `MetadataServer` with `ip`/`personality`, from Task 4); leilfs-api `GET /api/v1/charts?id=&node=` (Phase 1).
- Produces: the final user-facing shell. Keeps the **two** chart pages (Masters, Chunkservers), each enumerating its nodes. No dropdown.

Implements **Design decision 1**. Read `charts.ts`, `ChartsSection.tsx`, `app.tsx` before starting.

- [ ] **Step 1: charts.ts — fetch from leilfs-api by node**

Replace `getCSV` and thread a `node` selector instead of `host`/`port`:
```ts
async function getCSV(chart: ChartInfo, node: string, range: number): Promise<string> {
  const url = new URL("/api/v1/charts", location.origin);
  url.searchParams.set("id", String(chart.id + range));
  if (node) url.searchParams.set("node", node);   // empty node = the configured master
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.text();
}
```
Change `fetchChartData(chart, host, port, range)` to `fetchChartData(chart, node, range)` and pass `node` to `getCSV`. The chart catalog ids and all CSV parsing/transform logic are unchanged (leilfs-api forwards the same uint32 id to the same CHART command and returns the same CSV).

- [ ] **Step 2: ChartsSection.tsx — node-based cards, two enumerated pages**

Change `ChartCard` and `ChartContainer` to take a single `node: string` instead of `host`/`port` (update the `ChartCard` `useEffect` dependency from `[chart.id, host, port, range]` to `[chart.id, node, range]`; pass `node` into `fetchChartData`).

Keep `ChartsSection`'s `{ which: "master" | "servers" }` prop and split into two enumerations:

```tsx
export function ChartsSection({ which, reloadKey }: { which: "master" | "servers"; reloadKey: number }) {
  return which === "master"
    ? <MasterCharts reloadKey={reloadKey} />
    : <ChunkserverCharts reloadKey={reloadKey} />;
}

function MasterCharts({ reloadKey }: { reloadKey: number }) {
  // Enumerate masters from metadata-servers. Phase-1 leilfs-api can only target
  // the configured master (node=""), so every master block uses node="" today;
  // the enumeration is structured for future per-master targeting.
  const { data, error, loading } = useFetch<MetadataServer[]>(() => api.metadataServers(MASTER), [reloadKey]);
  if (loading) return <p>Loading…</p>;
  if (error) return <p class="MISSING">{error}</p>;
  const masters = (data ?? []).filter((s) => s.personality === "master");
  const list = masters.length ? masters : [{ ip: "", hostname: "", personality: "master" } as MetadataServer];
  return (
    <>
      {list.map((m) => (
        <ChartContainer
          key={m.ip || "master"}
          title={`Master ${m.hostname ? `${m.hostname} (${m.ip})` : m.ip || "(configured)"} charts`}
          node=""                              /* Phase-1: configured master only */
          charts={masterCharts}
          cls="masterCharts"
        />
      ))}
    </>
  );
}

function ChunkserverCharts({ reloadKey }: { reloadKey: number }) {
  const { data, error, loading } = useFetch<Server[]>(() => api.chunkservers(MASTER), [reloadKey]);
  if (loading) return <p>Loading…</p>;
  if (error) return <p class="MISSING">{error}</p>;
  const servers = (data ?? []).filter((s) => s.connected);
  return (
    <>
      {servers.map((s) => (
        <ChartContainer
          key={s.ip}
          title={`Chunkserver ${s.hostname ? `${s.hostname} ` : ""}(${s.ip}) charts`}
          node={s.ip}
          charts={chunkServerCharts}
          cls="chunkServerCharts"
        />
      ))}
    </>
  );
}
```
`MASTER` is the shared constant `{ host: "sfsmaster", port: 9421 }` (the `api.*` arg is ignored by leilfs-api but the signatures still take it); import it or define a module-local const. Update imports: add `MetadataServer` from `../types`; keep `Server`.

- [ ] **Step 3: app.tsx — remove the free-text selector, keep both chart pages**

- Remove `form` state, `applyMaster`, and the two `<input>`s + `Go` button.
- Keep a constant `master` (`{ host: "sfsmaster", port: 9421 }`) passed to data sections so their signatures are unchanged. Keep `reloadKey` and the `Refresh` button.
- Replace the `.master-selector` block with just the Refresh control:
```tsx
<div class="master-selector">
  <button class="button" onClick={() => setReloadKey((k) => k + 1)}>Refresh</button>
</div>
```
- **Keep both chart nav entries** (`master-charts`, `server-charts`) in `SECTIONS` and `renderSection`. Update the two chart cases to drop the now-unused `master` prop:
```tsx
case "master-charts": return <ChartsSection which="master" reloadKey={reloadKey} />;
case "server-charts": return <ChartsSection which="servers" reloadKey={reloadKey} />;
```
Data section cases keep `master={master}`.

- [ ] **Step 4: Build**

Run: `cd /home/jorge/Work/leilfs-monitoring/go/web && npm run build`
Expected: success.

- [ ] **Step 5: Commit**

```bash
cd /home/jorge/Work/leilfs-monitoring
cat > /tmp/p2-task9.txt <<'EOF'
feat(web): charts via leilfs-api, enumerated per page

Fetch charts from leilfs-api's /api/v1/charts?id=&node= (empty node = the
configured master) and remove the free-text host/port + Go control. Keep two
chart pages: Masters enumerates master(s) from metadata-servers (Phase-1 targets
the configured master via node=""), Chunkservers enumerates connected
chunkservers (node=<ip>).

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
git commit -F /tmp/p2-task9.txt
```

---

## Task 10: Deploy wiring — compose + vite dev proxy

**Files:**
- Modify: `compose.yaml`
- Modify: `go/web/vite.config.ts`

**Interfaces:**
- Produces: a runnable stack where `leil-monitoring-go` proxies to a leilfs-api service.

- [ ] **Step 1: compose.yaml — add leilfs-api, drop leil-api-go, repoint**

- Add a `leilfs-api` service (image or build per how leilfs-api is published; if no published image, reference its repo build context — note for the operator). Environment: `LEILFS_MASTER_ENDPOINTS=${SAUNAFS_MASTER_HOST:-sfsmaster}:${SAUNAFS_MASTER_PORT:-9421}`; expose its port (default 8080).
- Remove the `leil-api-go` service block.
- Change `leil-monitoring-go`'s `LEIL_API_URL` to `http://leilfs-api:8080` and its `depends_on` to `leilfs-api`.
- Leave the separate legacy Python `leil-api` service alone unless the operator wants it gone (out of scope; note it).

- [ ] **Step 2: vite.config.ts — dev proxy to leilfs-api**

Point the dev proxy default at leilfs-api and proxy the `/api/v1` prefix:
```ts
const apiTarget = process.env.LEIL_API_URL || "http://localhost:8080";
// server.proxy:
"/api": apiTarget,
"/docs": apiTarget,
"/openapi.json": apiTarget,
```
(`/api` already covers `/api/v1`.)

- [ ] **Step 3: Validate compose**

Run: `cd /home/jorge/Work/leilfs-monitoring && docker compose config >/dev/null && echo OK`
Expected: `OK` (compose file parses). If `docker` is unavailable, note it and skip.

- [ ] **Step 4: Commit**

```bash
cd /home/jorge/Work/leilfs-monitoring
cat > /tmp/p2-task10.txt <<'EOF'
chore(deploy): point monitoring at leilfs-api

Add a leilfs-api service, remove the intermediate leil-api-go, repoint
leil-monitoring-go's LEIL_API_URL, and update the vite dev proxy target.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
git commit -F /tmp/p2-task10.txt
```

---

## Manual end-to-end verification (after Task 10)

Bring up leilfs-api + leil-monitoring against the integration cluster (or a real master), then:
- Load the SPA; confirm each section renders: Info, Chunks, Servers, Disks, Config, Mounts.
- Disks: paths show `chunkserver:path`, "No errors"/error display correct, per-range stats populate.
- Charts → Master Charts page: the master's charts load (node=""). Charts → Server Charts page: one block per connected chunkserver loads (node=ip).
- Confirm no requests hit the removed `leil-api` (all go to `/api/v1/*` → leilfs-api).
- Confirm the SPA build embedded in `leil-monitoring` serves at `/`.

---

## Self-Review

**Spec coverage** (design spec → task):
- Delete leil-api + apiclient + leilfs → Task 1. ✓
- Repoint leil-monitoring proxy → Task 1 (no path rewrite; verified). ✓
- SPA api.ts → /api/v1/* → Task 2. ✓
- SPA types/components canonical → Tasks 3–8 (every endpoint in the field map covered). ✓
- charts.ts → /api/v1/charts → Task 9. ✓
- Remove host/port+Go; keep two enumerated chart pages → Task 9. ✓
- compose + vite → Task 10. ✓
- Cutover single-shot: the branch as a whole is the cutover; each task builds green; runtime correctness verified end-to-end after Task 10. ✓

**Placeholder scan:** Rename details are delegated to the committed field-map doc with exact line citations (not "TBD"); structural changes (Tasks 1, 5, 8, 9, 10) carry full code. No "add error handling"-style vagueness.

**Type consistency:** Interface NAMES are preserved across `api.ts` (Task 2) and the section tasks (3–8); `Server` keeps its name though it maps leilfs-api's `Chunkserver`. `ChartsSection` keeps its `which: "master" | "servers"` prop; only the internal card wiring changes (`host`/`port` → `node`), and Task 9 updates the only caller (`app.tsx`). `fetchChartData` signature change (`host,port`→`node`) is contained within Task 9 (charts.ts + ChartsSection are its only users).

**Risks called out:** Multi-master chart targeting is a noted future leilfs-api enhancement (today the Masters page targets the configured master via `node=""`). The `leilfs/` deletion is gated on a re-verified import check (Task 1 Step 1). leilfs-api must be deployed (Phase 1) before this stack runs.
