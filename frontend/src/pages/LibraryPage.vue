<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ArrowRight, BookOpen, CalendarClock, LoaderCircle, X } from "@lucide/vue";
import { api, formatDate, formatEnum, type Loan, type ReadingProgressItem, type Reservation } from "../api";
import { notify } from "../toast";

const emit = defineEmits<{ navigate: [path: string] }>();
const loans = ref<Loan[]>([]);
const reservations = ref<Reservation[]>([]);
const reading = ref<ReadingProgressItem[]>([]);
const tab = ref<"reading" | "borrowed" | "reservations" | "history">("reading");
const loading = ref(true);
const error = ref("");
const cancelling = ref("");

const active = computed(() => loans.value.filter((loan) => ["BORROWED", "OVERDUE"].includes(loan.status)));
const history = computed(() => loans.value.filter((loan) => ["RETURNED", "LOST"].includes(loan.status)));
const activeReservations = computed(() => reservations.value.filter((item) => ["WAITING", "READY"].includes(item.status)));
const currentItems = computed(() => tab.value === "reading" ? reading.value : tab.value === "borrowed" ? active.value : tab.value === "history" ? history.value : activeReservations.value);

function daysLabel(loan: Loan) {
  const days = Math.ceil((new Date(loan.due_at).getTime() - Date.now()) / 86400000);
  if (days < 0) return `Overdue by ${Math.abs(days)} day${Math.abs(days) === 1 ? "" : "s"}`;
  if (days === 0) return "Due today";
  return `${days} day${days === 1 ? "" : "s"} remaining`;
}

async function load() {
  loading.value = true; error.value = "";
  try { [loans.value, reservations.value, reading.value] = await Promise.all([api<Loan[]>("/api/v1/loans/me"), api<Reservation[]>("/api/v1/reservations/me"), api<ReadingProgressItem[]>("/api/v1/reading-progress")]); }
  catch (caught) { error.value = caught instanceof Error ? caught.message : "Unable to load your library."; }
  finally { loading.value = false; }
}

async function cancel(item: Reservation) {
  cancelling.value = item.id;
  try {
    await api(`/api/v1/reservations/${item.id}`, { method: "DELETE" });
    notify("Reservation cancelled.");
    await load();
  } catch (caught) { notify(caught instanceof Error ? caught.message : "Unable to cancel reservation.", "error"); }
  finally { cancelling.value = ""; }
}

onMounted(load);
</script>

<template>
  <main class="library-page">
    <header><p class="eyebrow">Your reading space</p><h1>My Library</h1><p>Borrowed books, reservations, and the titles you have returned.</p></header>
    <nav class="library-tabs" aria-label="Library sections">
      <button :class="{ active: tab === 'reading' }" type="button" @click="tab = 'reading'">Reading <span>{{ reading.length }}</span></button>
      <button :class="{ active: tab === 'borrowed' }" type="button" @click="tab = 'borrowed'">Borrowed <span>{{ active.length }}</span></button>
      <button :class="{ active: tab === 'reservations' }" type="button" @click="tab = 'reservations'">Reservations <span>{{ activeReservations.length }}</span></button>
      <button :class="{ active: tab === 'history' }" type="button" @click="tab = 'history'">History <span>{{ history.length }}</span></button>
    </nav>
    <div v-if="loading" class="library-loading"><LoaderCircle class="spin" :size="23" /> Loading your library</div>
    <section v-else-if="error" class="library-empty"><h2>Your library is out of reach.</h2><p>{{ error }}</p><button type="button" @click="load">Try again</button></section>
    <section v-else-if="!currentItems.length" class="library-empty"><BookOpen :size="38" /><h2>Your shelf is waiting.</h2><p>{{ tab === 'reading' ? 'Digital books you start will appear here.' : tab === 'reservations' ? 'Books you reserve will appear here.' : tab === 'history' ? 'Returned books will remain here for you.' : 'Books you borrow will appear here.' }}</p><button type="button" @click="emit('navigate', '/explore')">Explore Litera <ArrowRight :size="16" /></button></section>
    <section v-else class="library-list">
      <article v-for="item in tab === 'reading' ? reading : []" :key="item.id">
        <div class="library-cover"><img v-if="item.book.cover_url" :src="item.book.cover_url" :alt="`${item.book.title} cover`" /><BookOpen v-else :size="25" /></div>
        <div><span class="status-badge">Reading</span><h2>{{ item.book.title }}</h2><p>{{ item.chapter?.title || `Page ${item.current_page}` }}</p><div class="reading-progress"><i :style="{ width: `${item.progress_percentage}%` }"></i></div><strong>{{ Math.round(item.progress_percentage) }}% complete</strong></div>
        <button type="button" aria-label="Continue reading" @click="emit('navigate', `/read/${item.edition_id}`)"><ArrowRight :size="18" /></button>
      </article>
      <article v-for="loan in tab === 'reservations' ? [] : (tab === 'borrowed' ? active : history)" :key="loan.id">
        <div class="library-cover"><img v-if="loan.book_copy.edition.book.cover_url" :src="loan.book_copy.edition.book.cover_url" :alt="`${loan.book_copy.edition.book.title} cover`" /><BookOpen v-else :size="25" /></div>
        <div><span class="status-badge" :class="loan.status.toLowerCase()">{{ formatEnum(loan.status) }}</span><h2>{{ loan.book_copy.edition.book.title }}</h2><p>{{ loan.book_copy.barcode }} · Borrowed {{ formatDate(loan.borrowed_at) }}</p><strong v-if="tab === 'borrowed'" :class="{ overdue: loan.status === 'OVERDUE' }">{{ daysLabel(loan) }}</strong><strong v-else>Returned {{ formatDate(loan.returned_at) }}</strong></div>
        <button type="button" aria-label="View book" @click="emit('navigate', `/books/${loan.book_copy.edition.book.slug}`)"><ArrowRight :size="18" /></button>
      </article>
      <article v-for="item in tab === 'reservations' ? activeReservations : []" :key="item.id">
        <div class="library-cover"><img v-if="item.edition.book.cover_url" :src="item.edition.book.cover_url" :alt="`${item.edition.book.title} cover`" /><CalendarClock v-else :size="25" /></div>
        <div><span class="status-badge" :class="item.status.toLowerCase()">{{ formatEnum(item.status) }}</span><h2>{{ item.edition.book.title }}</h2><p v-if="item.status === 'WAITING'">Queue position #{{ item.queue_position }}</p><p v-else>Ready for pickup<span v-if="item.expires_at"> until {{ formatDate(item.expires_at) }}</span></p><strong v-if="item.book_copy">{{ item.book_copy.barcode }} · {{ item.book_copy.shelf_location || 'Pickup desk' }}</strong></div>
        <button type="button" :disabled="cancelling === item.id" aria-label="Cancel reservation" @click="cancel(item)"><X :size="18" /></button>
      </article>
    </section>
  </main>
</template>

<style scoped>
.library-page { width: min(1120px, 88vw); min-height: 78vh; margin: auto; padding: 75px 0 130px; }.library-page > header { display: grid; grid-template-columns: .65fr 1fr .8fr; gap: 5vw; align-items: end; padding-bottom: 65px; }.library-page h1 { margin: 0; font-size: clamp(3.2rem, 6vw, 6rem); font-weight: 560; line-height: .95; }.library-page > header > p:last-child { margin: 0; color: #69706b; line-height: 1.65; }.library-tabs { display: flex; gap: 35px; border-bottom: 1px solid #cdd2cd; }.library-tabs button { display: flex; gap: 9px; padding: 16px 0; border-bottom: 2px solid transparent; background: transparent; color: #68706a; }.library-tabs button.active { border-color: #173d32; color: #173d32; }.library-tabs span { color: #949a95; font-size: .72rem; }.library-list { border-bottom: 1px solid #cdd2cd; }.library-list article { display: grid; grid-template-columns: 78px 1fr auto; gap: 24px; align-items: center; min-height: 150px; padding: 24px 0; border-top: 1px solid #cdd2cd; }.library-cover { display: grid; width: 66px; aspect-ratio: 2/3; place-items: center; overflow: hidden; background: #dce8e3; color: #4f6659; }.library-cover img { width: 100%; height: 100%; object-fit: cover; }.library-list h2 { margin: 8px 0; font-size: 1.35rem; }.library-list p { margin: 0 0 8px; color: #747b75; font-size: .85rem; }.library-list strong { color: #56655d; font-size: .82rem; }.library-list strong.overdue { color: #a34b3f; }.library-list > article > button { display: grid; width: 40px; height: 40px; place-items: center; border-radius: 50%; background: transparent; }.library-list > article > button:hover { background: #e4e8e4; }.status-badge { display: inline-block; padding: 5px 8px; background: #e2e5e2; color: #5f6661; font-size: .65rem; font-weight: 700; text-transform: uppercase; }.status-badge.ready,.status-badge.returned { background: #d9e8df; color: #315a46; }.status-badge.overdue { background: #f0ddd8; color: #8a4035; }.library-loading,.library-empty { display: grid; min-height: 330px; place-content: center; justify-items: center; gap: 14px; text-align: center; }.library-empty h2 { margin: 12px 0 0; font-size: 2.2rem; font-weight: 560; }.library-empty p { margin: 0; color: #747b75; }.library-empty button { display: inline-flex; align-items: center; gap: 8px; margin-top: 12px; padding: 10px 0; border-bottom: 1px solid; background: transparent; }
.reading-progress { width: min(340px,100%); height: 3px; margin: 10px 0 6px; background: #d8ddd9; }.reading-progress i { display: block; height: 100%; background: #2f6953; }
@media (max-width: 760px) { .library-page { width: calc(100% - 44px); padding-top: 55px; }.library-page > header { grid-template-columns: 1fr; gap: 18px; }.library-tabs { gap: 20px; overflow-x: auto; }.library-tabs button { white-space: nowrap; }.library-list article { grid-template-columns: 58px 1fr auto; gap: 14px; }.library-cover { width: 54px; }.library-list h2 { font-size: 1.05rem; } }
</style>
