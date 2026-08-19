export const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API}/api${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
    cache: "no-store",
  });
  if (!response.ok)
    throw new Error((await response.json()).detail || "Request failed");
  return response.json();
}
