export const apiBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export type User = {
  id: string;
  name: string;
  email: string;
  role: "USER" | "ADMIN";
  avatar_url: string | null;
  is_active: boolean;
};

export type Category = { id: string; name: string; slug: string; description?: string | null };
export type Author = { id: string; name: string };
export type BookSummary = {
  id: string;
  title: string;
  slug: string;
  description: string | null;
  cover_url: string | null;
  language: string;
  book_type: "FICTION" | "NON_FICTION" | "EDUCATIONAL" | "REFERENCE";
  category: Category;
  authors: Author[];
};
export type Edition = {
  id: string;
  isbn: string | null;
  publisher: string | null;
  edition_number: string | null;
  publication_year: number | null;
  page_count: number | null;
  language: string | null;
  digital: { file_type: "PDF" | "EPUB"; access_level: "PUBLIC" | "REGISTERED" | "MEMBER"; available: boolean }[];
  physical: { total_copies: number; available_copies: number };
};
export type BookDetail = BookSummary & { editions: Edition[] };
export type Page<T> = { items: T[]; page: number; page_size: number; total: number; total_pages: number };
export type MembershipStatus = "PENDING" | "ACTIVE" | "REJECTED" | "EXPIRED" | "SUSPENDED";
export type Membership = {
  id: string;
  status: MembershipStatus;
  member_number: string | null;
  applied_at: string;
  approved_at: string | null;
  expires_at: string | null;
  rejection_reason: string | null;
  suspension_reason: string | null;
};
export type AdminBook = BookSummary & { status: "DRAFT" | "PUBLISHED" | "ARCHIVED" };
export type DigitalFile = { id: string; edition_id: string; file_url: string; file_type: "PDF" | "EPUB"; file_size: number | null; access_level: "PUBLIC" | "REGISTERED" | "MEMBER"; uploaded_at: string };
export type BookCopy = { id: string; edition_id: string; barcode: string; shelf_location: string | null; status: "AVAILABLE" | "BORROWED" | "RESERVED" | "LOST" | "DAMAGED" | "MAINTENANCE"; condition: string | null; acquired_at: string | null };
export type AdminEdition = Omit<Edition, "digital" | "physical"> & { book_id: string; digital_files: DigitalFile[]; physical_copies: BookCopy[] };
export type AdminBookDetail = AdminBook & { editions: AdminEdition[] };
export type AdminMembership = Membership & { user: { id: string; name: string; email: string } };
export type MembershipPage = { items: AdminMembership[]; total: number; page: number; page_size: number };

export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}

function errorMessage(status: number, detail?: unknown) {
  if (typeof detail === "string" && detail && status < 500) return detail;
  if (Array.isArray(detail) && typeof detail[0]?.msg === "string") return detail[0].msg.replace(/^Value error, /, "");
  if (status === 401) return "Please sign in to continue.";
  if (status === 403) return "You do not have access to this action.";
  if (status === 404) return "We could not find what you were looking for.";
  if (status >= 500) return "Litera is having trouble connecting. Please try again shortly.";
  return "Something went wrong. Please try again.";
}

async function refreshAccessToken() {
  const refreshToken = sessionStorage.getItem("litera_refresh");
  if (!refreshToken) return null;
  let response: Response;
  try {
    response = await fetch(`${apiBase}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  } catch { return null; }
  if (!response.ok) return null;
  const tokens = await response.json();
  sessionStorage.setItem("litera_access", tokens.access_token);
  sessionStorage.setItem("litera_refresh", tokens.refresh_token);
  return tokens.access_token as string;
}

export async function api<T>(path: string, options: RequestInit = {}, retry = true): Promise<T> {
  const token = sessionStorage.getItem("litera_access");
  const headers = new Headers(options.headers);
  if (options.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let response: Response;
  try { response = await fetch(`${apiBase}${path}`, { ...options, headers }); }
  catch { throw new ApiError("Unable to reach Litera. Check your connection and try again.", 0); }

  if (response.status === 401 && token && retry) {
    const refreshed = await refreshAccessToken();
    if (refreshed) return api<T>(path, options, false);
    clearSession();
  }

  const body = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(errorMessage(response.status, body?.detail), response.status);
  return body as T;
}

export function saveSession(tokens: { access_token: string; refresh_token: string }) {
  sessionStorage.setItem("litera_access", tokens.access_token);
  sessionStorage.setItem("litera_refresh", tokens.refresh_token);
}

export function clearSession() {
  sessionStorage.removeItem("litera_access");
  sessionStorage.removeItem("litera_refresh");
}

export function hasSession() { return Boolean(sessionStorage.getItem("litera_access")); }

export function formatEnum(value: string) {
  return value.toLowerCase().replace(/_/g, " ").replace(/\b\w/g, (letter: string) => letter.toUpperCase());
}

export function formatDate(value: string | null) {
  return value ? new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(new Date(value)) : "";
}
