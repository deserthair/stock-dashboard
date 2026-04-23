import { describe, expect, it } from "vitest";

import {
  labelFor,
  presetRange,
  rangeFromSearch,
  toQueryString,
} from "@/lib/dateRange";

describe("rangeFromSearch", () => {
  it("returns empty when no params", () => {
    expect(rangeFromSearch({})).toEqual({ from: undefined, to: undefined });
  });
  it("accepts valid ISO dates", () => {
    expect(rangeFromSearch({ from: "2025-10-01", to: "2026-01-31" })).toEqual({
      from: "2025-10-01",
      to: "2026-01-31",
    });
  });
  it("drops malformed inputs silently", () => {
    expect(rangeFromSearch({ from: "garbage", to: "2026-01-31" })).toEqual({
      from: undefined,
      to: "2026-01-31",
    });
  });
  it("handles array-shaped duplicates", () => {
    expect(
      rangeFromSearch({ from: ["2025-10-01", "2026-01-01"], to: undefined }),
    ).toEqual({ from: "2025-10-01", to: undefined });
  });
});

describe("toQueryString", () => {
  it("empty when no bounds", () => {
    expect(toQueryString({})).toBe("");
  });
  it("emits leading ampersand so it slots into an existing query", () => {
    expect(toQueryString({ from: "2025-10-01", to: "2026-01-31" })).toBe(
      "&start_date=2025-10-01&end_date=2026-01-31",
    );
  });
  it("supports one-sided ranges", () => {
    expect(toQueryString({ from: "2025-10-01" })).toBe("&start_date=2025-10-01");
    expect(toQueryString({ to: "2026-01-31" })).toBe("&end_date=2026-01-31");
  });
});

describe("labelFor", () => {
  it("reports All time when unbounded", () => {
    expect(labelFor({})).toBe("All time");
  });
  it("formats two-sided range", () => {
    expect(labelFor({ from: "2025-10-01", to: "2026-01-31" })).toBe(
      "2025-10-01 → 2026-01-31",
    );
  });
  it("formats open-on-end", () => {
    expect(labelFor({ from: "2025-10-01" })).toBe("Since 2025-10-01");
  });
  it("formats open-on-start", () => {
    expect(labelFor({ to: "2026-01-31" })).toBe("Until 2026-01-31");
  });
});

describe("presetRange", () => {
  it("returns empty for undefined", () => {
    expect(presetRange(undefined)).toEqual({});
  });
  it("produces a valid N-day range", () => {
    const r = presetRange(30);
    expect(r.from).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(r.to).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(new Date(r.from!).getTime()).toBeLessThan(new Date(r.to!).getTime());
  });
});
