// Typed fetch wrappers around the leil-api JSON endpoints. Every call forwards
// the selected master host/port as query params (the API accepts these).

import type {
  ChunkHealth, ChunkMatrix, ChunkOperationsInfo, Disk, Export, FsCheckInfo,
  Goal, INotifier, Metalogger, MetadataServer, Mount, Server, SystemInfo,
} from "./types";

export interface Master {
  host: string;
  port: number;
}

async function get<T>(path: string, master: Master): Promise<T> {
  const url = new URL(path, location.origin);
  url.searchParams.set("masterhost", master.host);
  url.searchParams.set("masterport", String(master.port));
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
  info: (m: Master) => get<SystemInfo>("/api/info", m),
  chunkHealth: (m: Master) => get<ChunkHealth>("/api/chunkhealth", m),
  chunkservers: (m: Master) => get<Server[]>("/api/chunkservers", m),
  disks: (m: Master) => get<Disk[]>("/api/disks", m),
  mounts: (m: Master) => get<Mount[]>("/api/mounts", m),
  metadataServers: (m: Master) => get<MetadataServer[]>("/api/metadataservers", m),
  inotifiers: (m: Master) => get<INotifier[]>("/api/inotifiers", m),
  fsCheckInfo: (m: Master) => get<FsCheckInfo>("/api/fscheckinfo", m),
  chunkOperationsInfo: (m: Master) => get<ChunkOperationsInfo>("/api/chunkoperationsinfo", m),
  goals: (m: Master) => get<Goal[]>("/api/goals", m),
  chunkMatrix: (m: Master) => get<ChunkMatrix>("/api/chunkmatrix", m),
  metaloggers: (m: Master) => get<Metalogger[]>("/api/metaloggers", m),
  exports: (m: Master) => get<Export[]>("/api/exports", m),
};
