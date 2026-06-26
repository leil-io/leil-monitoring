import { useState } from "preact/hooks";
import type { Master } from "../api";
import { api } from "../api";
import { useFetch } from "../hooks";
import { OP_NAMES, type Mount } from "../types";

function OpsTable({ title, mounts, which }: {
  title: string;
  mounts: Mount[];
  which: "currentOpStats" | "lastHourOpStats";
}) {
  return (
    <table class="FR sortable" cellSpacing="0">
      <thead>
        <tr><th colSpan={4 + OP_NAMES.length}>{title}</th></tr>
        <tr>
          <th>#</th><th>Host</th><th>IP</th><th>Mounted Path</th>
          {OP_NAMES.map((op) => <th>{op}</th>)}
        </tr>
      </thead>
      <tbody>
        {mounts.map((m, idx) => {
          const stats = m[which];
          return (
            <tr class={`C${(idx % 2) + 1}`}>
              <td style={{ textAlign: "right" }}>{m.id}</td>
              <td>{m.hostname}</td>
              <td style={{ textAlign: "center" }}>{m.ip}</td>
              <td>{m.mountedPath}</td>
              {OP_NAMES.map((op) => <td style={{ textAlign: "right" }}>{stats[op]}</td>)}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

export function MountsSection({ master, reloadKey }: { master: Master; reloadKey: number }) {
  const { data, error, loading } = useFetch<Mount[]>(
    () => api.mounts(master),
    [master.host, master.port, reloadKey],
  );
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  if (loading) return <p>Loading…</p>;
  if (error) return <p class="MISSING">{error}</p>;
  const mounts = data ?? [];

  const toggle = (id: number) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  return (
    <>
      <table class="FR sortable" cellSpacing="0">
        <thead>
          <tr><th colSpan={15}>Connected Clients (Mounts)</th></tr>
          <tr>
            <th>#</th><th>Session ID</th><th>Host</th><th>IP</th><th>Version</th><th>Mounted Path</th>
            <th>Root UID</th><th>Root GID</th><th>MapAll UID</th><th>MapAll GID</th>
            <th>Min Goal</th><th>Max Goal</th><th>Min Trash Time</th><th>Max Trash Time</th><th>Mount Info</th>
          </tr>
        </thead>
        <tbody>
          {mounts.map((m, idx) => (
            <>
              <tr class={`C${(idx % 2) + 1}`} style={{ cursor: "pointer" }} onClick={() => toggle(m.id)}>
                <td style={{ textAlign: "right" }}>{m.id}</td>
                <td style={{ textAlign: "right" }}>{m.sessionId}</td>
                <td>{m.hostname}</td>
                <td style={{ textAlign: "center" }}>{m.ip}</td>
                <td style={{ textAlign: "center" }}>{m.version}</td>
                <td>{m.mountedPath}</td>
                <td>{m.rootUid}</td>
                <td>{m.rootGid}</td>
                <td>{m.mapAllUid}</td>
                <td>{m.mapAllGid}</td>
                <td>{m.minGoal}</td>
                <td>{m.maxGoal}</td>
                <td>{m.minTrashTime}</td>
                <td>{m.maxTrashTime}</td>
                <td>Click to view</td>
              </tr>
              {expanded.has(m.id) && (
                <tr>
                  <td colSpan={15}>
                    <div style={{ textAlign: "left", padding: "10px" }}>
                      <hr />
                      <pre style={{ whiteSpace: "pre-wrap", wordWrap: "break-word" }}>{m.mountInfo}</pre>
                    </div>
                  </td>
                </tr>
              )}
            </>
          ))}
        </tbody>
      </table>

      <OpsTable title="Operations (current)" mounts={mounts} which="currentOpStats" />
      <OpsTable title="Operations (last hour)" mounts={mounts} which="lastHourOpStats" />
    </>
  );
}
