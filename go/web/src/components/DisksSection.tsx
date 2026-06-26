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
          const st: DiskStats = disk.stats[range];
          return (
            <tr class={`C${(idx % 2) + 1}`}>
              <td>{`${disk.chunkserver}:${disk.path}`}</td>
              <td style={{ textAlign: "right" }} title={`${Math.trunc(st.readBytesPerSecond ?? 0)} B/s`}>{humanizeBytes(st.readBytesPerSecond ?? 0)}/s</td>
              <td style={{ textAlign: "right" }} title={`${Math.trunc(st.writeBytesPerSecond ?? 0)} B/s`}>{humanizeBytes(st.writeBytesPerSecond ?? 0)}/s</td>
              <td style={{ textAlign: "right" }} title={`${st.readUsec} μs total`}>{ms(st.readUsecAvg ?? 0)}</td>
              <td style={{ textAlign: "right" }} title={`${st.readUsecMax} μs max`}>{ms(st.readUsecMax)}</td>
              <td style={{ textAlign: "right" }} title={`${st.writeUsec} μs total`}>{ms(st.writeUsecAvg ?? 0)}</td>
              <td style={{ textAlign: "right" }} title={`${st.writeUsecMax} μs max`}>{ms(st.writeUsecMax)}</td>
              <td style={{ textAlign: "right" }} title={`${st.fsyncUsec} μs total`}>{ms(st.fsyncUsecAvg ?? 0)}</td>
              <td style={{ textAlign: "right" }} title={`${st.fsyncUsecMax} μs max`}>{ms(st.fsyncUsecMax)}</td>
              <td style={{ textAlign: "right" }} title={`Average ${Math.trunc(st.readBlockSizeAvg ?? 0)} bytes/op`}>{st.readOps}</td>
              <td style={{ textAlign: "right" }} title={`Average ${Math.trunc(st.writeBlockSizeAvg ?? 0)} bytes/op`}>{st.writeOps}</td>
              <td style={{ textAlign: "right" }}>{st.fsyncOps}</td>
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
          {disks.map((disk, idx) => {
            const errText = disk.lastError === null
              ? "No errors"
              : `chunk ${disk.lastError.chunkId} @ ${new Date(disk.lastError.timestamp * 1000).toLocaleString()}`;
            const errClass = disk.lastError === null ? "" : "MISSING";
            return (
              <tr class={`C${(idx % 2) + 1}`}>
                <td style={{ textAlign: "right" }}>{idx + 1}</td>
                <td>{`${disk.chunkserver}:${disk.path}`}</td>
                <td style={{ textAlign: "right" }} class={statusClass(disk.status)}>{disk.status}</td>
                <td style={{ textAlign: "right" }} class={errClass || "NORMAL"}>{errText}</td>
                <td style={{ textAlign: "right" }}>{disk.chunks}</td>
                <td style={{ textAlign: "right" }}>{humanizeBytes(disk.usedSpaceBytes)}</td>
                <td style={{ textAlign: "right" }}>{humanizeBytes(disk.totalSpaceBytes)}</td>
                <td><ProgressBar pct={percent(disk.usedSpaceBytes, disk.totalSpaceBytes)} /></td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <StatsTable disks={disks} range="minute" />
      <StatsTable disks={disks} range="hour" />
      <StatsTable disks={disks} range="day" />
    </>
  );
}
