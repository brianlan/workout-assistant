import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  getCategories,
  getVideos,
  uploadVideo,
  importVideoUrl,
  getVideoThumbnailUrl,
} from "../api/client";
import type { Category, Video } from "../types";

function formatDuration(seconds: number | null): string {
  if (!seconds) return "";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export default function LibraryPage() {
  const [videos, setVideos] = useState<Video[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [showImport, setShowImport] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadVideos = useCallback(async () => {
    try {
      const data = await getVideos({
        category_id: selectedCategory ?? undefined,
        search: search || undefined,
      });
      setVideos(data);
    } catch {
      // silently handle
    } finally {
      setLoading(false);
    }
  }, [selectedCategory, search]);

  useEffect(() => {
    getCategories().then(setCategories).catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    const timer = setTimeout(() => {
      loadVideos();
    }, search ? 300 : 0);
    return () => clearTimeout(timer);
  }, [loadVideos, search]);

  return (
    <div>
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Video Library</h1>
        <button
          onClick={() => setShowImport(true)}
          className="inline-flex items-center rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          + Import Video
        </button>
      </div>

      {/* Filters */}
      <div className="mb-6 flex flex-col gap-3 sm:flex-row">
        <select
          value={selectedCategory ?? ""}
          onChange={(e) =>
            setSelectedCategory(e.target.value ? Number(e.target.value) : null)
          }
          className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="">All Categories</option>
          {categories.map((cat) => (
            <option key={cat.id} value={cat.id}>
              {cat.name}
            </option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Search videos..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      {/* Video Grid */}
      {loading ? (
        <div className="py-12 text-center text-gray-500">Loading...</div>
      ) : videos.length === 0 ? (
        <div className="py-12 text-center text-gray-500">
          No videos found. Import your first video to get started.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {videos.map((video) => (
            <Link
              key={video.id}
              to={`/videos/${video.id}`}
              className="group overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm transition hover:shadow-md"
            >
              <div className="aspect-video w-full overflow-hidden bg-gray-100">
                <img
                  src={getVideoThumbnailUrl(video.id)}
                  alt={video.title}
                  className="h-full w-full object-cover"
                  loading="lazy"
                />
              </div>
              <div className="p-3">
                <h3 className="truncate text-sm font-medium text-gray-900 group-hover:text-blue-600">
                  {video.title}
                </h3>
                <div className="mt-1 flex items-center gap-2 text-xs text-gray-500">
                  {video.difficulty && (
                    <span className="rounded bg-gray-100 px-1.5 py-0.5 capitalize">
                      {video.difficulty}
                    </span>
                  )}
                  {video.duration && (
                    <span>{formatDuration(video.duration)}</span>
                  )}
                  {video.status === "transcoding" && (
                    <span className="rounded bg-yellow-100 px-1.5 py-0.5 text-yellow-800">
                      Transcoding
                    </span>
                  )}
                  {video.status === "importing" && (
                    <span className="rounded bg-blue-100 px-1.5 py-0.5 text-blue-800">
                      Importing
                    </span>
                  )}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Import Modal */}
      {showImport && (
        <ImportModal
          categories={categories}
          onClose={() => setShowImport(false)}
          onImported={() => {
            setShowImport(false);
            loadVideos();
          }}
        />
      )}
    </div>
  );
}

function ImportModal({
  categories,
  onClose,
  onImported,
}: {
  categories: Category[];
  onClose: () => void;
  onImported: () => void;
}) {
  const [tab, setTab] = useState<"file" | "url">("file");
  const [file, setFile] = useState<File | null>(null);
  const [url, setUrl] = useState("");
  const [categoryId, setCategoryId] = useState<number | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    if (!categoryId) {
      setError("Please select a category");
      return;
    }
    setSubmitting(true);
    setError("");

    try {
      const metadata = {
        title: title || undefined,
        description: description || undefined,
        difficulty: difficulty || undefined,
      };

      if (tab === "file") {
        if (!file) {
          setError("Please select a file");
          setSubmitting(false);
          return;
        }
        await uploadVideo(file, categoryId, metadata);
      } else {
        if (!url.trim()) {
          setError("Please enter a URL");
          setSubmitting(false);
          return;
        }
        await importVideoUrl(url.trim(), categoryId, metadata);
      }
      onImported();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Import failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-bold">Import Video</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="mb-4 flex border-b">
          <button
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium ${
              tab === "file"
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
            onClick={() => setTab("file")}
          >
            File Upload
          </button>
          <button
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium ${
              tab === "url"
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
            onClick={() => setTab("url")}
          >
            URL Import
          </button>
        </div>

        <div className="space-y-3">
          {tab === "file" ? (
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Video File
              </label>
              <input
                type="file"
                accept="video/*"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                className="block w-full text-sm text-gray-500 file:mr-4 file:rounded-md file:border-0 file:bg-blue-50 file:px-4 file:py-2 file:text-sm file:font-medium file:text-blue-700 hover:file:bg-blue-100"
              />
              {file && (
                <p className="mt-1 text-xs text-gray-500">{file.name}</p>
              )}
            </div>
          ) : (
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Video URL
              </label>
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://youtube.com/watch?v=..."
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          )}

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Category *
            </label>
            <select
              value={categoryId ?? ""}
              onChange={(e) => setCategoryId(e.target.value ? Number(e.target.value) : null)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="">Select category...</option>
              {categories.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Title (optional)
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Video title"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Description (optional)
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Difficulty (optional)
            </label>
            <select
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="">Not specified</option>
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
          </div>

          {error && (
            <p className="text-sm text-red-600">{error}</p>
          )}

          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {submitting ? "Importing..." : "Import"}
          </button>
        </div>
      </div>
    </div>
  );
}
