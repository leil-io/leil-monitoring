import type { Master } from "../api";
import { api } from "../api";
import { useFetch, settle } from "../hooks";
import { humanizeBytes, percent } from "../format";
import { DataTable, type Column } from "./DataTable";
import { ProgressBar } from "./ProgressBar";
import type { INotifier, Metalogger, MetadataServer, Server } from "../types";

interface ServersData {
  metadata?: MetadataServer[];
  servers?: Server[];
  metaloggers?: Metalogger[];
  inotifiers?: INotifier[];
}

const metaCols: Column<MetadataServer>[] = [
  { header: "#", align: "right", cell: (s) => s.id, sort: (s) => s.id },
  { header: "Host", cell: (s) => s.hostname, sort: (s) => s.hostname ?? "" },
  { header: "IP", align: "center", cell: (s) => s.ip, sort: (s) => s.ip },
  { header: "Client Port", align: "center", cell: (s) => s.port, sort: (s) => s.port },
  { header: "Version", align: "center", cell: (s) => s.version, sort: (s) => s.version },
  { header: "Personality", align: "center", cell: (s) => s.personality, sort: (s) => s.personality },
  { header: "State", align: "center", cell: (s) => s.state, sort: (s) => s.state },
  { header: "Metadata Version", align: "right", cell: (s) => s.metadataVersion, sort: (s) => s.metadataVersion },
];

const loggerCols = (): Column<Metalogger>[] => [
  { header: "#", align: "right", cell: (l) => l.id, sort: (l) => l.id },
  { header: "Host", cell: (l) => l.hostname, sort: (l) => l.hostname ?? "" },
  { header: "IP", align: "center", cell: (l) => l.ip, sort: (l) => l.ip },
  { header: "Version", align: "center", cell: (l) => l.version, sort: (l) => l.version },
];

export function ServersSection({ master, reloadKey }: { master: Master; reloadKey: number }) {
  const { data, error, loading } = useFetch<ServersData>(async () => {
    const [metadata, servers, metaloggers, inotifiers] = await Promise.all([
      settle(api.metadataServers(master)),
      settle(api.chunkservers(master)),
      settle(api.metaloggers(master)),
      settle(api.inotifiers(master)),
    ]);
    return { metadata, servers, metaloggers, inotifiers };
  }, [master.host, master.port, reloadKey]);

  if (loading) return <p>Loading…</p>;
  if (error) return <p class="MISSING">{error}</p>;
  const d = data!;

  return (
    <>
      {d.metadata && <DataTable title="Metadata Servers" columns={metaCols} rows={d.metadata} />}

      {d.servers && (
        <table class="FR" cellSpacing="0">
          <thead>
            <tr><th colSpan={14}>Chunk Servers</th></tr>
            <tr>
              <th rowSpan={2}>#</th><th rowSpan={2}>Host</th><th rowSpan={2}>IP</th><th rowSpan={2}>Port</th>
              <th rowSpan={2}>Version</th><th rowSpan={2}>Label</th>
              <th colSpan={4}>'Regular' HDD Space</th><th colSpan={4}>'To Be Empty' HDD Space</th>
            </tr>
            <tr>
              <th>Chunks</th><th>Used</th><th>Total</th><th class="PROGBAR">% Used</th>
              <th>Chunks</th><th>Used</th><th>Total</th><th class="PROGBAR">% Used</th>
            </tr>
          </thead>
          <tbody>
            {d.servers.map((s, idx) => (
              <tr class={`C${(idx % 2) + 1}`}>
                {!s.connected ? (
                  <>
                    <td style={{ textAlign: "right" }}><span class="DISCONNECTED">{s.id}</span></td>
                    <td><span class="DISCONNECTED">{s.hostname}</span></td>
                    <td style={{ textAlign: "center" }}><span class="DISCONNECTED">{s.ip}</span></td>
                    <td style={{ textAlign: "center" }}><span class="DISCONNECTED">{s.port}</span></td>
                    <td colSpan={9}><span class="DISCONNECTED">Disconnected</span></td>
                  </>
                ) : (
                  <>
                    <td style={{ textAlign: "right" }}>{s.id}</td>
                    <td>{s.hostname}</td>
                    <td style={{ textAlign: "center" }}>{s.ip}</td>
                    <td style={{ textAlign: "center" }}>{s.port}</td>
                    <td style={{ textAlign: "center" }}>{s.version}</td>
                    <td class="LEFT">{s.label}</td>
                    <td style={{ textAlign: "right" }}>{s.chunks}</td>
                    <td style={{ textAlign: "right" }}>{humanizeBytes(s.usedSpaceBytes)}</td>
                    <td style={{ textAlign: "right" }}>{humanizeBytes(s.totalSpaceBytes)}</td>
                    <td><ProgressBar pct={percent(s.usedSpaceBytes, s.totalSpaceBytes)} px /></td>
                    <td style={{ textAlign: "right" }}>{s.chunksToDelete}</td>
                    <td style={{ textAlign: "right" }}>{humanizeBytes(s.usedSpaceToDeleteBytes)}</td>
                    <td style={{ textAlign: "right" }}>{humanizeBytes(s.totalSpaceToDeleteBytes)}</td>
                    <td><ProgressBar pct={percent(s.usedSpaceToDeleteBytes, s.totalSpaceToDeleteBytes)} px /></td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {d.metaloggers && <DataTable title="Metadata Backup Loggers" columns={loggerCols()} rows={d.metaloggers} />}
      {d.inotifiers && d.inotifiers.length > 0 && (
        <DataTable title="INotifier Loggers" columns={loggerCols()} rows={d.inotifiers} />
      )}
    </>
  );
}
