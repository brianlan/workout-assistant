import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeAll } from "vitest";
import LibraryPage from "./LibraryPage";
import type { Video, Category } from "../types";

const mockCategories: Category[] = [
  { id: 1, name: "Strength", created_at: "2024-01-01T00:00:00" },
  { id: 2, name: "Cardio", created_at: "2024-01-01T00:00:00" },
];

const mockVideos: Video[] = [
  {
    id: 1,
    title: "Push-Up Workout",
    description: "Great push-up routine",
    category_id: 1,
    difficulty: "beginner",
    muscle_groups: '["chest"]',
    duration: 300,
    format: "mp4",
    file_size: 1000000,
    thumbnail_path: "/thumbs/1.jpg",
    file_path: "/videos/strength/1.mp4",
    source_url: null,
    status: "ready",
    imported_at: "2024-01-01T00:00:00",
  },
  {
    id: 2,
    title: "Squat Session",
    description: "Leg day workout",
    category_id: 2,
    difficulty: "intermediate",
    muscle_groups: '["legs"]',
    duration: 450,
    format: "mp4",
    file_size: 2000000,
    thumbnail_path: "/thumbs/2.jpg",
    file_path: "/videos/cardio/2.mp4",
    source_url: null,
    status: "ready",
    imported_at: "2024-01-01T00:00:00",
  },
];

beforeAll(() => {
  const mockFetch = vi.fn().mockImplementation((url: string) => {
    if (url.includes("/api/categories")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockCategories),
      });
    }
    if (url.includes("/api/videos")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockVideos),
      });
    }
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve([]),
    });
  });
  globalThis.fetch = mockFetch as unknown as typeof fetch;
});

describe("LibraryPage", () => {
  function renderWithRouter(ui: React.ReactElement) {
    return render(<MemoryRouter>{ui}</MemoryRouter>);
  }

  it("renders video cards with titles", async () => {
    renderWithRouter(<LibraryPage />);
    await waitFor(() => {
      expect(screen.getByText("Push-Up Workout")).toBeInTheDocument();
      expect(screen.getByText("Squat Session")).toBeInTheDocument();
    });
  });

  it("renders category filter", async () => {
    renderWithRouter(<LibraryPage />);
    await waitFor(() => {
      expect(screen.getByText("All Categories")).toBeInTheDocument();
      expect(screen.getByText("Strength")).toBeInTheDocument();
      expect(screen.getByText("Cardio")).toBeInTheDocument();
    });
  });

  it("renders search input", async () => {
    renderWithRouter(<LibraryPage />);
    await waitFor(() => {
      expect(screen.getByPlaceholderText("Search videos...")).toBeInTheDocument();
    });
  });

  it("renders import button", async () => {
    renderWithRouter(<LibraryPage />);
    await waitFor(() => {
      expect(screen.getByText("+ Import Video")).toBeInTheDocument();
    });
  });

  it("renders difficulty badges on video cards", async () => {
    renderWithRouter(<LibraryPage />);
    await waitFor(() => {
      expect(screen.getByText("beginner")).toBeInTheDocument();
      expect(screen.getByText("intermediate")).toBeInTheDocument();
    });
  });
});
