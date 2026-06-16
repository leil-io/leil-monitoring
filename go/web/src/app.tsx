import { useEffect, useState } from "preact/hooks";
import type { Master } from "./api";
import { InfoSection } from "./components/InfoSection";
import { ChunksSection } from "./components/ChunksSection";
import { ServersSection } from "./components/ServersSection";
import { DisksSection } from "./components/DisksSection";
import { ConfigSection } from "./components/ConfigSection";
import { MountsSection } from "./components/MountsSection";
import { ChartsSection } from "./components/ChartsSection";

const SECTIONS = [
  { id: "info", label: "Info" },
  { id: "chunks", label: "Chunks" },
  { id: "servers", label: "Servers" },
  { id: "disks", label: "Disks" },
  { id: "config", label: "Config" },
  { id: "mounts", label: "Mounts" },
  { id: "master-charts", label: "Master Charts" },
  { id: "server-charts", label: "Server Charts" },
] as const;

type SectionId = (typeof SECTIONS)[number]["id"];

function currentHash(): SectionId {
  const h = location.hash.replace(/^#/, "");
  return (SECTIONS.find((s) => s.id === h)?.id ?? "info") as SectionId;
}

function renderSection(id: SectionId, master: Master, reloadKey: number) {
  switch (id) {
    case "info": return <InfoSection master={master} reloadKey={reloadKey} />;
    case "chunks": return <ChunksSection master={master} reloadKey={reloadKey} />;
    case "servers": return <ServersSection master={master} reloadKey={reloadKey} />;
    case "disks": return <DisksSection master={master} reloadKey={reloadKey} />;
    case "config": return <ConfigSection master={master} reloadKey={reloadKey} />;
    case "mounts": return <MountsSection master={master} reloadKey={reloadKey} />;
    case "master-charts": return <ChartsSection master={master} which="master" reloadKey={reloadKey} />;
    case "server-charts": return <ChartsSection master={master} which="servers" reloadKey={reloadKey} />;
  }
}

export function App() {
  const [section, setSection] = useState<SectionId>(currentHash());
  const [master, setMaster] = useState<Master>({ host: "sfsmaster", port: 9421 });
  const [form, setForm] = useState({ host: "sfsmaster", port: "9421" });
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const onHash = () => setSection(currentHash());
    addEventListener("hashchange", onHash);
    return () => removeEventListener("hashchange", onHash);
  }, []);

  const applyMaster = () => {
    const port = parseInt(form.port, 10);
    setMaster({ host: form.host || "sfsmaster", port: Number.isNaN(port) ? 9421 : port });
    setReloadKey((k) => k + 1);
  };

  return (
    <>
      <header id="header">
        <div class="logo">
          <a href="#info">
            <img src="/logomini.svg" alt="logo" width={110} height={38} />
          </a>
        </div>
        <nav class="menu">
          {SECTIONS.map((s) => (
            <a class={`button${section === s.id ? " active" : ""}`} href={`#${s.id}`}>
              {s.label}
            </a>
          ))}
        </nav>
        <div class="master-selector">
          <input
            type="text"
            value={form.host}
            size={20}
            aria-label="master host"
            onInput={(e) => setForm({ ...form, host: (e.target as HTMLInputElement).value })}
          />
          <input
            type="number"
            value={form.port}
            aria-label="master port"
            onInput={(e) => setForm({ ...form, port: (e.target as HTMLInputElement).value })}
          />
          <button class="button" onClick={applyMaster}>Go</button>
          <button class="button" onClick={() => setReloadKey((k) => k + 1)}>Refresh</button>
        </div>
      </header>
      <div id="container">{renderSection(section, master, reloadKey)}</div>
    </>
  );
}
