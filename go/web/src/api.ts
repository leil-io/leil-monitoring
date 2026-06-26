// Typed fetch wrappers around leilfs-api's canonical /api/v1/* endpoints.

import type {
  ChunkHealth, ChunkMatrix, ChunkOperationsInfo, Disk, Export, FsCheckInfo,
  Goal, INotifier, Metalogger, MetadataServer, Mount, Server, SystemInfo,
} from "./types";

export interface Master {
  host: string;
  port: number;
}

async function get<T>(path: string, _master: Master): Promise<T> {
  const url = new URL(path, location.origin);
  const res = await fetch(url);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* ignore non-JSON body */
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  info:                (m: Master) => get<SystemInfo>("/api/v1/cluster", m),
  chunkHealth:         (m: Master) => get<ChunkHealth>("/api/v1/cluster/chunk-health", m),
  chunkservers:        (m: Master) => get<Server[]>("/api/v1/chunkservers", m),
  disks:               (m: Master) => get<Disk[]>("/api/v1/disks?verbose=true", m),
  mounts:              (m: Master) => get<Mount[]>("/api/v1/mounts", m),
  metadataServers:     (m: Master) => get<MetadataServer[]>("/api/v1/metadata-servers", m),
  inotifiers:          (m: Master) => get<INotifier[]>("/api/v1/inotifiers", m),
  fsCheckInfo:         (m: Master) => get<FsCheckInfo>("/api/v1/cluster/fs-check", m),
  chunkOperationsInfo: (m: Master) => get<ChunkOperationsInfo>("/api/v1/cluster/chunk-operations", m),
  goals:               (m: Master) => get<Goal[]>("/api/v1/goals", m),
  chunkMatrix:         (m: Master) => get<ChunkMatrix>("/api/v1/cluster/chunk-matrix", m),
  metaloggers:         (m: Master) => get<Metalogger[]>("/api/v1/metaloggers", m),
  exports:             (m: Master) => get<Export[]>("/api/v1/exports", m),
};
