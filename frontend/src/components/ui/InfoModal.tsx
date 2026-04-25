"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import type { InfoContent } from "./InfoIcon";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function InfoModal({
  info,
  onClose,
}: {
  info: InfoContent;
  onClose: () => void;
}) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [onClose]);

  async function ask() {
    if (!question.trim() || loading) return;
    setLoading(true);
    setError(null);
    setAnswer(null);
    try {
      const res = await fetch(`${BASE}/api/ai/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          section_title: info.title,
          section_explanation: info.explanation,
          page_context: info.pageContext ?? "",
          question: question.trim(),
        }),
      });
      if (!res.ok) {
        const body = await res.text();
        throw new Error(body || `${res.status} ${res.statusText}`);
      }
      const data = (await res.json()) as { answer: string };
      setAnswer(data.answer);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  if (!mounted) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      onClick={onClose}
    >
      <div
        className="relative max-h-[85vh] w-full max-w-xl overflow-y-auto rounded-sm border border-border bg-panel shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="sticky top-0 flex items-center border-b border-border bg-panel-2 px-4 py-2.5">
          <span className="text-[10px] uppercase tracking-[0.15em] text-fg-faint">
            What is this?
          </span>
          <span className="ml-3 font-semibold text-fg">{info.title}</span>
          <button
            type="button"
            aria-label="Close"
            onClick={onClose}
            className="ml-auto text-fg-dim transition-colors hover:text-fg"
          >
            ×
          </button>
        </header>

        <div className="space-y-4 px-4 py-4">
          <section>
            <h3 className="mb-1.5 text-[10px] uppercase tracking-[0.15em] text-accent">
              Plain English
            </h3>
            <p className="whitespace-pre-line text-[13px] leading-relaxed text-fg">
              {info.explanation}
            </p>
          </section>

          <section className="border-t border-border pt-4">
            <h3 className="mb-1.5 text-[10px] uppercase tracking-[0.15em] text-accent">
              Ask AI
            </h3>
            <p className="mb-2 text-[11px] text-fg-dim">
              Type a follow-up question. We&apos;ll send it along with this
              section&apos;s context.
            </p>
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. Why does this matter for my watchlist?"
              rows={3}
              className="w-full rounded-sm border border-border bg-panel-2 px-2.5 py-2 text-[12px] text-fg outline-none placeholder:text-fg-faint focus:border-accent"
            />
            <div className="mt-2 flex items-center gap-2">
              <button
                type="button"
                disabled={loading || !question.trim()}
                onClick={ask}
                className="rounded-sm border border-accent bg-accent/10 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.1em] text-accent transition-colors hover:bg-accent/20 disabled:cursor-not-allowed disabled:border-border disabled:bg-panel-2 disabled:text-fg-faint"
              >
                {loading ? "Asking…" : "Ask AI"}
              </button>
              {error && (
                <span className="text-[11px] text-down">Error: {error}</span>
              )}
            </div>

            {answer && (
              <div className="mt-3 rounded-sm border border-border bg-panel-2 p-3">
                <h4 className="mb-1.5 text-[10px] uppercase tracking-[0.15em] text-fg-faint">
                  Answer
                </h4>
                <p className="whitespace-pre-line text-[13px] leading-relaxed text-fg">
                  {answer}
                </p>
              </div>
            )}
          </section>
        </div>
      </div>
    </div>,
    document.body,
  );
}
