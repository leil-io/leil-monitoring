import { useState } from "preact/hooks";
import type { ComponentChildren } from "preact";

export type Align = "left" | "right" | "center";

export interface Column<T> {
  header: ComponentChildren;
  align?: Align;
  cell: (row: T, index: number) => ComponentChildren;
  // When present the column is sortable; returns a comparable value.
  sort?: (row: T) => number | string;
  className?: string;
}

function compare(a: number | string, b: number | string, asc: boolean): number {
  if (typeof a === "number" && typeof b === "number") {
    return asc ? a - b : b - a;
  }
  const r = String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: "base" });
  return asc ? r : -r;
}

interface Props<T> {
  title: ComponentChildren;
  columns: Column<T>[];
  rows: T[];
}

// DataTable renders a dense .FR sortable table matching the Python look:
// a title header row, a column header row, and zebra-striped C1/C2 body rows.
export function DataTable<T>({ title, columns, rows }: Props<T>) {
  const [sortIdx, setSortIdx] = useState(-1);
  const [asc, setAsc] = useState(true);

  let display = rows;
  if (sortIdx >= 0 && columns[sortIdx]?.sort) {
    const acc = columns[sortIdx].sort!;
    display = [...rows].sort((a, b) => compare(acc(a), acc(b), asc));
  }

  const onHeaderClick = (i: number) => {
    if (!columns[i].sort) return;
    if (i === sortIdx) setAsc(!asc);
    else {
      setSortIdx(i);
      setAsc(true);
    }
  };

  return (
    <table class="FR sortable" cellSpacing="0">
      <thead>
        <tr>
          <th colSpan={columns.length}>{title}</th>
        </tr>
        <tr>
          {columns.map((c, i) => (
            <th
              style={{ cursor: c.sort ? "pointer" : "default" }}
              class={i === sortIdx ? (asc ? "asc" : "desc") : undefined}
              onClick={() => onHeaderClick(i)}
            >
              {c.header}
              {i === sortIdx ? (asc ? " ▲" : " ▼") : ""}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {display.map((row, idx) => (
          <tr class={`C${(idx % 2) + 1}`}>
            {columns.map((c) => (
              <td style={{ textAlign: c.align ?? "left" }} class={c.className}>
                {c.cell(row, idx)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
