<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ArrowRight, ArrowUpRight, BookOpen, Bookmark, ChevronRight, Compass, Eye, EyeOff, Focus, History, LibraryBig, LoaderCircle, LogOut, Menu, NotebookPen, Search, Sparkles, X } from "@lucide/vue";

type View = "landing" | "login" | "register" | "home";
type User = { id: string; name: string; email: string; role: "USER" | "ADMIN" };
type Book = { id: string; title: string; author: string; category: string; year: string; cover: string; tone: string };

const apiBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const view = ref<View>("landing");
const mobileOpen = ref(false);
const query = ref("");
const showPassword = ref(false);
const loading = ref(false);
const authError = ref("");
const user = ref<User | null>(null);
const loginForm = ref({ email: "", password: "" });
const registerForm = ref({ name: "", email: "", password: "" });
const books = ref<Book[]>([
  { id: "hujan", title: "Hujan", author: "Tere Liye", category: "Fiction", year: "2016", cover: "/covers/hujan.jpg", tone: "cool" },
  { id: "gatsby", title: "The Great Gatsby", author: "F. Scott Fitzgerald", category: "Classic", year: "1925", cover: "/covers/gatsby.jpg", tone: "ink" },
  { id: "bumi", title: "Bumi", author: "Tere Liye", category: "Fantasy", year: "2014", cover: "/covers/bumi.jpg", tone: "forest" },
  { id: "potter", title: "Deathly Hallows", author: "J. K. Rowling", category: "Fantasy", year: "2007", cover: "/covers/harry-potter.jpg", tone: "warm" },
]);

const filteredBooks = computed(() => {
  const term = query.value.trim().toLowerCase();
  return term ? books.value.filter((book) => [book.title, book.author, book.category].some((value) => value.toLowerCase().includes(term))) : books.value;
});

function navigate(next: View) {
  view.value = next;
  mobileOpen.value = false;
  authError.value = "";
  window.location.hash = next === "landing" ? "" : next;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function discover(term?: string) {
  if (term) query.value = term;
  requestAnimationFrame(() => document.querySelector("#books")?.scrollIntoView({ behavior: "smooth" }));
}

function goToSection(id: string) {
  if (view.value !== "landing") navigate("landing");
  requestAnimationFrame(() => document.querySelector(`#${id}`)?.scrollIntoView({ behavior: "smooth" }));
}

async function request(path: string, options: RequestInit = {}) {
  const response = await fetch(`${apiBase}${path}`, { ...options, headers: { "Content-Type": "application/json", ...options.headers } });
  const body = response.status === 204 ? null : await response.json();
  if (!response.ok) throw new Error(body?.detail || "Something went wrong. Please try again.");
  return body;
}

async function loadUser(token: string) {
  user.value = await request("/api/v1/users/me", { headers: { Authorization: `Bearer ${token}` } });
}

async function signIn(email: string, password: string) {
  const tokens = await request("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
  sessionStorage.setItem("litera_access", tokens.access_token);
  sessionStorage.setItem("litera_refresh", tokens.refresh_token);
  await loadUser(tokens.access_token);
  navigate("home");
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
    await request("/api/v1/auth/register", { method: "POST", body: JSON.stringify(registerForm.value) });
    await signIn(registerForm.value.email, registerForm.value.password);
  } catch (error) { authError.value = error instanceof Error ? error.message : "Unable to create your account."; }
  finally { loading.value = false; }
}

async function logout() {
  const refreshToken = sessionStorage.getItem("litera_refresh");
  try {
    if (refreshToken) await request("/api/v1/auth/logout", { method: "POST", body: JSON.stringify({ refresh_token: refreshToken }) });
  } finally {
    sessionStorage.removeItem("litera_access");
    sessionStorage.removeItem("litera_refresh");
    user.value = null;
    navigate("landing");
  }
}

onMounted(async () => {
  const hash = window.location.hash.slice(1) as View;
  if (["login", "register", "home"].includes(hash)) view.value = hash;
  const token = sessionStorage.getItem("litera_access");
  if (!token) { if (view.value === "home") view.value = "login"; return; }
  try { await loadUser(token); if (hash === "home") view.value = "home"; }
  catch { sessionStorage.removeItem("litera_access"); sessionStorage.removeItem("litera_refresh"); if (view.value === "home") view.value = "login"; }
});
</script>

<template>
  <div class="site-frame">
    <header class="site-header" :class="{ compact: view === 'login' || view === 'register' }">
      <button class="brand" type="button" @click="navigate(user ? 'home' : 'landing')">Litera<span>.</span></button>
      <template v-if="view !== 'login' && view !== 'register'">
        <nav class="desktop-nav" aria-label="Main navigation">
          <button type="button" @click="goToSection('about')">About</button>
          <button type="button" @click="goToSection('books')">Explore</button>
          <button type="button" @click="goToSection('learning')">How it works</button>
          <button type="button" @click="goToSection('membership')">Membership</button>
        </nav>
        <div class="nav-actions">
          <template v-if="user">
            <button class="text-button" type="button" @click="navigate('home')">{{ user.name }}</button>
            <button class="icon-button" type="button" title="Sign out" aria-label="Sign out" @click="logout"><LogOut :size="18" /></button>
          </template>
          <template v-else>
            <button class="text-button desktop-only" type="button" @click="navigate('login')">Sign in</button>
            <button class="primary-button desktop-only" type="button" @click="navigate('register')">Get started <ArrowUpRight :size="16" /></button>
          </template>
          <button class="icon-button mobile-menu-button" type="button" :aria-expanded="mobileOpen" aria-label="Toggle navigation" @click="mobileOpen = !mobileOpen"><X v-if="mobileOpen" :size="21" /><Menu v-else :size="21" /></button>
        </div>
        <nav v-if="mobileOpen" class="mobile-nav" aria-label="Mobile navigation">
          <button type="button" @click="goToSection('about')">About</button><button type="button" @click="goToSection('books')">Explore</button><button type="button" @click="goToSection('learning')">How it works</button><button type="button" @click="goToSection('membership')">Membership</button>
          <button v-if="!user" type="button" @click="navigate('login')">Sign in</button><button v-if="!user" type="button" @click="navigate('register')">Get started</button>
        </nav>
      </template>
      <button v-else class="quiet-link" type="button" @click="navigate('landing')">Back to discover</button>
    </header>

    <main v-if="view === 'landing'" class="landing-view">
      <section class="discovery-hero">
        <div class="hero-copy">
          <p class="eyebrow">Your space to read and grow</p>
          <h1>Read deeper.<br />Learn beyond<br />the page.</h1>
          <p class="hero-intro">Discover books with purpose, follow ideas that matter, and build a reading habit that stays with you.</p>
          <form class="discovery-search" role="search" @submit.prevent="discover()">
            <label class="sr-only" for="discovery">Search books, authors, or subjects</label><Search :size="20" aria-hidden="true" />
            <input id="discovery" v-model="query" type="search" placeholder="Search a title, author, or topic" />
            <button type="submit" aria-label="Search"><ArrowRight :size="20" /></button>
          </form>
        </div>
        <div class="hero-library" aria-label="Featured books">
          <img v-for="book in books" :key="book.id" :src="book.cover" :alt="`${book.title} cover`" />
        </div>
      </section>

      <section id="about" class="about-section">
        <p class="eyebrow">What is Litera?</p>
        <div class="about-copy"><h2>A digital library built around learning, not endless scrolling.</h2><div><p>Litera helps readers discover meaningful books, keep their reading organized, and return to ideas worth remembering.</p><p>It brings exploration, a personal shelf, and reading continuity into one calm space, so choosing what to read feels easier and every book has somewhere to lead.</p></div></div>
        <div class="about-principles"><span>Discover with purpose</span><span>Read at your pace</span><span>Grow through ideas</span></div>
      </section>

      <section class="category-strip" aria-label="Book categories">
        <div><span>Explore by interest</span><button type="button" @click="query = ''; discover()">All books</button><button type="button" @click="discover('Fiction')">Fiction</button><button type="button" @click="discover('Fantasy')">Fantasy</button><button type="button" @click="discover('Classic')">Classics</button></div>
      </section>

      <section id="books" class="book-section">
        <div class="section-heading"><div><p class="eyebrow">Curated for curious minds</p><h2>{{ query ? `Results for "${query}"` : "Start with a good book." }}</h2><p v-if="!query" class="section-description">Stories and ideas selected to help you see more, understand more, and keep learning.</p></div><button v-if="query" class="line-button" type="button" @click="query = ''">Clear search <X :size="15" /></button></div>
        <div v-if="filteredBooks.length" class="book-grid">
          <article v-for="(book, index) in filteredBooks" :key="book.id" class="book-item"><div class="cover-wrap" :class="book.tone"><span class="book-number">0{{ index + 1 }}</span><img :src="book.cover" :alt="`${book.title} cover`" /></div><div class="book-meta"><h3>{{ book.title }}</h3><p>{{ book.author }}</p><span>{{ book.category }} / {{ book.year }}</span></div></article>
        </div>
        <div v-else class="empty-search"><p>No title here yet.</p><button class="line-button" type="button" @click="query = ''">Return to all books <ArrowRight :size="15" /></button></div>
      </section>

      <section id="learning" class="learning-section">
        <div class="learning-heading"><p class="eyebrow">More than a reading list</p><h2>Turn every page<br />into progress.</h2><p>Litera gives your curiosity a simple path, from finding the right book to remembering what mattered.</p></div>
        <div class="learning-steps">
          <article><span>01</span><Compass :size="26" /><h3>Find your direction</h3><p>Explore by topic, mood, or the question you want to answer next.</p></article>
          <article><span>02</span><Bookmark :size="26" /><h3>Build your shelf</h3><p>Keep meaningful books in one place and return whenever you are ready.</p></article>
          <article><span>03</span><NotebookPen :size="26" /><h3>Keep what matters</h3><p>Turn reading into a habit and ideas into something you can use.</p></article>
        </div>
      </section>

      <section class="why-section">
        <div class="why-heading"><p class="eyebrow">Why Litera?</p><h2>Reading should feel<br />simple and meaningful.</h2><p>Most platforms compete for your attention. Litera is designed to help you direct it.</p></div>
        <div class="benefit-grid">
          <article><Compass :size="25" /><h3>Purposeful discovery</h3><p>Start from an interest, a question, or the kind of perspective you want to find.</p></article>
          <article><LibraryBig :size="25" /><h3>One personal library</h3><p>Keep the books you care about together instead of losing them across tabs and lists.</p></article>
          <article><History :size="25" /><h3>Easy to return</h3><p>Your reading space is ready when you come back, without making you start over.</p></article>
          <article><Focus :size="25" /><h3>Made for focus</h3><p>A clear experience with less noise, helping the book remain the most important thing.</p></article>
        </div>
      </section>

      <section class="path-section">
        <div class="path-heading"><p class="eyebrow">Choose your path</p><h2>What will you<br />learn next?</h2></div>
        <div class="path-list"><button type="button" @click="discover('Fiction')"><span>See life through another story</span><small>Fiction</small><ArrowUpRight :size="20" /></button><button type="button" @click="discover('Fantasy')"><span>Stretch your imagination</span><small>Fantasy</small><ArrowUpRight :size="20" /></button><button type="button" @click="discover('Classic')"><span>Meet ideas that endured</span><small>Classics</small><ArrowUpRight :size="20" /></button></div>
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
          <details><summary>What can I do with Litera?<ChevronRight :size="18" /></summary><p>You can explore the catalog, search by title or category, create an account, and build a personal reading space as the library grows.</p></details>
          <details><summary>Is Litera only for students?<ChevronRight :size="18" /></summary><p>No. Litera is for anyone who reads to understand, imagine, improve a skill, or simply spend time with a good story.</p></details>
          <details><summary>Do I need an account to explore?<ChevronRight :size="18" /></summary><p>You can browse the public catalog without an account. An account gives you a personal space for your reading journey.</p></details>
          <details><summary>What kinds of books will I find?<ChevronRight :size="18" /></summary><p>The catalog can hold fiction, classics, fantasy, and learning-focused collections, with more subjects added as Litera develops.</p></details>
        </div>
      </section>

      <section id="membership" class="membership-section"><div><p class="eyebrow">Your next chapter starts here</p><h2>A quieter place<br />to keep growing.</h2><p>Create your shelf, continue where you stopped, and make room for a better reading habit.</p><button type="button" class="membership-button" @click="navigate('register')">Start learning <ArrowRight :size="18" /></button></div><Sparkles :size="120" stroke-width="1" aria-hidden="true" /></section>
    </main>

    <main v-else-if="view === 'login' || view === 'register'" class="auth-view">
      <div class="auth-lines" aria-hidden="true"><span></span><span></span><span></span></div>
      <section class="auth-panel">
        <p class="eyebrow">{{ view === 'login' ? 'Welcome back' : 'Start your shelf' }}</p><h1>{{ view === 'login' ? 'Continue reading.' : 'Make room for curiosity.' }}</h1>
        <p class="auth-intro">{{ view === 'login' ? 'Your next thought is waiting where you left it.' : 'One account for discovery, learning, and everything you want to return to.' }}</p>
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
        <p class="auth-switch">{{ view === 'login' ? 'New to Litera?' : 'Already have a shelf?' }} <button type="button" @click="navigate(view === 'login' ? 'register' : 'login')">{{ view === 'login' ? 'Create an account' : 'Sign in' }}</button></p>
      </section><p class="auth-footnote"><BookOpen :size="16" /> Read slowly. Learn deeply.</p>
    </main>

    <main v-else class="home-view">
      <section class="home-intro"><p class="eyebrow">Your reading space</p><h1>Good {{ new Date().getHours() < 12 ? 'morning' : new Date().getHours() < 18 ? 'afternoon' : 'evening' }},<br />{{ user?.name || 'reader' }}.</h1><p>What's on your mind today?</p><form class="home-search" @submit.prevent="navigate('landing'); discover()"><Search :size="20" /><input v-model="query" type="search" placeholder="Search a title, author, or idea..." /><button type="submit" aria-label="Search"><ArrowUpRight :size="21" /></button></form></section>
      <section class="empty-shelf"><div class="empty-number">00</div><div><p class="eyebrow">Pick up where you left off</p><h2>Your shelf is ready<br />for its first chapter.</h2><p>Books you begin will gather here, ready when you return.</p><button class="line-button" type="button" @click="navigate('landing')">Find your first read <ArrowRight :size="16" /></button></div></section>
      <section class="home-books"><div class="section-heading"><div><p class="eyebrow">Explore while you settle in</p><h2>Open a new direction.</h2></div><button class="line-button" type="button" @click="navigate('landing')">View all <ChevronRight :size="16" /></button></div><div class="book-grid compact-grid"><article v-for="(book, index) in books.slice(0, 3)" :key="book.id" class="book-item"><div class="cover-wrap" :class="book.tone"><span class="book-number">0{{ index + 1 }}</span><img :src="book.cover" :alt="`${book.title} cover`" /></div><div class="book-meta"><h3>{{ book.title }}</h3><p>{{ book.author }}</p><span>{{ book.category }} / {{ book.year }}</span></div></article></div></section>
    </main>

    <footer v-if="view === 'landing' || view === 'home'" class="site-footer"><button class="brand" type="button" @click="navigate('landing')">Litera<span>.</span></button><p>A calmer place to read, think, and return.</p><span>&copy; {{ new Date().getFullYear() }}</span></footer>
  </div>
</template>
