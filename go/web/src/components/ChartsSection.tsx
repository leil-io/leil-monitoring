import { useEffect, useRef, useState } from "preact/hooks";
import Chart from "chart.js/auto";
import "chartjs-adapter-date-fns";
import { api } from "../api";
import type { Master } from "../api";
import { useFetch } from "../hooks";
import { chunkServerCharts, fetchChartData, masterCharts, timeRange, type ChartInfo } from "../charts";
import type { MetadataServer, Server } from "../types";

const MASTER: Master = { host: "sfsmaster", port: 9421 };

function ChartCard({ chart, node }: { chart: ChartInfo; node: string }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const chartRef = useRef<Chart | null>(null);
  const [range, setRange] = useState<number>(timeRange.SHORT.id);
  const [err, setErr] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetchChartData(chart, node, range)
      .then(({ labels, series }) => {
        if (cancelled || !canvasRef.current) return;
        const datasets = series.map((s) => ({
          label: s.label, data: s.data, borderWidth: 2, fill: true, tension: 0.1,
        }));
        if (chartRef.current) {
          chartRef.current.data.labels = labels;
          chartRef.current.data.datasets = datasets as never;
          chartRef.current.update();
        } else {
          chartRef.current = new Chart(canvasRef.current, {
            type: "line",
            data: { labels, datasets: datasets as never },
            options: {
              responsive: true,
              scales: { x: { type: "time" }, y: { beginAtZero: true } },
            },
          });
        }
        setErr("");
      })
      .catch((e) => !cancelled && setErr(String(e?.message ?? e)));
    return () => {
      cancelled = true;
    };
  }, [chart.id, node, range]);

  useEffect(() => () => chartRef.current?.destroy(), []);

  return (
    <div class="chart-container">
      <canvas ref={canvasRef} />
      <div class="chart-options">
        {Object.values(timeRange).map((tr) => (
          <div class={`button${range === tr.id ? " active" : ""}`} onClick={() => setRange(tr.id)}>
            {tr.name}
          </div>
        ))}
      </div>
      {err && <div class="MISSING" style={{ padding: "4px" }}>{err}</div>}
    </div>
  );
}

function ChartContainer({ title, node, charts, cls }: {
  title: string; node: string; charts: ChartInfo[]; cls: string;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div class={`chart-containers ${cls}`}>
      <div class="chart-header" onClick={() => setOpen(!open)}>
        {title}
        <div class={open ? "arrow-up" : "arrow-down"} />
      </div>
      <div class={`chart-content${open ? " show" : ""}`}>
        {open && charts.map((c) => <ChartCard key={c.name} chart={c} node={node} />)}
      </div>
    </div>
  );
}

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
