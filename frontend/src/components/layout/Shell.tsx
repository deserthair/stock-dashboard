import type { UniverseRow } from "@/lib/types";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

export function Shell({
  universe,
  activeTicker,
  children,
}: {
  universe: UniverseRow[];
  activeTicker?: string;
  children: React.ReactNode;
}) {
  return (
    <>
      <TopBar />
      <div className="flex">
        <Sidebar universe={universe} activeTicker={activeTicker} />
        <main className="min-w-0 flex-1 p-4">{children}</main>
      </div>
    </>
  );
}
