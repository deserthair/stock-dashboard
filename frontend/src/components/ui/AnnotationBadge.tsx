import type { Annotation } from "@/lib/interpret";
import { Tooltip } from "./Tooltip";

const TONE_CLASS: Record<Annotation["tone"], string> = {
  info: "border-border-hot text-fg-dim",
  warn: "border-[rgba(255,181,71,0.4)] text-amber",
  alert: "border-[rgba(255,92,92,0.4)] text-down",
};

export function AnnotationBadge({ ann }: { ann: Annotation | null }) {
  if (!ann) return null;
  return (
    <Tooltip tip={ann.hint}>
      <span
        className={[
          "ml-1.5 inline-block rounded-sm border px-1 py-0 text-[9px] uppercase tracking-[0.05em]",
          TONE_CLASS[ann.tone],
        ].join(" ")}
      >
        {ann.label}
      </span>
    </Tooltip>
  );
}
