import { useCallback, useEffect, useState } from "react";
import {
  getCategories,
  createCategory,
  updateCategory,
  deleteCategory,
} from "../api/client";
import type { Category } from "../types";

export default function CategoriesPage() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [newName, setNewName] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const loadCategories = useCallback(async () => {
    try {
      const data = await getCategories();
      setCategories(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCategories();
  }, [loadCategories]);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setError("");
    try {
      await createCategory(newName.trim());
      setNewName("");
      loadCategories();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create category");
    }
  };

  const handleRename = async (id: number) => {
    if (!editName.trim()) return;
    setError("");
    try {
      await updateCategory(id, editName.trim());
      setEditingId(null);
      loadCategories();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to rename category");
    }
  };

  const handleDelete = async (cat: Category) => {
    if (categories.length <= 1) {
      setError("Cannot delete the only category. Create another first.");
      return;
    }
    if (!confirm(`Delete category "${cat.name}"? Videos will need to be reassigned.`)) return;

    // Reassign to first other category
    const target = categories.find((c) => c.id !== cat.id);
    try {
      await deleteCategory(cat.id, target?.id);
      loadCategories();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete category");
    }
  };

  if (loading) return <div className="py-12 text-center text-gray-500">Loading...</div>;

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">Categories</h1>

      {/* Create new category */}
      <div className="mb-6 flex gap-2">
        <input
          type="text"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="New category name"
          onKeyDown={(e) => e.key === "Enter" && handleCreate()}
          className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
        <button
          onClick={handleCreate}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          Add
        </button>
      </div>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      {/* Category list */}
      {categories.length === 0 ? (
        <p className="py-8 text-center text-gray-500">No categories yet.</p>
      ) : (
        <div className="space-y-2">
          {categories.map((cat) => (
            <div
              key={cat.id}
              className="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-3"
            >
              {editingId === cat.id ? (
                <div className="flex flex-1 gap-2">
                  <input
                    type="text"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleRename(cat.id)}
                    className="flex-1 rounded-md border border-gray-300 px-3 py-1.5 text-sm"
                    autoFocus
                  />
                  <button
                    onClick={() => handleRename(cat.id)}
                    className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white"
                  >
                    Save
                  </button>
                  <button
                    onClick={() => setEditingId(null)}
                    className="rounded-md border border-gray-300 px-3 py-1.5 text-sm"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <>
                  <span className="font-medium text-gray-900">{cat.name}</span>
                  <div className="flex gap-2">
                    <button
                      onClick={() => {
                        setEditingId(cat.id);
                        setEditName(cat.name);
                      }}
                      className="text-sm text-blue-600 hover:text-blue-800"
                    >
                      Rename
                    </button>
                    <button
                      onClick={() => handleDelete(cat)}
                      className="text-sm text-red-600 hover:text-red-800"
                    >
                      Delete
                    </button>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
