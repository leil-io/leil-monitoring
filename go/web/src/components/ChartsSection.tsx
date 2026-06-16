import { useEffect, useRef, useState } from "preact/hooks";
import Chart from "chart.js/auto";
import "chartjs-adapter-date-fns";
import type { Master } from "../api";
import { api } from "../api";
import { useFetch } from "../hooks";
import { chunkServerCharts, fetchChartData, masterCharts, timeRange, type ChartInfo } from "../charts";
import type { Server } from "../types";

function ChartCard({ chart, host, port }: { chart: ChartInfo; host: string; port: string | number }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const chartRef = useRef<Chart | null>(null);
  const [range, setRange] = useState<number>(timeRange.SHORT.id);
  const [err, setErr] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetchChartData(chart, host, port, range)
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
  }, [chart.id, host, port, range]);

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

function ChartContainer({ title, host, port, charts, cls }: {
  title: string; host: string; port: string | number; charts: ChartInfo[]; cls: string;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div class={`chart-containers ${cls}`}>
      <div class="chart-header" onClick={() => setOpen(!open)}>
        {title}
        <div class={open ? "arrow-up" : "arrow-down"} />
      </div>
      <div class={`chart-content${open ? " show" : ""}`}>
        {open && charts.map((c) => <ChartCard key={c.name} chart={c} host={host} port={port} />)}
      </div>
    </div>
  );
}

export function ChartsSection({ master, which, reloadKey }: {
  master: Master; which: "master" | "servers"; reloadKey: number;
}) {
  if (which === "master") {
    return (
      <ChartContainer
        title={`Master (${master.host}:${master.port}) charts`}
        host={master.host}
        port={master.port}
        charts={masterCharts}
        cls="masterCharts"
      />
    );
  }
  return <ServerCharts master={master} reloadKey={reloadKey} />;
}

function ServerCharts({ master, reloadKey }: { master: Master; reloadKey: number }) {
  const { data, error, loading } = useFetch<Server[]>(
    () => api.chunkservers(master),
    [master.host, master.port, reloadKey],
  );
  if (loading) return <p>Loading…</p>;
  if (error) return <p class="MISSING">{error}</p>;
  const servers = (data ?? []).filter((s) => !s.is_disconnected);
  return (
    <>
      {servers.map((s) => (
        <ChartContainer
          key={`${s.ip_address}:${s.port}`}
          title={`Chunkserver ${s.hostname} (${s.ip_address}:${s.port}) charts`}
          host={s.ip_address}
          port={s.port}
          charts={chunkServerCharts}
          cls="chunkServerCharts"
        />
      ))}
    </>
  );
}
