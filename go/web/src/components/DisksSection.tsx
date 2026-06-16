import type { Master } from "../api";
import { api } from "../api";
import { useFetch } from "../hooks";
import { humanizeBytes, percent } from "../format";
import { ProgressBar } from "./ProgressBar";
import type { Disk, DiskStats } from "../types";

function statusClass(status: string): string {
  const s = status.toLowerCase();
  if (s.includes("damaged") || s.includes("error")) return "MISSING";
  if (s.includes("scanning")) return "ENDANGERED";
  return "NORMAL";
}

const ms = (usec: number) => `${(usec / 1000).toFixed(1)} ms`;

function StatsTable({ disks, range }: { disks: Disk[]; range: "minute" | "hour" | "day" }) {
  const key = `${range}_stats` as const;
  return (
    <table class="FR sortable" cellSpacing="0">
      <thead>
        <tr><th colSpan={12}>Disk stats ({range} stats)</th></tr>
        <tr>
          <th>Path</th><th>Read</th><th>Write</th><th>Read time (avg)</th><th>Read time (max)</th>
          <th>Write time (avg)</th><th>Write time (max)</th><th>Fsync time (avg)</th><th>Fsync time (max)</th>
          <th>Read ops</th><th>Write ops</th><th>Fsync ops</th>
        </tr>
      </thead>
      <tbody>
        {disks.map((disk, idx) => {
          const st: DiskStats = disk[key];
          return (
            <tr class={`C${(idx % 2) + 1}`}>
              <td>{disk.path}</td>
              <td style={{ textAlign: "right" }} title={`${Math.trunc(st.read_bytes_persecond)} B/s`}>{humanizeBytes(st.read_bytes_persecond)}/s</td>
              <td style={{ textAlign: "right" }} title={`${Math.trunc(st.written_bytes_persecond)} B/s`}>{humanizeBytes(st.written_bytes_persecond)}/s</td>
              <td style={{ textAlign: "right" }} title={`${st.read_usec} μs total`}>{ms(st.read_usec_avg)}</td>
              <td style={{ textAlign: "right" }} title={`${st.read_usec_max} μs max`}>{ms(st.read_usec_max)}</td>
              <td style={{ textAlign: "right" }} title={`${st.written_usec} μs total`}>{ms(st.written_usec_avg)}</td>
              <td style={{ textAlign: "right" }} title={`${st.written_usec_max} μs max`}>{ms(st.written_usec_max)}</td>
              <td style={{ textAlign: "right" }} title={`${st.fsync_usec} μs total`}>{ms(st.fsync_usec_avg)}</td>
              <td style={{ textAlign: "right" }} title={`${st.fsync_usec_max} μs max`}>{ms(st.fsync_usec_max)}</td>
              <td style={{ textAlign: "right" }} title={`Average ${Math.trunc(st.read_block_size_avg)} bytes/op`}>{st.read_ops}</td>
              <td style={{ textAlign: "right" }} title={`Average ${Math.trunc(st.written_block_size_avg)} bytes/op`}>{st.write_ops}</td>
              <td style={{ textAlign: "right" }}>{st.fsync_ops}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

export function DisksSection({ master, reloadKey }: { master: Master; reloadKey: number }) {
  const { data, error, loading } = useFetch<Disk[]>(
    () => api.disks(master),
    [master.host, master.port, reloadKey],
  );

  if (loading) return <p>Loading…</p>;
  if (error) return <p class="MISSING">{error}</p>;
  const disks = data ?? [];

  return (
    <>
      <table class="FR" cellSpacing="0">
        <thead>
          <tr><th colSpan={8}>Disks</th></tr>
          <tr>
            <th>#</th><th>Path</th><th>Status</th><th>Last Error</th>
            <th>Chunks</th><th>Used Space</th><th>Total Space</th><th class="PROGBAR">% Used</th>
          </tr>
        </thead>
        <tbody>
          {disks.map((disk, idx) => (
            <tr class={`C${(idx % 2) + 1}`}>
              <td style={{ textAlign: "right" }}>{idx + 1}</td>
              <td>{disk.path}</td>
              <td style={{ textAlign: "right" }} class={statusClass(disk.status)}>{disk.status}</td>
              <td style={{ textAlign: "right" }} class={disk.last_error.toLowerCase().includes("no errors") ? "NORMAL" : "MISSING"}>{disk.last_error}</td>
              <td style={{ textAlign: "right" }}>{disk.chunks}</td>
              <td style={{ textAlign: "right" }}>{humanizeBytes(disk.used_space)}</td>
              <td style={{ textAlign: "right" }}>{humanizeBytes(disk.total_space)}</td>
              <td><ProgressBar pct={percent(disk.used_space, disk.total_space)} /></td>
            </tr>
          ))}
        </tbody>
      </table>

      <StatsTable disks={disks} range="minute" />
      <StatsTable disks={disks} range="hour" />
      <StatsTable disks={disks} range="day" />
    </>
  );
}
