import type { Master } from "../api";
import { api } from "../api";
import { useFetch, settle } from "../hooks";
import { DataTable, type Column } from "./DataTable";
import type { Export, Goal } from "../types";

interface ConfigData {
  exports?: Export[];
  goals?: Goal[];
}

const exportCols: Column<Export>[] = [
  { header: "#", align: "right", cell: (e) => e.id, sort: (e) => e.id },
  { header: "IP From", align: "center", cell: (e) => e.ip_from, sort: (e) => e.ip_from },
  { header: "IP To", align: "center", cell: (e) => e.ip_to, sort: (e) => e.ip_to },
  { header: "Path", cell: (e) => e.path, sort: (e) => e.path },
  { header: "Flags", cell: (e) => e.flags, sort: (e) => e.flags },
];

const goalCols: Column<Goal>[] = [
  { header: "ID", align: "center", cell: (g) => g.id, sort: (g) => g.id },
  { header: "Name", align: "center", cell: (g) => g.name, sort: (g) => g.name },
  { header: "Definition", cell: (g) => g.definition, sort: (g) => g.definition },
];

export function ConfigSection({ master, reloadKey }: { master: Master; reloadKey: number }) {
  const { data, error, loading } = useFetch<ConfigData>(async () => {
    const [exports, goals] = await Promise.all([
      settle(api.exports(master)),
      settle(api.goals(master)),
    ]);
    return { exports, goals };
  }, [master.host, master.port, reloadKey]);

  if (loading) return <p>Loading…</p>;
  if (error) return <p class="MISSING">{error}</p>;
  const d = data!;

  return (
    <>
      {d.exports && d.exports.length > 0 && <DataTable title="Exports" columns={exportCols} rows={d.exports} />}
      {d.goals && d.goals.length > 0 && <DataTable title="Goals" columns={goalCols} rows={d.goals} />}
    </>
  );
}
