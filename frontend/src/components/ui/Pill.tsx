import type { ReactNode } from "react";

type Tone = "default" | "green" | "red" | "amber" | "cyan";

const TONE: Record<Tone, string> = {
  default: "border-border-hot text-fg",
  green: "border-[rgba(63,217,123,0.4)] text-up",
  red: "border-[rgba(255,92,92,0.4)] text-down",
  amber: "border-[rgba(255,181,71,0.4)] text-amber",
  cyan: "border-[rgba(92,213,255,0.4)] text-cyan",
};

export function Pill({
  tone = "default",
  children,
}: {
  tone?: Tone;
  children: ReactNode;
}) {
  return (
    <span
      className={`inline-block rounded-sm border bg-panel-2 px-1.5 py-[2px] text-[10px] tracking-[0.05em] ${TONE[tone]}`}
    >
      {children}
    </span>
  );
}

export function hypothesisTone(label: string | null | undefined): Tone {
  switch (label) {
    case "BEAT":
      return "green";
    case "MISS":
      return "red";
    case "MIXED":
      return "amber";
    default:
      return "default";
  }
}
