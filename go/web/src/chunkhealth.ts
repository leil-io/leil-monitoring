// Client-side port of ChunkMappedHealth.from_chunk_health and
// get_goal_chunk_sums (src/leil_client/models.py / leil_monitoring/main.py).
// The Go API exposes /api/chunkhealth and /api/goals separately, so the goal
// mapping that the Python server did is reproduced here.

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

export function mapGoalHealth(health: ChunkHealth, goals: Goal[]): MappedGoalHealth[] {
  return goals.map((goal) => {
    const key = String(goal.id);
    const safe = health.safe[key] ?? 0;
    const endangered = health.endangered[key] ?? 0;
    const lost = health.lost[key] ?? 0;
    return {
      name: goal.name,
      safe,
      endangered,
      lost,
      replication: health.replication[key] ?? [],
      deletion: health.deletion[key] ?? [],
      total: safe + endangered + lost,
    };
  });
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
