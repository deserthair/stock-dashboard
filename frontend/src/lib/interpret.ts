/**
 * Threshold annotations: tiny contextual labels rendered next to a number when
 * its value crosses a meaningful boundary (e.g. social-media z > 2 → "unusual").
 *
 * Returning `null` means the value is unremarkable; render nothing.
 *
 * Tone:
 *   - "info"  — dim grey, just a label
 *   - "warn"  — amber, worth a look
 *   - "alert" — red, extreme
 */
export type AnnotationTone = "info" | "warn" | "alert";

export interface Annotation {
  label: string;
  tone: AnnotationTone;
  hint: string;
}

export function annotate(
  metric:
    | "social_z"
    | "change_30d_pct"
    | "change_1d_pct"
    | "hypothesis_score"
    | "rs_vs_xly"
    | "jobs_30d_pct"
    | "sentiment_7d"
    | "news_volume_pct_baseline",
  v: number | null | undefined,
): Annotation | null {
  if (v === null || v === undefined || Number.isNaN(v)) return null;
  const a = Math.abs(v);
  switch (metric) {
    case "social_z":
      if (a >= 3) return { label: "extreme", tone: "alert", hint: "≥3σ above normal — top 0.1% of days" };
      if (a >= 2) return { label: "unusual", tone: "warn", hint: "≥2σ — roughly top 2% of days" };
      return null;
    case "change_30d_pct":
      if (a >= 25) return { label: "extreme", tone: "alert", hint: "|Δ 30D| ≥ 25%" };
      if (a >= 15) return { label: "outsized", tone: "warn", hint: "|Δ 30D| ≥ 15%" };
      return null;
    case "change_1d_pct":
      if (a >= 8) return { label: "gap", tone: "alert", hint: "|Δ 1D| ≥ 8% — likely news-driven" };
      if (a >= 4) return { label: "big move", tone: "warn", hint: "|Δ 1D| ≥ 4%" };
      return null;
    case "hypothesis_score":
      if (a >= 0.7) return { label: "strong", tone: "warn", hint: "high-confidence model lean" };
      if (a >= 0.4) return { label: "lean", tone: "info", hint: "moderate model lean" };
      return null;
    case "rs_vs_xly":
      if (a >= 8) return { label: v > 0 ? "leader" : "laggard", tone: "warn", hint: "|RS| ≥ 8 vs sector" };
      return null;
    case "jobs_30d_pct":
      if (v >= 20) return { label: "hiring", tone: "warn", hint: "+20% open-roles in 30D — expansion signal" };
      if (v <= -15) return { label: "freeze", tone: "alert", hint: "-15% open-roles — contraction signal" };
      return null;
    case "sentiment_7d":
      if (a >= 0.6) return { label: v > 0 ? "very pos" : "very neg", tone: "warn", hint: "|sentiment| ≥ 0.6 of [-1,+1]" };
      return null;
    case "news_volume_pct_baseline":
      if (v >= 200) return { label: "spike", tone: "alert", hint: "≥3× baseline news volume" };
      if (v >= 100) return { label: "elevated", tone: "warn", hint: "≥2× baseline news volume" };
      return null;
  }
}
