/**
 * Types consumed by the app are re-exported from the auto-generated OpenAPI
 * types in `api-types.ts`. Regenerate with `npm run gen:types` any time the
 * backend API surface changes.
 */
import type { components } from "./api-types";

type S = components["schemas"];

export type UniverseRow = S["UniverseRow"];
export type StatSummary = S["StatSummary"];
export type BriefingSection = S["BriefingSection"];
export type BriefingOut = S["BriefingOut"];
export type EventOut = S["EventOut"];
export type Severity = EventOut["severity"];
export type UpcomingEarnings = S["UpcomingEarnings"];
export type MacroRow = S["MacroRow"];
export type CompanyDetail = S["CompanyDetail"];
export type BriefingResponse = S["BriefingResponse"];
export type NewsItemOut = S["NewsItemOut"];
export type SocialPostOut = S["SocialPostOut"];
export type RedditPostOut = S["RedditPostOut"];
export type FilingOut = S["FilingOut"];
export type JobsSnapshotOut = S["JobsSnapshotOut"];
export type CorrelationOut = S["CorrelationOut"];
export type SourceRunOut = S["SourceRunOut"];
export type PriceBar = S["PriceBar"];
export type ChartMarker = S["ChartMarker"];
export type CompanyPriceHistory = S["CompanyPriceHistory"];
export type EarningsRow = S["EarningsRow"];
export type HypothesisTrackerRow = S["HypothesisTrackerRow"];
export type HypothesisTrackerSummary = S["HypothesisTrackerSummary"];
export type MacroSeriesDetail = S["MacroSeriesDetail"];
export type ScatterPointOut = S["ScatterPointOut"];
export type RegressionLineOut = S["RegressionLineOut"];
export type ScatterResponse = S["ScatterResponse"];
export type HeatmapResponse = S["HeatmapResponse"];
export type CoefficientOut = S["CoefficientOut"];
export type RegressionFitOut = S["RegressionFitOut"];
export type AnalysisAxesResponse = S["AnalysisAxesResponse"];
export type FeatureContribution = S["FeatureContribution"];
export type EventAttributionResponse = S["EventAttributionResponse"];

// MacroSeriesDetail.observations is typed as list[dict] on the backend.
// Narrow it here to the shape we actually produce and consume.
export interface MacroObservation {
  date: string;
  value: number | null;
}
