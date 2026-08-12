export async function postJSON<T>(url: string, body: unknown): Promise<T> {
  if (!url.startsWith('http')) {
    throw new Error(
      'Missing or invalid API URL. Set EXPO_PUBLIC_API_BASE_URL in mobile/.env (see mobile/.env.example).'
    );
  }
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data?.error ?? `Request failed (${res.status})`);
  }
  return data as T;
}
