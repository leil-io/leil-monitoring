// ProgressBar reproduces the .box/.progress/.value markup from the Jinja
// templates. In "px" mode the fill width is pct*2 px (chunkservers table); in
// percent mode it is pct% (disks table).
export function ProgressBar({ pct, px }: { pct: number; px?: boolean }) {
  const width = px ? `${pct * 2}px` : `${Math.min(pct, 100)}%`;
  return (
    <div class="box">
      <div class="progress" style={{ width }} />
      <div class="value">{pct.toFixed(2)}</div>
    </div>
  );
}
