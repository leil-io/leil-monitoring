import type { Master } from "../api";
import { api } from "../api";
import { useFetch, settle } from "../hooks";
import { humanizeBytes, formatTimestamp } from "../format";
import type { ChunkMatrix, ChunkOperationsInfo, FsCheckInfo, SystemInfo } from "../types";

interface InfoData {
  info?: SystemInfo;
  ops?: ChunkOperationsInfo;
  matrix?: ChunkMatrix;
  fsCheck?: FsCheckInfo;
}

function matrixClass(i: number, j: number): string {
  if (i === 0) return j === 0 ? "DELETEREADY" : "DELETEPENDING";
  if (j === 0) return "MISSING";
  if (j > i) return "OVERGOAL";
  if (j < i) return j === 1 ? "ENDANGERED" : "UNDERGOAL";
  return "NORMAL";
}

const label = (i: number) => (i < 10 ? String(i) : "10+");

export function InfoSection({ master, reloadKey }: { master: Master; reloadKey: number }) {
  const { data, error, loading } = useFetch<InfoData>(async () => {
    const [info, ops, matrix, fsCheck] = await Promise.all([
      settle(api.info(master)),
      settle(api.chunkOperationsInfo(master)),
      settle(api.chunkMatrix(master)),
      settle(api.fsCheckInfo(master)),
    ]);
    return { info, ops, matrix, fsCheck };
  }, [master.host, master.port, reloadKey]);

  if (loading) return <p>Loading…</p>;
  if (error) return <p class="MISSING">{error}</p>;
  const d = data!;

  return (
    <>
      {d.info && (
        <table class="FR" cellSpacing="0">
          <thead>
            <tr><th colSpan={15}>Info</th></tr>
            <tr>
              <th>Version</th><th>RAM Used</th><th>Total Space</th><th>Avail Space</th>
              <th>Trash Space</th><th>Trash Files</th><th>Reserved Space</th><th>Reserved Files</th>
              <th>Total Objects</th><th>Directories</th><th>Files</th><th>Symlinks</th>
              <th>Chunks</th><th>All Copies</th><th>Regular Copies</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td style={{ textAlign: "center" }}>{d.info.version}</td>
              <td style={{ textAlign: "right" }}>{humanizeBytes(d.info.ram_used)}</td>
              <td style={{ textAlign: "right" }}>{humanizeBytes(d.info.total_space)}</td>
              <td style={{ textAlign: "right" }}>{humanizeBytes(d.info.avail_space)}</td>
              <td style={{ textAlign: "right" }}>{humanizeBytes(d.info.trash_space)}</td>
              <td style={{ textAlign: "right" }}>{d.info.trash_files}</td>
              <td style={{ textAlign: "right" }}>{humanizeBytes(d.info.reserved_space)}</td>
              <td style={{ textAlign: "right" }}>{d.info.reserved_files}</td>
              <td style={{ textAlign: "right" }}>{d.info.total_objects}</td>
              <td style={{ textAlign: "right" }}>{d.info.directories}</td>
              <td style={{ textAlign: "right" }}>{d.info.files}</td>
              <td style={{ textAlign: "right" }}>{d.info.symlinks}</td>
              <td style={{ textAlign: "right" }}>{d.info.chunks}</td>
              <td style={{ textAlign: "right" }}>{d.info.all_copies}</td>
              <td style={{ textAlign: "right" }}>{d.info.regular_copies}</td>
            </tr>
          </tbody>
        </table>
      )}

      {d.ops && d.ops.loop_start > 0 && (
        <table class="FR" cellSpacing="0">
          <thead>
            <tr><th colSpan={8}>Chunk Operations Info</th></tr>
            <tr><th colSpan={2}>Loop Time</th><th colSpan={4}>Deletions</th><th colSpan={2}>Replications</th></tr>
            <tr>
              <th>Start</th><th>End</th><th>Invalid</th><th>Unused</th>
              <th>Disk Clean</th><th>Over Goal</th><th>Under Goal</th><th>Rebalance</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td style={{ textAlign: "center" }}>{formatTimestamp(d.ops.loop_start)}</td>
              <td style={{ textAlign: "center" }}>{formatTimestamp(d.ops.loop_end)}</td>
              <td style={{ textAlign: "right" }}>{d.ops.delete_invalid}/{d.ops.delete_invalid + d.ops.not_delete_invalid}</td>
              <td style={{ textAlign: "right" }}>{d.ops.delete_unused}/{d.ops.delete_unused + d.ops.not_delete_unused}</td>
              <td style={{ textAlign: "right" }}>{d.ops.delete_disk_clean}/{d.ops.delete_disk_clean + d.ops.not_delete_disk_clean}</td>
              <td style={{ textAlign: "right" }}>{d.ops.delete_over_goal}/{d.ops.delete_over_goal + d.ops.not_delete_over_goal}</td>
              <td style={{ textAlign: "right" }}>{d.ops.replicate_under_goal}/{d.ops.replicate_under_goal + d.ops.not_replicate_under_goal}</td>
              <td style={{ textAlign: "right" }}>{d.ops.rebalance}</td>
            </tr>
          </tbody>
        </table>
      )}

      {d.matrix && (
        <table class="FR" cellSpacing="0">
          <tbody>
            <tr><th colSpan={13}>All chunks state matrix</th></tr>
            <tr>
              <th rowSpan={2} class="PERC4">needed<br />copies</th>
              <th colSpan={12} class="PERC96">Valid copies (standard goal chunks only)</th>
            </tr>
            <tr>
              {Array.from({ length: 11 }, (_, i) => <th class="PERC8">{label(i)}</th>)}
              <th class="PERC8">all</th>
            </tr>
            {d.matrix.matrix.map((row, i) => (
              <tr>
                <td style={{ textAlign: "center" }}>{label(i)}</td>
                {row.map((value, j) => (
                  <td style={{ textAlign: "right" }}>
                    <span class={matrixClass(i, j)}>{value > 0 ? value : "-"}</span>
                  </td>
                ))}
                <td style={{ textAlign: "right" }}>{row.reduce((a, b) => a + b, 0)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {d.fsCheck && d.fsCheck.loop_start > 0 && (
        <table class="FR" cellSpacing="0">
          <tbody>
            <tr><th colSpan={8}>Filesystem Check Info</th></tr>
            <tr>
              <th>Check Loop Start Time</th><th>Check Loop End Time</th><th>Files</th><th>Under-Goal Files</th>
              <th>Missing Files</th><th>Chunks</th><th>Under-Goal Chunks</th><th>Missing Chunks</th>
            </tr>
            <tr>
              <td style={{ textAlign: "center" }}>{formatTimestamp(d.fsCheck.loop_start)}</td>
              <td style={{ textAlign: "center" }}>{formatTimestamp(d.fsCheck.loop_end)}</td>
              <td style={{ textAlign: "right" }}>{d.fsCheck.files}</td>
              <td style={{ textAlign: "right" }}>{d.fsCheck.under_goal_files}</td>
              <td style={{ textAlign: "right" }}>{d.fsCheck.missing_files}</td>
              <td style={{ textAlign: "right" }}>{d.fsCheck.chunks}</td>
              <td style={{ textAlign: "right" }}>{d.fsCheck.under_goal_chunks}</td>
              <td style={{ textAlign: "right" }}>{d.fsCheck.missing_chunks}</td>
            </tr>
            {d.fsCheck.message && (
              <>
                <tr><th colSpan={8}>Important Messages</th></tr>
                <tr><td colSpan={8}><pre>{d.fsCheck.message}</pre></td></tr>
              </>
            )}
          </tbody>
        </table>
      )}
    </>
  );
}
