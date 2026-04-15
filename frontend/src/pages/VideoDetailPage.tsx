import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import ReactPlayer from "react-player";
import {
  getVideoStreamUrl,
  updateVideo,
  deleteVideo,
  getCategories,
} from "../api/client";
import type { Video, Category } from "../types";

export default function VideoDetailPage() {
  const { id } = useParams<{ id: string }>();
  const videoId = Number(id);
  const [video, setVideo] = useState<Video | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [editing, setEditing] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editDifficulty, setEditDifficulty] = useState("");
  const [editCategoryId, setEditCategoryId] = useState<number>(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCategories().then(setCategories).catch(() => {});
  }, []);

  useEffect(() => {
    if (!videoId) return;
    // Fetch video via the list endpoint (no single GET in current API)
    fetch(`/api/videos?search=&page=1&page_size=1000`)
      .then((r) => r.json())
      .then((videos: Video[]) => {
        const v = videos.find((vid) => vid.id === videoId);
        if (v) {
          setVideo(v);
          setEditTitle(v.title);
          setEditDescription(v.description ?? "");
          setEditDifficulty(v.difficulty ?? "");
          setEditCategoryId(v.category_id);
        }
      })
      .catch(() => setError("Failed to load video"))
      .finally(() => setLoading(false));
  }, [videoId]);

  const handleSave = async () => {
    try {
      const updated = await updateVideo(videoId, {
        title: editTitle,
        description: editDescription || undefined,
        difficulty: editDifficulty || undefined,
        category_id: editCategoryId !== video?.category_id ? editCategoryId : undefined,
      });
      setVideo(updated);
      setEditing(false);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
    }
  };

  const handleDelete = async () => {
    if (!confirm("Are you sure you want to delete this video?")) return;
    try {
      await deleteVideo(videoId);
      window.history.back();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete");
    }
  };

  if (loading) return <div className="py-12 text-center text-gray-500">Loading...</div>;
  if (!video) return <div className="py-12 text-center text-gray-500">Video not found.</div>;

  const categoryName = categories.find((c) => c.id === video.category_id)?.name ?? "";

  return (
    <div>
      <Link to="/" className="mb-4 inline-flex items-center text-sm text-blue-600 hover:text-blue-800">
        <svg className="mr-1 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Back to Library
      </Link>

      <div className="mt-4 grid gap-6 lg:grid-cols-2">
        {/* Player */}
        <div className="overflow-hidden rounded-lg bg-black">
          <ReactPlayer
            url={getVideoStreamUrl(videoId)}
            controls
            width="100%"
            height="auto"
            style={{ aspectRatio: "16/9" }}
          />
        </div>

        {/* Details */}
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          {editing ? (
            <div className="space-y-3">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Title</label>
                <input
                  type="text"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Description</label>
                <textarea
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  rows={3}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Category</label>
                <select
                  value={editCategoryId}
                  onChange={(e) => setEditCategoryId(Number(e.target.value))}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                >
                  {categories.map((cat) => (
                    <option key={cat.id} value={cat.id}>{cat.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Difficulty</label>
                <select
                  value={editDifficulty}
                  onChange={(e) => setEditDifficulty(e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                >
                  <option value="">Not specified</option>
                  <option value="beginner">Beginner</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="advanced">Advanced</option>
                </select>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handleSave}
                  className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
                >
                  Save
                </button>
                <button
                  onClick={() => setEditing(false)}
                  className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div>
              <h1 className="text-xl font-bold text-gray-900">{video.title}</h1>
              <div className="mt-2 flex flex-wrap gap-2 text-sm text-gray-600">
                {categoryName && (
                  <span className="rounded bg-blue-100 px-2 py-0.5 text-blue-800">{categoryName}</span>
                )}
                {video.difficulty && (
                  <span className="rounded bg-gray-100 px-2 py-0.5 capitalize">{video.difficulty}</span>
                )}
                {video.duration && (
                  <span>{Math.floor(video.duration / 60)}:{String(Math.floor(video.duration % 60)).padStart(2, "0")}</span>
                )}
              </div>
              {video.description && (
                <p className="mt-3 text-sm text-gray-600">{video.description}</p>
              )}
              {video.muscle_groups && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {JSON.parse(video.muscle_groups).map((g: string) => (
                    <span key={g} className="rounded bg-green-100 px-2 py-0.5 text-xs text-green-800">{g}</span>
                  ))}
                </div>
              )}
              <div className="mt-4 flex gap-2">
                <button
                  onClick={() => setEditing(true)}
                  className="rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Edit
                </button>
                <button
                  onClick={handleDelete}
                  className="rounded-md border border-red-300 px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50"
                >
                  Delete
                </button>
              </div>
            </div>
          )}
          {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
        </div>
      </div>
    </div>
  );
}
