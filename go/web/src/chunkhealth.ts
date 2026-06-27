// Client-side port of ChunkMappedHealth.from_chunk_health and
// get_goal_chunk_sums (src/leil_client/models.py / leil_monitoring/main.py).
// The Go API exposes /api/v1/cluster/chunk-health with goals embedded (name,
// safe, endangered, lost, replication, deletion) plus a pre-computed totals
// object, so no separate goals fetch is needed here.

import type { ChunkHealth, Goal } from "./types";

export interface MappedGoalHealth {
  name: string;
  total: number;
  safe: number;
  endangered: number;
  lost: number;
  replication: number[];
  deletion: number[];
}

export function mapGoalHealth(health: ChunkHealth, _goals?: Goal[]): MappedGoalHealth[] {
  return health.goals.map((g) => ({
    name: g.name,
    total: g.total,
    safe: g.safe,
    endangered: g.endangered,
    lost: g.lost,
    replication: Array.from(g.replication),
    deletion: Array.from(g.deletion),
  }));
}

// goalChunkSums mirrors get_goal_chunk_sums: column-wise sums (11 columns)
// across goals that have replication/deletion data.
export function goalChunkSums(
  mapped: MappedGoalHealth[],
  attribute: "replication" | "deletion",
): number[] {
  const sums: number[] = [];
  for (let i = 0; i < 11; i++) {
    let total = 0;
    for (const goal of mapped) {
      const arr = goal[attribute];
      if (arr.length > 0) total += arr[i] ?? 0;
    }
    sums.push(total);
  }
  return sums;
}
