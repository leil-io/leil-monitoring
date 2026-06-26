// Port of src/leil_monitoring/static/charts.js. The chart catalogs and the
// CSV -> series transformation are preserved; only the data fetch points at the
// Go API endpoint (/api/cgicharts) and the Chart.js rendering is left to the
// caller (see ChartsSection.tsx). Vendored UMD libs are replaced by npm deps.

import Papa from "papaparse";
import { fromUnixTime } from "date-fns";

export const timeRange = {
  SHORT: { id: 0, name: "Short" },
  MEDIUM: { id: 1, name: "Medium" },
  LONG: { id: 2, name: "Long" },
  VERYLONG: { id: 3, name: "Very Long" },
} as const;

export const dataUnit = {
  NONE: 0,
  BYTE: 1,
  BIT: 2,
  CPUTIME: 3,
  TIME: 4,
} as const;

export interface ChartInfo {
  name: string;
  id: number;
  labels: string[];
  unit: number;
  rate?: boolean;
  sumSeries?: boolean;
}

export interface ChartData {
  labels: Date[];
  series: { label: string; data: number[] }[];
}

export const masterCharts: ChartInfo[] = [
  { name: "cpu", id: 91000, labels: ["Total CPU usage %", "Kernelspace CPU usage %"], unit: dataUnit.CPUTIME, rate: false, sumSeries: true },
  { name: "memory", id: 90200, labels: ["Memory used"], unit: dataUnit.BYTE, rate: false },
  { name: "chunkDels", id: 90020, labels: ["Chunk deletions"], unit: dataUnit.NONE, rate: false },
  { name: "chunkReps", id: 90030, labels: ["Chunk replications"], unit: dataUnit.NONE, rate: false },
  { name: "statfs", id: 90040, labels: ["statfs operations"], unit: dataUnit.NONE, rate: false },
  { name: "getattr", id: 90050, labels: ["getattr operations"], unit: dataUnit.NONE, rate: false },
  { name: "setattr", id: 90060, labels: ["setattr operations"], unit: dataUnit.NONE, rate: false },
  { name: "lookup", id: 90070, labels: ["lookup operations"], unit: dataUnit.NONE, rate: false },
  { name: "mkdir", id: 90080, labels: ["mkdir operations"], unit: dataUnit.NONE, rate: false },
  { name: "rmdir", id: 90090, labels: ["rmdir operations"], unit: dataUnit.NONE, rate: false },
  { name: "symlink", id: 90100, labels: ["symlink operations"], unit: dataUnit.NONE, rate: false },
  { name: "readlink", id: 90110, labels: ["readlink operations"], unit: dataUnit.NONE, rate: false },
  { name: "mknod", id: 90120, labels: ["mknod operations"], unit: dataUnit.NONE, rate: false },
  { name: "unlink", id: 90130, labels: ["unlink operations"], unit: dataUnit.NONE, rate: false },
  { name: "rename", id: 90140, labels: ["rename operations"], unit: dataUnit.NONE, rate: false },
  { name: "link", id: 90150, labels: ["link operations"], unit: dataUnit.NONE, rate: false },
  { name: "readdir", id: 90160, labels: ["readdir operations"], unit: dataUnit.NONE, rate: false },
  { name: "open", id: 90170, labels: ["open operations"], unit: dataUnit.NONE, rate: false },
  { name: "read", id: 90180, labels: ["read operations"], unit: dataUnit.NONE, rate: false },
  { name: "write", id: 90190, labels: ["write operations"], unit: dataUnit.NONE, rate: false },
  { name: "packetsReceived", id: 90210, labels: ["Packets received (per second)"], unit: dataUnit.NONE, rate: true },
  { name: "packetsSent", id: 90220, labels: ["Packets sent (per second)"], unit: dataUnit.NONE, rate: true },
  { name: "bytesReceived", id: 90230, labels: ["Bytes received (per second)"], unit: dataUnit.BYTE, rate: true },
  { name: "bytesSent", id: 90240, labels: ["Bytes sent (per second)"], unit: dataUnit.BYTE, rate: true },
];

export const chunkServerCharts: ChartInfo[] = [
  { name: "cpu", id: 91000, labels: ["Total CPU usage %", "Kernelspace CPU usage %"], unit: dataUnit.CPUTIME, rate: false, sumSeries: true },
  { name: "memory", id: 90300, labels: ["Memory used"], unit: dataUnit.BYTE },
  { name: "bytesReceivedClient", id: 91010, labels: ["Client/Chunkserver bytes received (per second)"], unit: dataUnit.BYTE, rate: true, sumSeries: true },
  { name: "bytesSentClient", id: 91020, labels: ["Client/Chunkserver bytes sent (per second)"], unit: dataUnit.BYTE, rate: true, sumSeries: true },
  { name: "bytesReadOverhead", id: 91030, labels: ["Bytes read total (per second)", "Bytes read overhead (per second)"], unit: dataUnit.BYTE, rate: true },
  { name: "bytesWrittenOverhead", id: 91040, labels: ["Bytes written total (per second)", "Bytes written overhead (per second)"], unit: dataUnit.BYTE, rate: true },
  { name: "bytesReceivedMaster", id: 90020, labels: ["Bytes received from master (per second)"], unit: dataUnit.BYTE, rate: true },
  { name: "bytesSentMaster", id: 90030, labels: ["Bytes sent to master (per second)"], unit: dataUnit.BYTE, rate: true },
  { name: "lowLevelReadOps", id: 91050, labels: ["Low-level read operations total", "Low-level read operations overhead"], unit: dataUnit.NONE, rate: false },
  { name: "lowLevelWriteOps", id: 91060, labels: ["Low-level write operations total", "Low-level write operations overhead"], unit: dataUnit.NONE, rate: false },
  { name: "highLevelWriteOps", id: 90170, labels: ["High-level write operations total"], unit: dataUnit.NONE, rate: false, sumSeries: true },
  { name: "dataReadTime", id: 90180, labels: ["Time of data read operations"], unit: dataUnit.TIME, rate: true },
  { name: "dataWriteTime", id: 90190, labels: ["Time of data write operations"], unit: dataUnit.TIME, rate: true },
  { name: "chunkReplications", id: 90200, labels: ["Number of chunk replications"], unit: dataUnit.NONE, rate: false },
  { name: "chunkCreations", id: 90210, labels: ["Number of chunk creations"], unit: dataUnit.NONE, rate: false },
  { name: "chunkDeletions", id: 90220, labels: ["Number of chunk deletions"], unit: dataUnit.NONE, rate: false },
  { name: "chunkTests", id: 90270, labels: ["Number of chunk tests"], unit: dataUnit.NONE, rate: false },
  { name: "chunkGCPurges", id: 90310, labels: ["Chunk purges (.dat, .met) by GC per minute"], unit: dataUnit.NONE, rate: false },
  { name: "spaceGrowth", id: 90320, labels: ["Storage Growth Rate (per second)"], unit: dataUnit.BYTE, rate: true },
  { name: "spaceReclamation", id: 90330, labels: ["Storage Reclamation Rate (per second)"], unit: dataUnit.BYTE, rate: true },
];

function secondPowerOf(num: number): [string, number] {
  if (typeof num !== "number" || Number.isNaN(num)) return ["N/A", 0];
  const units = ["μ", "m", ""];
  let n = num;
  let power = 0;
  for (const unit of units) {
    if (unit === units[units.length - 1] || Math.abs(n) < 1000) {
      return [`${unit}s`, power];
    }
    n /= 1000;
    power++;
  }
  return ["s", 0];
}

function bytePowerOf(num: number, unitType: number): [string, number] {
  if (typeof num !== "number" || Number.isNaN(num)) return ["N/A", 0];
  const units = ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"];
  const suffix = unitType === dataUnit.BIT ? "b" : unitType === dataUnit.BYTE ? "B" : "N/A";
  let n = num;
  let power = 0;
  for (const unit of units) {
    if (Math.abs(n) < 1024.0) return [`${unit}${suffix}`, power];
    n /= 1024.0;
    power++;
  }
  return [`Yi${suffix}`, power];
}

function getIntervalSecs(range: number): number {
  switch (range) {
    case timeRange.SHORT.id: return 60;
    case timeRange.MEDIUM.id: return 360;
    case timeRange.LONG.id: return 1800;
    case timeRange.VERYLONG.id: return 86400;
    default: throw new Error("Invalid time range");
  }
}

function parseCPUtime(time: number, range: number): number {
  return (time / (getIntervalSecs(range) * 1_000_000)) * 100;
}

function parseData(csvData: string): number[][] {
  const result = Papa.parse<string[]>(csvData, { header: false, skipEmptyLines: true });
  const rows = result.data.slice(1);
  return rows.map((row) =>
    row.map((cell) => (cell === "" || cell === null || cell === undefined ? 0 : Number(cell))),
  );
}

function getIntervalFromData(rows: number[][]): number {
  if (rows.length < 2) throw new Error("Not enough rows to determine interval");
  return rows[1][0] - rows[0][0];
}

function accumulateRows(rows: number[][]): number[][] {
  return rows.map((row) => {
    const accumulated: number[] = [row[0]];
    let running = 0;
    for (let i = row.length - 1; i >= 1; i--) {
      running += Number(row[i] || 0);
      accumulated[i] = running;
    }
    return accumulated;
  });
}

async function getCSV(chart: ChartInfo, node: string, range: number): Promise<string> {
  const url = new URL("/api/v1/charts", location.origin);
  url.searchParams.set("id", String(chart.id + range));
  if (node) url.searchParams.set("node", node);   // empty node = the configured master
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.text();
}

// fetchChartData reproduces setupChartInfo's transformation and returns Chart.js
// ready data (x-axis Date labels + named series).
export async function fetchChartData(
  chart: ChartInfo,
  node: string,
  range: number = timeRange.SHORT.id,
): Promise<ChartData> {
  const csv = await getCSV(chart, node, range);
  const rawRows = parseData(csv);
  const rows = chart.sumSeries ? accumulateRows(rawRows) : rawRows;
  const intervalSecs = getIntervalFromData(rows);
  const labels = rows.map((row) => fromUnixTime(row[0]));

  const mapCellValues = (transform: (cell: number) => number, rate = false): number[][] =>
    rows.map((row) => {
      const out: number[] = [];
      for (let i = 1; i < row.length; i++) {
        const cellValue = Number(row[i] || 0);
        let v = cellValue === 0 ? 0 : transform(cellValue);
        if (v !== 0 && rate) v = v / intervalSecs;
        out.push(v);
      }
      return out;
    });

  const peakMagnitude = (): number =>
    rows.reduce((max, row) => {
      let rowMax = 0;
      for (let i = 1; i < row.length; i++) rowMax = Math.max(rowMax, Number(row[i] || 0));
      return Math.max(max, rowMax);
    }, 0);

  const withSuffix = (lbls: string[], suffix = ""): string[] =>
    lbls.map((l) => (suffix ? `${l} ${suffix}` : `${l}`));

  let values: number[][];
  let yLabels: string[];

  switch (chart.unit) {
    case dataUnit.BYTE:
    case dataUnit.BIT: {
      let maxVal = peakMagnitude();
      if (maxVal !== 0 && chart.rate) maxVal = maxVal / intervalSecs;
      const [labelSize, power] = bytePowerOf(maxVal, chart.unit);
      values = mapCellValues((cell) => cell / Math.pow(1024, power), chart.rate);
      yLabels = withSuffix(chart.labels, `(${labelSize})`);
      break;
    }
    case dataUnit.CPUTIME: {
      values = mapCellValues((cell) => parseCPUtime(cell, range), chart.rate);
      yLabels = withSuffix(chart.labels);
      break;
    }
    case dataUnit.TIME: {
      let maxVal = peakMagnitude();
      if (maxVal !== 0 && chart.rate) maxVal = maxVal / intervalSecs;
      const [labelSize, power] = secondPowerOf(maxVal);
      values = mapCellValues((cell) => cell / Math.pow(1000, power), chart.rate);
      yLabels = withSuffix(chart.labels, `(${labelSize})`);
      break;
    }
    case dataUnit.NONE:
    default: {
      values = mapCellValues((cell) => cell, chart.rate);
      yLabels = withSuffix(chart.labels);
      break;
    }
  }

  // Pivot rows x cols into per-series arrays (setupLineChart logic).
  const series: { label: string; data: number[] }[] = [];
  for (const row of values) {
    for (let i = 0; i < row.length; i++) {
      if (typeof yLabels[i] === "undefined") continue;
      if (series.length < i + 1) series.push({ label: yLabels[i], data: [] });
      series[i].data.push(row[i]);
    }
  }

  return { labels, series };
}
