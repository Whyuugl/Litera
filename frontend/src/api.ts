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
  digital: { id: string; file_type: "PDF" | "EPUB"; access_level: "PUBLIC" | "REGISTERED" | "MEMBER"; processing_status: ProcessingStatus; available: boolean }[];
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
export type ProcessingStatus = "UPLOADED" | "PROCESSING" | "READY" | "FAILED";
export type DigitalFile = { id: string; edition_id: string; file_url: string; original_filename: string | null; mime_type: string | null; file_type: "PDF" | "EPUB"; file_size: number | null; access_level: "PUBLIC" | "REGISTERED" | "MEMBER"; allow_download: boolean; processing_status: ProcessingStatus; processing_error: string | null; processed_at: string | null; uploaded_at: string };
export type BookCopy = { id: string; edition_id: string; barcode: string; shelf_location: string | null; status: "AVAILABLE" | "BORROWED" | "RESERVED" | "LOST" | "DAMAGED" | "MAINTENANCE"; condition: string | null; acquired_at: string | null };
export type AdminEdition = Omit<Edition, "digital" | "physical"> & { book_id: string; digital_files: DigitalFile[]; physical_copies: BookCopy[] };
export type AdminBookDetail = AdminBook & { editions: AdminEdition[] };
export type AdminMembership = Membership & { user: { id: string; name: string; email: string } };
export type MembershipPage = { items: AdminMembership[]; total: number; page: number; page_size: number };
export type ReservationStatus = "WAITING" | "READY" | "FULFILLED" | "CANCELLED" | "EXPIRED";
export type LoanStatus = "BORROWED" | "RETURNED" | "OVERDUE" | "LOST";
export type CirculationBook = { id: string; title: string; slug: string; cover_url: string | null };
export type CirculationEdition = { id: string; isbn: string | null; publisher: string | null; book: CirculationBook };
export type CirculationCopy = { id: string; barcode: string; shelf_location: string | null; status: BookCopy["status"]; edition: CirculationEdition };
export type Reservation = {
  id: string;
  user_id: string;
  edition_id: string;
  book_copy_id: string | null;
  status: ReservationStatus;
  queue_position: number;
  reserved_at: string;
  expires_at: string | null;
  fulfilled_at: string | null;
  edition: CirculationEdition;
  book_copy: CirculationCopy | null;
};
export type AdminReservation = Reservation & { user: { id: string; name: string; email: string } };
export type ReservationPage = Page<AdminReservation>;
export type Loan = {
  id: string;
  user_id: string;
  book_copy_id: string;
  borrowed_at: string;
  due_at: string;
  returned_at: string | null;
  status: LoanStatus;
  renewal_count: number;
  processed_by: string | null;
  book_copy: CirculationCopy;
};
export type AdminLoan = Loan & { user: { id: string; name: string; email: string } };
export type LoanPage = Page<AdminLoan>;
export type Chapter = { id: string; edition_id: string; chapter_number: number; title: string; page_start: number; page_end: number };
export type Reader = { edition_id: string; digital_file_id: string; access_level: Edition["digital"][number]["access_level"]; processing_status: ProcessingStatus; page_count: number; book: { id: string; title: string; slug: string; cover_url: string | null }; chapters: Chapter[]; learning_available: boolean; summary_chapter_ids: string[] };
export type ReaderPage = { page_number: number; content: string };
export type ReadingProgress = { id: string; user_id: string; edition_id: string; chapter_id: string | null; progress_percentage: number; current_page: number; position_data: Record<string, unknown> | null; started_at: string; last_read_at: string; completed_at: string | null };
export type ReadingProgressItem = ReadingProgress & { book: Reader["book"]; chapter: Chapter | null };
export type ReaderBookmark = { id: string; edition_id: string; chapter_id: string | null; page_number: number; position_data: Record<string, unknown> | null; note: string | null; created_at: string };
export type QuizDifficulty = "EASY" | "MEDIUM" | "HARD";
export type QuizOption = { id: string; option_text: string; order_number: number };
export type QuizQuestion = { id: string; question: string; question_type: "MULTIPLE_CHOICE"; order_number: number; options: QuizOption[] };
export type StudentQuiz = { id: string; chapter_id: string; edition_id: string; title: string; difficulty: QuizDifficulty; questions: QuizQuestion[] };
export type QuizSummary = { id: string; chapter_id: string; title: string; difficulty: QuizDifficulty; question_count: number };
export type AttemptSummary = { id: string; quiz_id: string; score: number | null; correct_answers: number; total_questions: number; started_at: string; completed_at: string | null };
export type AttemptStarted = { id: string; quiz: StudentQuiz; started_at: string; answers: Record<string, string> };
export type AnswerReview = { question_id: string; question: string; selected_option_id: string; selected_answer: string; correct_option_id: string; correct_answer: string; is_correct: boolean; explanation: string | null };
export type AttemptResult = AttemptSummary & { quiz: StudentQuiz; review: AnswerReview[] };
export type LearningChapter = Chapter & { is_read: boolean; quizzes: QuizSummary[]; best_score: number | null; summary_available: boolean };
export type LearningProgress = { edition_id: string; book: Reader["book"]; chapters_total: number; chapters_read: number; quizzes_available: number; quizzes_completed: number; average_score: number | null; book_summary_available: boolean; chapters: LearningChapter[] };
export type SummaryStatus = "PENDING" | "READY" | "FAILED";
export type SummaryResponse = { id: string; edition_id: string; chapter_id: string | null; summary_type: "BOOK" | "CHAPTER"; spoiler_mode: "NONE" | "SPOILER_FREE"; content: string | null; source_content_hash: string; provider: string; model: string; status: SummaryStatus; error_message: string | null; generated_at: string | null; created_at: string; updated_at: string; is_stale: boolean };
export type AdminQuizOption = QuizOption & { is_correct: boolean };
export type AdminQuizQuestion = Omit<QuizQuestion, "options"> & { explanation: string | null; options: AdminQuizOption[] };
export type AdminQuiz = { id: string; chapter_id: string; title: string; difficulty: QuizDifficulty; generated_by: "ADMIN" | "AI"; ai_model: string | null; is_published: boolean; created_by: string | null; created_at: string; updated_at: string; questions: AdminQuizQuestion[]; attempt_count: number };

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
  if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
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
