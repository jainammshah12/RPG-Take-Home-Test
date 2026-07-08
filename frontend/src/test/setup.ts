import "@testing-library/jest-dom/vitest";

/** Recharts ResponsiveContainer requires ResizeObserver in jsdom. */
globalThis.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};
