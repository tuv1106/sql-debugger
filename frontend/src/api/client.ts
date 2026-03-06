const LOCAL_BASE_URL = import.meta.env.VITE_LOCAL_API_URL ?? 'http://localhost:8765';
const CLOUD_BASE_URL = import.meta.env.VITE_CLOUD_API_URL ?? 'http://localhost:8000';

async function request<T>(baseUrl: string, path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  return response.json() as T;
}

export const localApi = {
  get: <T>(path: string) => request<T>(LOCAL_BASE_URL, path),
  post: <T>(path: string, body: unknown) =>
    request<T>(LOCAL_BASE_URL, path, { method: 'POST', body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(LOCAL_BASE_URL, path, { method: 'PUT', body: JSON.stringify(body) }),
  delete: <T>(path: string) =>
    request<T>(LOCAL_BASE_URL, path, { method: 'DELETE' }),
};

export const cloudApi = {
  get: <T>(path: string) => request<T>(CLOUD_BASE_URL, path),
  post: <T>(path: string, body: unknown) =>
    request<T>(CLOUD_BASE_URL, path, { method: 'POST', body: JSON.stringify(body) }),
};
