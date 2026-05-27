import { describe, expect, it } from "vitest";
import {
  categoryLabel,
  chartAxisLabel,
  fmtMoney,
  formatChatError,
  periodLabel,
  primaryEntityName,
} from "../utils";

describe("fmtMoney", () => {
  it("formats positive amounts", () => {
    expect(fmtMoney(1234.5)).toBe("$1,234.50");
  });

  it("formats signed amounts", () => {
    expect(fmtMoney(-10, true)).toBe("-$10.00");
    expect(fmtMoney(10, true)).toBe("+$10.00");
  });

  it("handles null", () => {
    expect(fmtMoney(null)).toBe("—");
  });
});

describe("categoryLabel", () => {
  it("maps known categories", () => {
    expect(categoryLabel("SOFTWARE")).toBe("Software");
    expect(categoryLabel("UNKNOWN")).toBe("Unknown");
  });
});

describe("periodLabel", () => {
  it("returns range for multiple months", () => {
    expect(periodLabel([{ month: "2025-01" }, { month: "2025-03" }])).toBe("2025-01 → 2025-03");
  });

  it("returns fallback when empty", () => {
    expect(periodLabel([])).toBe("All periods");
  });
});

describe("chart labels", () => {
  it("extracts primary client name before description", () => {
    expect(primaryEntityName("BrightPath Marketing — Social media graphics")).toBe(
      "BrightPath Marketing"
    );
  });

  it("shortens long axis labels", () => {
    const long = "A".repeat(40);
    expect(chartAxisLabel(long, 20).length).toBeLessThanOrEqual(20);
  });
});

describe("formatChatError", () => {
  it("hides raw 429 errors", () => {
    const msg = formatChatError(new Error("429 RESOURCE_EXHAUSTED quota exceeded"));
    expect(msg).toContain("rate-limited");
    expect(msg).not.toContain("RESOURCE_EXHAUSTED");
  });
});
