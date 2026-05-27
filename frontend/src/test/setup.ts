import "@testing-library/jest-dom/vitest";

/** Recharts ResponsiveContainer requires ResizeObserver in jsdom. */
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};
