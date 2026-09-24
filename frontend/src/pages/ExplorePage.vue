<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { ArrowLeft, ArrowRight, Search, SlidersHorizontal, X } from "@lucide/vue";
import { api, type BookSummary, type Category, type Page } from "../api";
import BookCard from "../components/BookCard.vue";

const emit = defineEmits<{ navigate: [path: string] }>();
const params = new URLSearchParams(location.search);
const search = ref(params.get("search") || "");
const category = ref(params.get("category") || "");
const bookType = ref(params.get("book_type") || "");
const language = ref(params.get("language") || "");
const page = ref(Math.max(1, Number(params.get("page")) || 1));
const result = ref<Page<BookSummary> | null>(null);
const categories = ref<Category[]>([]);
const loading = ref(true);
const error = ref("");
let searchTimer = 0;
let requestNumber = 0;

const hasFilters = computed(() => Boolean(search.value || category.value || bookType.value || language.value));
const pageNumbers = computed(() => {
  const total = result.value?.total_pages || 1;
  const start = Math.max(1, Math.min(page.value - 1, total - 2));
  return Array.from({ length: Math.min(3, total) }, (_, index) => start + index);
});

function syncUrl() {
  const next = new URLSearchParams();
  if (search.value.trim()) next.set("search", search.value.trim());
  if (category.value) next.set("category", category.value);
  if (bookType.value) next.set("book_type", bookType.value);
  if (language.value) next.set("language", language.value);
  if (page.value > 1) next.set("page", String(page.value));
  history.replaceState({}, "", `/explore${next.size ? `?${next}` : ""}`);
}

async function loadBooks() {
  const current = ++requestNumber;
  loading.value = true;
  error.value = "";
  syncUrl();
  const query = new URLSearchParams({ page: String(page.value), page_size: "12" });
  if (search.value.trim()) query.set("search", search.value.trim());
  if (category.value) query.set("category", category.value);
  if (bookType.value) query.set("book_type", bookType.value);
  if (language.value) query.set("language", language.value);
  try {
    const response = await api<Page<BookSummary>>(`/api/v1/books?${query}`);
    if (current === requestNumber) result.value = response;
  } catch (caught) {
    if (current === requestNumber) error.value = caught instanceof Error ? caught.message : "Unable to load books.";
  } finally {
    if (current === requestNumber) loading.value = false;
  }
}

function applyFilter() { page.value = 1; loadBooks(); }
function selectCategory(slug: string) { category.value = slug; applyFilter(); }
function changePage(next: number) { page.value = next; loadBooks(); window.scrollTo({ top: 0, behavior: "smooth" }); }
function clearFilters() { search.value = ""; category.value = ""; bookType.value = ""; language.value = ""; page.value = 1; loadBooks(); }

watch(search, () => {
  window.clearTimeout(searchTimer);
  searchTimer = window.setTimeout(() => { page.value = 1; loadBooks(); }, 400);
});
onBeforeUnmount(() => window.clearTimeout(searchTimer));
onMounted(async () => {
  loadBooks();
  try { categories.value = (await api<Page<Category>>("/api/v1/categories?page_size=100")).items; }
  catch { categories.value = []; }
});
</script>

<template>
  <main class="explore-page">
    <header class="explore-intro">
      <p class="eyebrow">Explore the collection</p>
      <div><h1>Find something<br />worth your time.</h1><p>Follow a subject, an author, or a question. The next useful idea may be closer than you think.</p></div>
      <label class="explore-search"><Search :size="20" /><span class="sr-only">Search title, author, or topic</span><input v-model="search" type="search" placeholder="Search title, author, or topic..." /><button v-if="search" type="button" aria-label="Clear search" @click="search = ''"><X :size="18" /></button></label>
    </header>

    <section class="filter-section" aria-label="Book filters">
      <div class="category-filters">
        <button type="button" :class="{ active: !category }" @click="selectCategory('')">All</button>
        <button v-for="item in categories" :key="item.id" type="button" :class="{ active: category === item.slug }" @click="selectCategory(item.slug)">{{ item.name }}</button>
      </div>
      <div class="select-filters"><SlidersHorizontal :size="17" aria-hidden="true" /><label><span class="sr-only">Book type</span><select v-model="bookType" @change="applyFilter"><option value="">All types</option><option value="FICTION">Fiction</option><option value="NON_FICTION">Non-fiction</option><option value="EDUCATIONAL">Educational</option><option value="REFERENCE">Reference</option></select></label><label><span class="sr-only">Language</span><select v-model="language" @change="applyFilter"><option value="">All languages</option><option value="id">Indonesian</option><option value="en">English</option></select></label><button v-if="hasFilters" class="reset-filter" type="button" @click="clearFilters">Reset</button></div>
    </section>

    <section class="results-section" aria-live="polite">
      <div class="result-heading"><p>{{ loading ? 'Looking through the shelves...' : `${result?.total || 0} ${result?.total === 1 ? 'book' : 'books'}` }}</p><span v-if="hasFilters && !loading">Filtered collection</span></div>
      <div v-if="loading" class="explore-grid" aria-label="Loading books"><div v-for="index in 8" :key="index" class="book-skeleton"><span></span><i></i><i></i></div></div>
      <div v-else-if="error" class="result-state"><h2>The shelves are out of reach.</h2><p>{{ error }}</p><button type="button" @click="loadBooks">Try again <ArrowRight :size="16" /></button></div>
      <div v-else-if="!result?.items.length" class="result-state"><h2>{{ search ? `Nothing matched "${search}".` : 'There are no books here yet.' }}</h2><p>{{ hasFilters ? 'Try another title, author, category, or reset your filters.' : 'The collection is ready for its first published title.' }}</p><button v-if="hasFilters" type="button" @click="clearFilters">Show all books <ArrowRight :size="16" /></button></div>
      <div v-else class="explore-grid"><BookCard v-for="(book, index) in result.items" :key="book.id" :book="book" :index="(page - 1) * 12 + index" @open="emit('navigate', `/books/${$event}`)" /></div>

      <nav v-if="result && result.total_pages > 1" class="pagination" aria-label="Book pages"><button type="button" :disabled="page === 1" aria-label="Previous page" @click="changePage(page - 1)"><ArrowLeft :size="18" /></button><button v-for="number in pageNumbers" :key="number" type="button" :class="{ active: page === number }" :aria-current="page === number ? 'page' : undefined" @click="changePage(number)">{{ number }}</button><button type="button" :disabled="page === result.total_pages" aria-label="Next page" @click="changePage(page + 1)"><ArrowRight :size="18" /></button></nav>
    </section>
  </main>
</template>

<style scoped>
.explore-page { min-height: 80vh; }
.explore-intro { padding: 72px max(6vw, calc((100vw - 1280px) / 2)) 65px; background: #dce8e3; }
.explore-intro > div { display: grid; grid-template-columns: 1.1fr .9fr; gap: 8vw; align-items: end; }
.explore-intro h1 { margin: 0; font-size: clamp(3rem, 5.6vw, 5.8rem); font-weight: 560; line-height: .96; }
.explore-intro > div > p { max-width: 470px; margin: 0 0 8px; color: #59655f; line-height: 1.7; }
.explore-search { display: grid; grid-template-columns: auto 1fr auto; gap: 14px; align-items: center; width: min(760px, 100%); margin-top: 50px; padding: 13px 4px; border-bottom: 2px solid #17251f; }
.explore-search input { min-width: 0; border: 0; outline: 0; background: transparent; font-size: 1.08rem; }
.explore-search button { display: grid; padding: 7px; place-items: center; background: transparent; }
.filter-section { display: flex; justify-content: space-between; gap: 30px; width: min(1280px, 88vw); margin: auto; padding: 25px 0; border-bottom: 1px solid #d3d7d3; }
.category-filters { display: flex; flex-wrap: wrap; gap: 7px; }
.category-filters button { padding: 9px 13px; border-radius: 3px; background: transparent; color: #5c635e; font-size: .82rem; }
.category-filters button.active { background: #173d32; color: white; }
.select-filters { display: flex; align-items: center; gap: 12px; }
.select-filters select { height: 36px; border: 0; border-bottom: 1px solid #aeb4af; outline: 0; background: transparent; font-size: .8rem; }
.reset-filter { padding: 8px 0; border-bottom: 1px solid #171a18; background: transparent; font-size: .78rem; }
.results-section { width: min(1280px, 88vw); margin: auto; padding: 45px 0 120px; }
.result-heading { display: flex; justify-content: space-between; margin-bottom: 38px; color: #747a75; font-size: .76rem; text-transform: uppercase; }
.result-heading p { margin: 0; }
.explore-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 58px clamp(24px, 4vw, 58px); }
.book-skeleton span { display: block; aspect-ratio: 2 / 3; background: #e3e6e2; animation: pulse 1.3s ease-in-out infinite; }
.book-skeleton i { display: block; width: 75%; height: 12px; margin-top: 17px; background: #e3e6e2; }
.book-skeleton i:last-child { width: 45%; height: 9px; margin-top: 8px; }
.result-state { padding: 90px 0; border-block: 1px solid #d3d7d3; }
.result-state h2 { margin: 0 0 14px; font-size: clamp(1.8rem, 3vw, 3rem); font-weight: 560; }
.result-state p { max-width: 540px; color: #6a706b; line-height: 1.6; }
.result-state button { display: inline-flex; align-items: center; gap: 9px; margin-top: 20px; padding: 10px 0; border-bottom: 1px solid; background: transparent; }
.pagination { display: flex; justify-content: center; gap: 7px; margin-top: 80px; }
.pagination button { display: grid; width: 40px; height: 40px; place-items: center; background: transparent; }
.pagination button.active { background: #173d32; color: white; }
.pagination button:disabled { cursor: default; opacity: .3; }
@keyframes pulse { 50% { opacity: .48; } }
@media (max-width: 900px) { .explore-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); } .filter-section { display: block; } .select-filters { margin-top: 20px; } }
@media (max-width: 650px) { .explore-intro { padding: 55px 22px; } .explore-intro > div { grid-template-columns: 1fr; gap: 24px; } .explore-intro h1 { font-size: clamp(2.8rem, 14vw, 4.2rem); } .filter-section, .results-section { width: calc(100% - 44px); } .category-filters { flex-wrap: nowrap; overflow-x: auto; padding-bottom: 5px; } .category-filters button { flex: none; } .select-filters { display: grid; grid-template-columns: auto 1fr 1fr auto; } .select-filters select { width: 100%; } .explore-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 40px 17px; } }
</style>
