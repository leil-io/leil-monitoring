// Ports of the server-side Jinja filters humanize_bytes and format_timestamp
// (src/leil_monitoring/main.py).

const BYTE_UNITS = ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"];

export function humanizeBytes(num: number, suffix = "B"): string {
  if (typeof num !== "number" || Number.isNaN(num)) return "N/A";
  let n = num;
  for (const unit of BYTE_UNITS) {
    if (Math.abs(n) < 1024.0) {
      return `${n.toFixed(1)} ${unit}${suffix}`;
    }
    n /= 1024.0;
  }
  return `${n.toFixed(1)} Yi${suffix}`;
}

export function formatTimestamp(ts: number | null | undefined): string {
  if (typeof ts !== "number" || ts === 0) return "N/A";
  const d = new Date(ts * 1000);
  const p = (x: number) => String(x).padStart(2, "0");
  return (
    `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ` +
    `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
  );
}

// percent computes used/total*100 guarding against zero, like the Jinja math.
export function percent(used: number, total: number): number {
  return total > 0 ? (used / total) * 100 : 0;
}
