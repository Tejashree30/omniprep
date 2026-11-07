export const API = process.env.NEXT_PUBLIC_API || "http://localhost:8000";
export async function post(path: string, body: any) {
  const r = await fetch(API + path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
  return r.json();
}
export async function get(path: string) { const r = await fetch(API + path); return r.json(); }
