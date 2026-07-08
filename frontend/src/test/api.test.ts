import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchAnalysis, fetchConfig, fetchHealth } from "../api";

describe("api client", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("fetchHealth calls /api/health", async () => {
    const mock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ status: "ok" }), { status: 200 })
    );
    const data = await fetchHealth();
    expect(data.status).toBe("ok");
    expect(mock).toHaveBeenCalledWith(expect.stringContaining("/api/health"));
  });

  it("fetchConfig returns default shoebox", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ default_shoebox: "/data/shoebox" }), { status: 200 })
    );
    const data = await fetchConfig();
    expect(data.default_shoebox).toBe("/data/shoebox");
  });

  it("fetchAnalysis throws on error response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Service unavailable" }), { status: 503 })
    );
    await expect(fetchAnalysis("/data/shoebox")).rejects.toThrow("Service unavailable");
  });
});
