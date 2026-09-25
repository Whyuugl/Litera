<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { ArrowRight, ArrowUpRight, BookOpen, Bookmark, ChevronRight, Compass, Eye, EyeOff, Focus, History, LibraryBig, LoaderCircle, LogOut, Menu, NotebookPen, Search, Sparkles, X } from "@lucide/vue";
import { api, clearSession, hasSession, saveSession, type BookSummary, type Page, type User } from "./api";
import BookCard from "./components/BookCard.vue";
import AdminShell from "./components/AdminShell.vue";
import ToastHost from "./components/ToastHost.vue";
import ContinueReading from "./components/ContinueReading.vue";
import BookDetailPage from "./pages/BookDetailPage.vue";
import ExplorePage from "./pages/ExplorePage.vue";
import MembershipPage from "./pages/MembershipPage.vue";
import LearningPage from "./pages/LearningPage.vue";
import QuizPage from "./pages/QuizPage.vue";
import LibraryPage from "./pages/LibraryPage.vue";
import ProfilePage from "./pages/ProfilePage.vue";
import ReaderPage from "./pages/ReaderPage.vue";
import AdminBookDetail from "./pages/admin/AdminBookDetail.vue";
import AdminBooks from "./pages/admin/AdminBooks.vue";
import AdminMemberDetail from "./pages/admin/AdminMemberDetail.vue";
import AdminMembers from "./pages/admin/AdminMembers.vue";
import AdminOverview from "./pages/admin/AdminOverview.vue";
import AdminTaxonomy from "./pages/admin/AdminTaxonomy.vue";
import AdminCirculation from "./pages/admin/AdminCirculation.vue";
import AdminLearning from "./pages/admin/AdminLearning.vue";

type View = "landing" | "login" | "register" | "home" | "explore" | "book" | "reader" | "learn" | "quiz" | "library" | "membership" | "profile" | "admin" | "not-found";

const currentPath = ref(location.pathname);
const mobileOpen = ref(false);
const query = ref("");
const showPassword = ref(false);
const loading = ref(false);
const authReady = ref(false);
const authError = ref("");
const user = ref<User | null>(null);
const loginForm = ref({ email: "", password: "" });
const registerForm = ref({ name: "", email: "", password: "" });
const catalogBooks = ref<BookSummary[]>([]);
const catalogLoading = ref(true);

const view = computed<View>(() => {
  if (currentPath.value === "/") return "landing";
  if (currentPath.value === "/login") return "login";
  if (currentPath.value === "/register") return "register";
  if (currentPath.value === "/home") return "home";
  if (currentPath.value === "/explore") return "explore";
  if (currentPath.value === "/membership") return "membership";
  if (currentPath.value === "/library") return "library";
  if (currentPath.value === "/profile") return "profile";
  if (currentPath.value === "/admin" || currentPath.value.startsWith("/admin/")) return "admin";
  if (/^\/books\/[^/]+$/.test(currentPath.value)) return "book";
  if (/^\/read\/[^/]+$/.test(currentPath.value)) return "reader";
  if (/^\/learn\/[^/]+$/.test(currentPath.value)) return "learn";
  if (/^\/quiz\/[^/]+$/.test(currentPath.value)) return "quiz";
  return "not-found";
});
const bookSlug = computed(() => decodeURIComponent(currentPath.value.split("/")[2] || ""));
const readerEditionId = computed(() => decodeURIComponent(currentPath.value.split("/")[2] || ""));
const catalogCovers = computed(() => catalogBooks.value.filter((book) => book.cover_url));
const signInPath = computed(() => currentPath.value.startsWith("/books/") ? `/login?redirect=${encodeURIComponent(currentPath.value)}` : "/login");
const protectedPaths = new Set(["/home", "/library", "/membership", "/profile"]);

function navigate(path: string, replace = false) {
  const target = new URL(path, location.origin);
  if (replace) history.replaceState({}, "", target);
  else history.pushState({}, "", target);
  currentPath.value = target.pathname;
  mobileOpen.value = false;
  authError.value = "";
  window.scrollTo({ top: 0, behavior: "smooth" });
  if (authReady.value) requestAnimationFrame(enforceAuthentication);
}

function discover(term?: string) {
  if (term) query.value = term;
  navigate(`/explore${query.value.trim() ? `?search=${encodeURIComponent(query.value.trim())}` : ""}`);
}

function goToSection(id: string) {
  if (view.value !== "landing") navigate("/");
  requestAnimationFrame(() => document.querySelector(`#${id}`)?.scrollIntoView({ behavior: "smooth" }));
}

function alternateAuthPath(path: "/login" | "/register") {
  const intended = new URLSearchParams(location.search).get("redirect");
  return intended ? `${path}?redirect=${encodeURIComponent(intended)}` : path;
}

async function loadUser() { user.value = await api<User>("/api/v1/users/me"); }

async function signIn(email: string, password: string) {
  const tokens = await api<{ access_token: string; refresh_token: string }>("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
  saveSession(tokens);
  await loadUser();
  const intended = new URLSearchParams(location.search).get("redirect");
  navigate(intended?.startsWith("/") && !intended.startsWith("//") ? intended : "/home");
}

async function submitLogin() {
  loading.value = true;
  authError.value = "";
  try { await signIn(loginForm.value.email, loginForm.value.password); }
  catch (error) { authError.value = error instanceof Error ? error.message : "Unable to sign in."; }
  finally { loading.value = false; }
}

async function submitRegister() {
  loading.value = true;
  authError.value = "";
  try {
    await api("/api/v1/auth/register", { method: "POST", body: JSON.stringify(registerForm.value) });
    await signIn(registerForm.value.email, registerForm.value.password);
  } catch (error) { authError.value = error instanceof Error ? error.message : "Unable to create your account."; }
  finally { loading.value = false; }
}

async function logout() {
  const refreshToken = sessionStorage.getItem("litera_refresh");
  try {
    if (refreshToken) await api("/api/v1/auth/logout", { method: "POST", body: JSON.stringify({ refresh_token: refreshToken }) });
  } finally {
    clearSession();
    user.value = null;
    navigate("/");
  }
}

function enforceAuthentication() {
  const adminRoute = currentPath.value === "/admin" || currentPath.value.startsWith("/admin/");
  if (authReady.value && (protectedPaths.has(currentPath.value) || adminRoute) && !user.value) {
    navigate(`/login?redirect=${encodeURIComponent(`${currentPath.value}${location.search}`)}`, true);
  } else if (authReady.value && adminRoute && user.value?.role !== "ADMIN") {
    navigate("/home", true);
  }
}

function handlePopState() { currentPath.value = location.pathname; enforceAuthentication(); }

onMounted(async () => {
  const legacyHash = location.hash.slice(1);
  if (["login", "register", "home"].includes(legacyHash)) navigate(`/${legacyHash}`, true);
  addEventListener("popstate", handlePopState);
  const catalogRequest = api<Page<BookSummary>>("/api/v1/books?page=1&page_size=4").then((page) => { catalogBooks.value = page.items; }).catch(() => {}).finally(() => { catalogLoading.value = false; });
  if (hasSession()) {
    try { await loadUser(); } catch { clearSession(); user.value = null; }
  }
  authReady.value = true;
  enforceAuthentication();
  await catalogRequest;
});
onBeforeUnmount(() => removeEventListener("popstate", handlePopState));
</script>

<template>
  <div class="site-frame">
    <header v-if="view !== 'admin' && view !== 'reader' && view !== 'quiz'" class="site-header" :class="{ compact: view === 'login' || view === 'register' }">
      <button class="brand" type="button" @click="navigate(user ? '/home' : '/')">Litera<span>.</span></button>
      <template v-if="view !== 'login' && view !== 'register'">
        <nav class="desktop-nav" aria-label="Main navigation">
          <button v-if="user" type="button" :class="{ active: view === 'home' }" @click="navigate('/home')">Home</button>
          <button type="button" :class="{ active: view === 'explore' || view === 'book' }" @click="navigate('/explore')">Explore</button>
          <button v-if="user" type="button" :class="{ active: view === 'library' }" @click="navigate('/library')">My Library</button>
          <button v-if="user" type="button" :class="{ active: view === 'membership' }" @click="navigate('/membership')">Membership</button>
          <button v-else type="button" @click="goToSection('about')">About</button>
        </nav>
        <div class="nav-actions">
          <template v-if="user">
            <button v-if="user.role === 'ADMIN'" class="admin-badge" type="button" @click="navigate('/admin')">Admin</button>
            <button class="text-button" type="button" @click="navigate('/profile')">{{ user.name }}</button>
            <button class="icon-button" type="button" title="Sign out" aria-label="Sign out" @click="logout"><LogOut :size="18" /></button>
          </template>
          <template v-else>
            <button class="text-button desktop-only" type="button" @click="navigate(signInPath)">Sign in</button>
            <button class="primary-button desktop-only" type="button" @click="navigate('/register')">Get started <ArrowUpRight :size="16" /></button>
          </template>
          <button class="icon-button mobile-menu-button" type="button" :aria-expanded="mobileOpen" aria-label="Toggle navigation" @click="mobileOpen = !mobileOpen"><X v-if="mobileOpen" :size="21" /><Menu v-else :size="21" /></button>
        </div>
        <nav v-if="mobileOpen" class="mobile-nav" aria-label="Mobile navigation">
          <button v-if="user" type="button" @click="navigate('/home')">Home</button><button type="button" @click="navigate('/explore')">Explore</button><button v-if="user" type="button" @click="navigate('/library')">My Library</button><button v-if="user" type="button" @click="navigate('/membership')">Membership</button><button v-if="user" type="button" @click="navigate('/profile')">Profile</button>
          <button v-if="!user" type="button" @click="navigate(signInPath)">Sign in</button><button v-if="!user" type="button" @click="navigate('/register')">Get started</button>
        </nav>
      </template>
      <button v-else class="quiet-link" type="button" @click="navigate('/')">Back to discover</button>
    </header>

    <ReaderPage v-if="view === 'reader'" :edition-id="readerEditionId" @navigate="navigate" />

    <AdminShell v-else-if="view === 'admin' && user?.role === 'ADMIN'" :current="currentPath" :user="user" @navigate="navigate" @logout="logout">
      <AdminOverview v-if="currentPath === '/admin'" :user="user" @navigate="navigate" />
      <AdminBooks v-else-if="currentPath === '/admin/books'" @navigate="navigate" />
      <AdminBookDetail v-else-if="/^\/admin\/books\/[^/]+$/.test(currentPath)" :id="decodeURIComponent(currentPath.split('/')[3])" @navigate="navigate" />
      <AdminLearning v-else-if="/^\/admin\/books\/[^/]+\/learning\/[^/]+$/.test(currentPath)" :book-id="decodeURIComponent(currentPath.split('/')[3])" :edition-id="decodeURIComponent(currentPath.split('/')[5])" @navigate="navigate" />
      <AdminTaxonomy v-else-if="currentPath === '/admin/categories'" kind="categories" />
      <AdminTaxonomy v-else-if="currentPath === '/admin/authors'" kind="authors" />
      <AdminMembers v-else-if="currentPath === '/admin/members'" @navigate="navigate" />
      <AdminMemberDetail v-else-if="/^\/admin\/members\/[^/]+$/.test(currentPath)" :id="decodeURIComponent(currentPath.split('/')[3])" @navigate="navigate" />
      <AdminCirculation v-else-if="['/admin/circulation', '/admin/loans', '/admin/reservations'].includes(currentPath)" />
      <main v-else class="not-found"><p class="eyebrow">Admin page not found</p><h1>This workspace<br />has no such page.</h1><button type="button" @click="navigate('/admin')">Return to overview <ArrowRight :size="17" /></button></main>
    </AdminShell>
    <main v-else-if="view === 'admin'" class="route-loading" aria-label="Checking admin access"><LoaderCircle class="spin" :size="24" /></main>

    <main v-else-if="view === 'landing'" class="landing-view">
      <section class="discovery-hero">
        <div class="hero-copy">
          <p class="eyebrow">Your space to read and grow</p>
          <h1>Read deeper.<br />Learn beyond<br />the page.</h1>
          <p class="hero-intro">Explore a growing e-book collection and read directly in your browser, with progress, bookmarks, and learning activities in one place.</p>
          <form class="discovery-search" role="search" @submit.prevent="discover()">
            <label class="sr-only" for="discovery">Search books, authors, or subjects</label><Search :size="20" aria-hidden="true" />
            <input id="discovery" v-model="query" type="search" placeholder="Search a title, author, or topic" />
            <button type="submit" aria-label="Search"><ArrowRight :size="20" /></button>
          </form>
        </div>
        <div v-if="catalogCovers.length" class="hero-library" aria-label="Featured books">
          <img v-for="book in catalogCovers" :key="book.id" :src="book.cover_url!" :alt="`${book.title} cover`" />
        </div>
      </section>

      <section id="about" class="about-section">
        <p class="eyebrow">What is Litera?</p>
        <div class="about-copy"><h2>A digital library built for reading, not just borrowing.</h2><div><p>Litera is a collection of e-books you can open and read directly on the web. Your page progress and bookmarks stay connected to your account.</p><p>Printed borrowing remains an additional option, while Learning Mode builds quizzes and review around the digital books you read.</p></div></div>
        <div class="about-principles"><span>Discover with purpose</span><span>Understand your access</span><span>Grow through ideas</span></div>
      </section>

      <section class="category-strip" aria-label="Book categories">
        <div><span>Explore by reading path</span><button type="button" @click="navigate('/explore')">All books</button><button type="button" @click="navigate('/explore?book_type=FICTION')">Fiction</button><button type="button" @click="navigate('/explore?book_type=NON_FICTION')">Non-fiction</button><button type="button" @click="navigate('/explore?book_type=EDUCATIONAL')">Educational</button><button type="button" @click="navigate('/explore?book_type=REFERENCE')">Reference</button></div>
      </section>

      <section id="books" class="book-section">
        <div class="section-heading"><div><p class="eyebrow">From the Litera catalog</p><h2>Start with a good book.</h2><p class="section-description">Published titles from the real collection, ready to explore in more detail.</p></div><button class="line-button" type="button" @click="navigate('/explore')">Explore all <ArrowRight :size="15" /></button></div>
        <div v-if="catalogLoading" class="catalog-loading"><span v-for="index in 4" :key="index"></span></div>
        <div v-else-if="catalogBooks.length" class="book-grid"><BookCard v-for="(book, index) in catalogBooks" :key="book.id" :book="book" :index="index" @open="navigate(`/books/${$event}`)" /></div>
        <div v-else class="empty-search"><p>No published titles yet.</p><button class="line-button" type="button" @click="navigate('/explore')">Open the catalog <ArrowRight :size="15" /></button></div>
      </section>

      <section id="learning" class="learning-section">
        <div class="learning-heading"><p class="eyebrow">More than a reading list</p><h2>Turn every page<br />into progress.</h2><p>Litera gives your curiosity a simple path, from finding the right book to remembering what mattered.</p></div>
        <div class="learning-steps">
          <article><span>01</span><Compass :size="26" /><h3>Find your direction</h3><p>Explore by topic, mood, or the question you want to answer next.</p></article>
          <article><span>02</span><Bookmark :size="26" /><h3>Read online</h3><p>Open an available e-book in the browser and return to the page where you stopped.</p></article>
          <article><span>03</span><NotebookPen :size="26" /><h3>Practice what you read</h3><p>Use chapter quizzes when Learning Mode is available, without interrupting the reading experience.</p></article>
        </div>
      </section>

      <section class="why-section">
        <div class="why-heading"><p class="eyebrow">Why Litera?</p><h2>Reading should feel<br />simple and meaningful.</h2><p>Most platforms compete for your attention. Litera is designed to help you direct it.</p></div>
        <div class="benefit-grid">
          <article><Compass :size="25" /><h3>Purposeful discovery</h3><p>Start from an interest, a question, or the kind of perspective you want to find.</p></article>
          <article><LibraryBig :size="25" /><h3>One clear catalog</h3><p>Explore published books and their editions without ecommerce clutter.</p></article>
          <article><History :size="25" /><h3>Clear access guidance</h3><p>Know whether an edition is public, registered-only, or for active members.</p></article>
          <article><Focus :size="25" /><h3>Made for focus</h3><p>A clear experience with less noise, helping the book remain the most important thing.</p></article>
        </div>
      </section>

      <section class="path-section">
        <div class="path-heading"><p class="eyebrow">Choose your path</p><h2>What will you<br />learn next?</h2></div>
        <div class="path-list"><button type="button" @click="navigate('/explore?book_type=FICTION')"><span>See life through another story</span><small>Fiction</small><ArrowUpRight :size="20" /></button><button type="button" @click="navigate('/explore?book_type=NON_FICTION')"><span>Understand the world around you</span><small>Non-fiction</small><ArrowUpRight :size="20" /></button><button type="button" @click="navigate('/explore?book_type=EDUCATIONAL')"><span>Learn something you can use</span><small>Educational</small><ArrowUpRight :size="20" /></button></div>
      </section>

      <section class="audience-section">
        <div class="audience-heading"><p class="eyebrow">Made for curious people</p><h2>There is more than one<br />way to be a reader.</h2></div>
        <div class="audience-list">
          <article><span>For students</span><h3>Find context beyond the classroom.</h3><p>Explore stories and ideas that make a subject easier to understand and more interesting to follow.</p></article>
          <article><span>For growing professionals</span><h3>Keep learning outside of work.</h3><p>Build a thoughtful reading habit around the skills, questions, and perspectives that matter to you.</p></article>
          <article><span>For lifelong readers</span><h3>Never run out of directions.</h3><p>Move between imagination and insight while keeping every discovery close enough to revisit.</p></article>
        </div>
      </section>

      <section class="faq-section">
        <div><p class="eyebrow">Questions, answered</p><h2>Before you open<br />the first page.</h2></div>
        <div class="faq-list">
          <details><summary>What can I do with Litera?<ChevronRight :size="18" /></summary><p>You can explore e-books, read available PDFs online, save progress and bookmarks, practice chapter quizzes, and optionally reserve printed copies.</p></details>
          <details><summary>Is Litera only for students?<ChevronRight :size="18" /></summary><p>No. Litera is for anyone who reads to understand, imagine, improve a skill, or simply spend time with a good story.</p></details>
          <details><summary>Do I need an account to explore?<ChevronRight :size="18" /></summary><p>You can browse the public catalog without an account. An account gives you a personal space for your reading journey.</p></details>
          <details><summary>What kinds of books will I find?<ChevronRight :size="18" /></summary><p>The catalog can hold fiction, classics, fantasy, and learning-focused collections, with more subjects added as Litera develops.</p></details>
        </div>
      </section>

      <section id="membership" class="membership-section"><div><p class="eyebrow">Your next chapter starts here</p><h2>A quieter place<br />to keep growing.</h2><p>Create your account, explore the catalog, and apply for access to more ways of reading.</p><button type="button" class="membership-button" @click="navigate(user ? '/membership' : '/register')">{{ user ? 'View membership' : 'Start learning' }} <ArrowRight :size="18" /></button></div><Sparkles :size="120" stroke-width="1" aria-hidden="true" /></section>
    </main>

    <ExplorePage v-else-if="view === 'explore'" @navigate="navigate" />
    <BookDetailPage v-else-if="view === 'book'" :slug="bookSlug" :user="user" @navigate="navigate" />
    <LearningPage v-else-if="view === 'learn'" :edition-id="readerEditionId" @navigate="navigate" />
    <QuizPage v-else-if="view === 'quiz'" :quiz-id="readerEditionId" @navigate="navigate" />
    <MembershipPage v-else-if="view === 'membership' && user" :user="user" />
    <LibraryPage v-else-if="view === 'library' && user" @navigate="navigate" />
    <ProfilePage v-else-if="view === 'profile' && user" :user="user" />

    <main v-else-if="view === 'login' || view === 'register'" class="auth-view">
      <div class="auth-lines" aria-hidden="true"><span></span><span></span><span></span></div>
      <section class="auth-panel">
        <p class="eyebrow">{{ view === 'login' ? 'Welcome back' : 'Join Litera' }}</p><h1>{{ view === 'login' ? 'Continue exploring.' : 'Make room for curiosity.' }}</h1>
        <p class="auth-intro">{{ view === 'login' ? 'Sign in to access your account and membership.' : 'One account for catalog access, membership, and the learning experiences ahead.' }}</p>
        <form v-if="view === 'login'" class="auth-form" @submit.prevent="submitLogin">
          <label>Email address<input v-model="loginForm.email" type="email" autocomplete="email" required placeholder="you@example.com" /></label>
          <label>Password<span class="password-field"><input v-model="loginForm.password" :type="showPassword ? 'text' : 'password'" autocomplete="current-password" required minlength="8" placeholder="Your password" /><button type="button" :aria-label="showPassword ? 'Hide password' : 'Show password'" @click="showPassword = !showPassword"><EyeOff v-if="showPassword" :size="18" /><Eye v-else :size="18" /></button></span></label>
          <p v-if="authError" class="form-error" role="alert">{{ authError }}</p><button class="submit-button" type="submit" :disabled="loading"><LoaderCircle v-if="loading" class="spin" :size="18" />{{ loading ? 'Signing in' : 'Sign in' }}<ArrowRight v-if="!loading" :size="18" /></button>
        </form>
        <form v-else class="auth-form" @submit.prevent="submitRegister">
          <label>Your name<input v-model="registerForm.name" type="text" autocomplete="name" required placeholder="How should we call you?" /></label><label>Email address<input v-model="registerForm.email" type="email" autocomplete="email" required placeholder="you@example.com" /></label>
          <label>Password<span class="password-field"><input v-model="registerForm.password" :type="showPassword ? 'text' : 'password'" autocomplete="new-password" required minlength="8" placeholder="At least 8 characters" /><button type="button" :aria-label="showPassword ? 'Hide password' : 'Show password'" @click="showPassword = !showPassword"><EyeOff v-if="showPassword" :size="18" /><Eye v-else :size="18" /></button></span></label>
          <p v-if="authError" class="form-error" role="alert">{{ authError }}</p><button class="submit-button" type="submit" :disabled="loading"><LoaderCircle v-if="loading" class="spin" :size="18" />{{ loading ? 'Creating account' : 'Create account' }}<ArrowRight v-if="!loading" :size="18" /></button>
        </form>
        <p class="auth-switch">{{ view === 'login' ? 'New to Litera?' : 'Already have a shelf?' }} <button type="button" @click="navigate(alternateAuthPath(view === 'login' ? '/register' : '/login'))">{{ view === 'login' ? 'Create an account' : 'Sign in' }}</button></p>
      </section><p class="auth-footnote"><BookOpen :size="16" /> Read slowly. Learn deeply.</p>
    </main>

    <main v-else-if="view === 'home' && user" class="home-view">
      <section class="home-intro"><p class="eyebrow">Your reading space</p><h1>Good {{ new Date().getHours() < 12 ? 'morning' : new Date().getHours() < 18 ? 'afternoon' : 'evening' }},<br />{{ user.name }}.</h1><p>What's on your mind today?</p><form class="home-search" @submit.prevent="discover()"><Search :size="20" /><input v-model="query" type="search" placeholder="Search a title, author, or idea..." /><button type="submit" aria-label="Search"><ArrowUpRight :size="21" /></button></form></section>
      <ContinueReading @navigate="navigate" />
      <section class="empty-shelf"><div class="empty-number">01</div><div><p class="eyebrow">A place to begin</p><h2>Your next e-book<br />is ready to open.</h2><p>Explore the digital collection, choose a title, and start reading directly in Litera.</p><button class="line-button" type="button" @click="navigate('/explore')">Browse e-books <ArrowRight :size="16" /></button></div></section>
      <section class="home-books"><div class="section-heading"><div><p class="eyebrow">Recently published</p><h2>Open a new direction.</h2></div><button class="line-button" type="button" @click="navigate('/explore')">View all <ChevronRight :size="16" /></button></div><div v-if="catalogBooks.length" class="book-grid compact-grid"><BookCard v-for="(book, index) in catalogBooks.slice(0, 3)" :key="book.id" :book="book" :index="index" @open="navigate(`/books/${$event}`)" /></div><div v-else class="empty-search"><p>No published books are available yet.</p></div></section>
    </main>

    <main v-else-if="!authReady" class="route-loading" aria-label="Loading account"><LoaderCircle class="spin" :size="24" /></main>
    <main v-else class="not-found"><p class="eyebrow">Page not found</p><h1>This page has<br />lost its place.</h1><button type="button" @click="navigate('/')">Return to Litera <ArrowRight :size="17" /></button></main>

    <footer v-if="view === 'landing' || view === 'home'" class="site-footer"><button class="brand" type="button" @click="navigate('/')">Litera<span>.</span></button><p>A calmer place to read, think, and return.</p><span>&copy; {{ new Date().getFullYear() }}</span></footer>
    <ToastHost />
  </div>
</template>
