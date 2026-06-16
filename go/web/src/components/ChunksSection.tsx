import type { Master } from "../api";
import { api } from "../api";
import { useFetch } from "../hooks";
import { goalChunkSums, mapGoalHealth, type MappedGoalHealth } from "../chunkhealth";

const REP_HEADERS = Array.from({ length: 11 }, (_, i) =>
  i === 0 ? "0 copies" : i === 10 ? "10+ copies" : i === 1 ? "1 copy" : `${i} copies`,
);

export function ChunksSection({ master, reloadKey }: { master: Master; reloadKey: number }) {
  const { data, error, loading } = useFetch<MappedGoalHealth[]>(async () => {
    const [health, goals] = await Promise.all([api.chunkHealth(master), api.goals(master)]);
    return mapGoalHealth(health, goals);
  }, [master.host, master.port, reloadKey]);

  if (loading) return <p>Loading…</p>;
  if (error) return <p class="MISSING">{error}</p>;

  const goalmap = (data ?? []).filter((g) => g.total !== 0);
  const sum = (k: "safe" | "endangered" | "lost" | "total") =>
    goalmap.reduce((acc, g) => acc + g[k], 0);
  const repSums = goalChunkSums(data ?? [], "replication");
  const delSums = goalChunkSums(data ?? [], "deletion");

  const replicationHeader = (verb: string) => (
    <tr>
      <th>goal</th>
      {REP_HEADERS.map((h) => (
        <th class="PERC8">{h}<br />to {verb}</th>
      ))}
    </tr>
  );

  return (
    <>
      <table class="FR" cellSpacing="0">
        <tbody>
          <tr><th colSpan={5}>Chunk Statistics</th></tr>
          <tr><th>Goal</th><th>Safe Chunks</th><th>Endangered Chunks</th><th>Missing Chunks</th><th>All Chunks</th></tr>
          {goalmap.map((g) => (
            <tr class="CI">
              <th style={{ textAlign: "center" }} class="LEFT">{g.name}</th>
              <td style={{ textAlign: "center" }}>{g.safe}</td>
              <td style={{ textAlign: "center" }}>{g.endangered}</td>
              <td style={{ textAlign: "center" }}>{g.lost}</td>
              <td style={{ textAlign: "center" }}>{g.total}</td>
            </tr>
          ))}
          <tr>
            <th>all</th><th>{sum("safe")}</th><th>{sum("endangered")}</th><th>{sum("lost")}</th><th>{sum("total")}</th>
          </tr>
        </tbody>
      </table>

      <table class="FR" cellSpacing="0">
        <tbody>
          <tr><th colSpan={12}>Chunks which need replication</th></tr>
          {replicationHeader("replicate")}
          {goalmap.map((g) => (
            <tr class="CI">
              <th class="LEFT">{g.name}</th>
              {g.replication.map((v) => <td style={{ textAlign: "center" }}>{v}</td>)}
            </tr>
          ))}
          <tr><th>all</th>{repSums.map((s) => <th>{s}</th>)}</tr>
        </tbody>
      </table>

      <table class="FR" cellSpacing="0">
        <tbody>
          <tr><th colSpan={12}>Chunks which need deletion</th></tr>
          {replicationHeader("delete")}
          {goalmap.map((g) => (
            <tr class="CI">
              <th class="LEFT">{g.name}</th>
              {g.deletion.map((v) => <td style={{ textAlign: "center" }}>{v}</td>)}
            </tr>
          ))}
          <tr><th>all</th>{delSums.map((s) => <th>{s}</th>)}</tr>
        </tbody>
      </table>
    </>
  );
}
