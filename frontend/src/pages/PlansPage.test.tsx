import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeAll } from "vitest";
import PlansPage from "./PlansPage";

beforeAll(() => {
  // Mock fetch to return 404 for active plan (no plan exists)
  const mockFetch = vi.fn().mockImplementation((url: string) => {
    if (url.includes("/plans/active")) {
      return Promise.resolve({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ detail: "No plans found" }),
      });
    }
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve([]),
    });
  });
  globalThis.fetch = mockFetch as unknown as typeof fetch;
});

function renderWithRouter(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe("PlansPage", () => {
  it("shows generate plan button when no active plan", async () => {
    renderWithRouter(<PlansPage />);
    await waitFor(() => {
      expect(screen.getByText("Generate Plan")).toBeInTheDocument();
    });
  });

  it("shows no active plan message", async () => {
    renderWithRouter(<PlansPage />);
    await waitFor(() => {
      expect(screen.getByText(/No active plan/i)).toBeInTheDocument();
    });
  });
});
