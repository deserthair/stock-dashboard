import { describe, expect, it } from "vitest";

import {
  directionClass,
  fmtDate,
  fmtErLabel,
  fmtNum,
  fmtPct,
  fmtRevenue,
  fmtSigma,
  fmtSigned,
} from "@/lib/format";

describe("fmtPct", () => {
  it("renders positive with + prefix and %", () => {
    expect(fmtPct(1.84)).toBe("+1.84%");
  });
  it("renders negatives", () => {
    expect(fmtPct(-0.62)).toBe("-0.62%");
  });
  it("returns em dash on null", () => {
    expect(fmtPct(null)).toBe("—");
  });
  it("respects digits override", () => {
    expect(fmtPct(0.12345, { digits: 4 })).toBe("+0.1235%");
  });
});

describe("fmtNum", () => {
  it("fixed to given digits", () => {
    expect(fmtNum(58.4201, 2)).toBe("58.42");
  });
  it("em dash for null", () => {
    expect(fmtNum(null)).toBe("—");
  });
});

describe("fmtSigned / fmtSigma", () => {
  it("signed number prefixes +", () => {
    expect(fmtSigned(5.2, 1)).toBe("+5.2");
    expect(fmtSigned(-3.1, 1)).toBe("-3.1");
  });
  it("sigma renders sigma char", () => {
    expect(fmtSigma(2.1)).toBe("+2.1σ");
  });
});

describe("fmtRevenue", () => {
  it("billions", () => {
    expect(fmtRevenue(2_910_000_000)).toBe("2.91B");
  });
  it("millions", () => {
    expect(fmtRevenue(162_000_000)).toBe("162M");
  });
  it("em dash for null", () => {
    expect(fmtRevenue(null)).toBe("—");
  });
});

describe("fmtDate / fmtErLabel", () => {
  it("extracts mm/dd", () => {
    expect(fmtDate("2026-04-23")).toBe("04/23");
  });
  it("concatenates date + time-of-day", () => {
    expect(fmtErLabel("2026-04-23", "AMC")).toBe("04/23 AMC");
  });
  it("handles null date", () => {
    expect(fmtErLabel(null, "AMC")).toBe("—");
  });
});

describe("directionClass", () => {
  it("positive → up colour", () => {
    expect(directionClass(1)).toBe("text-up");
  });
  it("negative → down colour", () => {
    expect(directionClass(-1)).toBe("text-down");
  });
  it("near-zero → dim", () => {
    expect(directionClass(0.05)).toBe("text-fg-dim");
  });
  it("null → dim", () => {
    expect(directionClass(null)).toBe("text-fg-dim");
  });
});
