"use client";

import { useState } from "react";
import { InfoModal } from "./InfoModal";

export type InfoContent = {
  title: string;
  explanation: string;
  pageContext?: string;
};

export function InfoIcon({
  info,
  className,
}: {
  info: InfoContent;
  className?: string;
}) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        aria-label={`What is ${info.title}?`}
        onClick={(e) => {
          e.stopPropagation();
          e.preventDefault();
          setOpen(true);
        }}
        className={[
          "inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full",
          "border border-border bg-panel-2 text-[9px] font-bold text-fg-dim",
          "transition-colors hover:border-accent hover:text-accent",
          className ?? "",
        ].join(" ")}
      >
        i
      </button>
      {open && <InfoModal info={info} onClose={() => setOpen(false)} />}
    </>
  );
}
