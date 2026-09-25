<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch, type ComponentPublicInstance } from "vue";
import { AlignLeft, ArrowLeft, Bookmark, BookmarkCheck, ChevronLeft, ChevronRight, GraduationCap, List, LoaderCircle, Minus, Moon, Plus, Sun, X } from "@lucide/vue";
import { api, hasSession, type Reader, type ReaderBookmark, type ReaderPage as ReaderTextPage, type ReadingProgress, type SummaryResponse } from "../api";
import { notify } from "../toast";

const props = defineProps<{ editionId: string; darkMode: boolean }>();
const emit = defineEmits<{ navigate: [path: string]; toggleTheme: [] }>();
const metadata = ref<Reader | null>(null);
const pages = ref<ReaderTextPage[]>([]);
const bookmarks = ref<ReaderBookmark[]>([]);
const page = ref(1);
const textSize = ref(1.125);
const readingPercent = ref(0);
const loading = ref(true);
const error = ref("");
const sidebar = ref(true);
const stage = ref<HTMLElement | null>(null);
const summary = ref<SummaryResponse | null>(null);
const summaryLoading = ref(false);
const summaryError = ref("");
const pageElements = new Map<number, HTMLElement>();
let saveTimer: ReturnType<typeof setTimeout> | undefined;
let scrollFrame = 0;

type SavedPosition = { page: number; offset: number; updated_at: string };

type TextBlock = { text: string; heading: boolean };

function textBlocks(content: string): TextBlock[] {
  return content.replace(/\r/g, "").split(/\n\s*\n/).map((block) => {
    const text = block.trim().replace(/-\n(?=[a-z])/g, "").replace(/\n/g, " ").replace(/\s+/g, " ");
    const heading = text.length < 120 && (/^(chapter|book|part|contents|preface|introduction)\b/i.test(text) || (text.length > 2 && text === text.toUpperCase()));
    return { text, heading };
  }).filter((block) => block.text);
}

const formattedPages = computed(() => pages.value.map((item) => ({ ...item, blocks: textBlocks(item.content) })));
const currentChapter = computed(() => metadata.value?.chapters.find((item) => page.value >= item.page_start && page.value <= item.page_end) || null);
const bookmarked = computed(() => bookmarks.value.some((item) => item.page_number === page.value));
const textScale = computed(() => Math.round(textSize.value / 1.125 * 100));
const progressKey = computed(() => `litera_reader_progress_${props.editionId}`);
const bookmarkKey = computed(() => `litera_reader_bookmarks_${props.editionId}`);

function offsetFrom(data: Record<string, unknown> | null | undefined): number {
  const value = Number(data?.offset || 0);
  return Number.isFinite(value) ? Math.max(0, Math.min(1, value)) : 0;
}

function currentPosition(): SavedPosition {
  const element = pageElements.get(page.value);
  const top = stage.value?.scrollTop || 0;
  const offset = element ? Math.max(0, Math.min(1, (top - element.offsetTop + 40) / Math.max(1, element.offsetHeight))) : 0;
  return { page: page.value, offset, updated_at: new Date().toISOString() };
}

function setPageElement(element: Element | ComponentPublicInstance | null) {
  if (!(element instanceof HTMLElement)) return;
  pageElements.set(Number(element.dataset.page), element);
}

function updateCurrentPage() {
  scrollFrame = 0;
  if (!stage.value) return;
  const marker = stage.value.getBoundingClientRect().top + stage.value.clientHeight * 0.28;
  let nearest = page.value;
  let distance = Number.POSITIVE_INFINITY;
  for (const [number, element] of pageElements) {
    const rect = element.getBoundingClientRect();
    const nextDistance = marker < rect.top ? rect.top - marker : marker > rect.bottom ? marker - rect.bottom : 0;
    if (nextDistance < distance) { distance = nextDistance; nearest = number; }
  }
  page.value = nearest;
  readingPercent.value = stage.value.scrollHeight > stage.value.clientHeight
    ? stage.value.scrollTop / (stage.value.scrollHeight - stage.value.clientHeight) * 100
    : 0;
  queueSave();
}

function handleScroll() {
  if (!scrollFrame) scrollFrame = requestAnimationFrame(updateCurrentPage);
}

function go(next: number, smooth = true, offset = 0) {
  if (!metadata.value || !stage.value) return;
  const target = Math.min(metadata.value.page_count, Math.max(1, Math.round(next) || 1));
  const element = pageElements.get(target);
  if (element) stage.value.scrollTo({ top: Math.max(0, element.offsetTop + element.offsetHeight * offset - 40), behavior: smooth ? "smooth" : "auto" });
  page.value = target;
  requestAnimationFrame(updateCurrentPage);
}

async function saveProgress() {
  if (!metadata.value) return;
  const position = currentPosition();
  localStorage.setItem(progressKey.value, JSON.stringify(position));
  if (!hasSession()) return;
  await api(`/api/v1/reading-progress/${props.editionId}`, {
    method: "PUT",
    body: JSON.stringify({ current_page: position.page, chapter_id: currentChapter.value?.id || null, position_data: { offset: position.offset } }),
  }).catch(() => {});
}

function queueSave() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(saveProgress, 700);
}

async function loadSummary() {
  if (!currentChapter.value) return;
  if (summary.value) { summary.value = null; return; }
  summaryLoading.value = true; summaryError.value = "";
  try { summary.value = await api<SummaryResponse>("/api/v1/chapters/" + currentChapter.value.id + "/summary"); }
  catch (caught) { summaryError.value = caught instanceof Error ? caught.message : "Summary unavailable."; }
  finally { summaryLoading.value = false; }
}

async function toggleBookmark() {
  const existing = bookmarks.value.find((item) => item.page_number === page.value);
  if (!hasSession()) {
    if (existing) {
      bookmarks.value = bookmarks.value.filter((item) => item.id !== existing.id);
      notify("Reading marker removed.");
    } else {
      const position = currentPosition();
      bookmarks.value.push({ id: `local-${Date.now()}`, edition_id: props.editionId, chapter_id: currentChapter.value?.id || null, page_number: page.value, position_data: { offset: position.offset }, note: null, created_at: new Date().toISOString() });
      notify("Reading spot marked.");
    }
    localStorage.setItem(bookmarkKey.value, JSON.stringify(bookmarks.value));
    return;
  }
  try {
    if (existing) {
      await api(`/api/v1/bookmarks/${existing.id}`, { method: "DELETE" });
      bookmarks.value = bookmarks.value.filter((item) => item.id !== existing.id);
      notify("Bookmark removed.");
    } else {
      const position = currentPosition();
      const created = await api<ReaderBookmark>("/api/v1/bookmarks", { method: "POST", body: JSON.stringify({ edition_id: props.editionId, chapter_id: currentChapter.value?.id || null, page_number: page.value, position_data: { offset: position.offset } }) });
      bookmarks.value.push(created);
      notify("Page bookmarked.");
    }
  } catch (caught) { notify(caught instanceof Error ? caught.message : "Unable to update bookmark.", "error"); }
}

async function load() {
  loading.value = true; error.value = "";
  try {
    const [reader, textPages] = await Promise.all([
      api<Reader>(`/api/v1/editions/${props.editionId}/reader`),
      api<ReaderTextPage[]>(`/api/v1/editions/${props.editionId}/pages`),
    ]);
    metadata.value = reader;
    pages.value = textPages;
    let resume: SavedPosition = { page: 1, offset: 0, updated_at: "" };
    try {
      const local = JSON.parse(localStorage.getItem(progressKey.value) || "null") as SavedPosition | null;
      if (local?.page) resume = local;
    } catch { localStorage.removeItem(progressKey.value); }
    if (hasSession()) {
      const [progress, saved] = await Promise.all([
        api<ReadingProgress | null>(`/api/v1/reading-progress/${props.editionId}`),
        api<ReaderBookmark[]>(`/api/v1/editions/${props.editionId}/bookmarks`),
      ]);
      if (progress && new Date(progress.last_read_at).getTime() > new Date(resume.updated_at || 0).getTime()) {
        resume = { page: progress.current_page, offset: offsetFrom(progress.position_data), updated_at: progress.last_read_at };
      }
      bookmarks.value = saved;
    } else {
      try { bookmarks.value = JSON.parse(localStorage.getItem(bookmarkKey.value) || "[]") as ReaderBookmark[]; }
      catch { localStorage.removeItem(bookmarkKey.value); }
    }
    page.value = resume.page;
    loading.value = false;
    await nextTick();
    go(resume.page, false, resume.offset);
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "Unable to open this edition.";
    loading.value = false;
  }
}

watch(page, queueSave);
watch(() => currentChapter.value?.id, () => { summary.value = null; summaryError.value = ""; });
onMounted(load);
onBeforeUnmount(() => {
  clearTimeout(saveTimer); cancelAnimationFrame(scrollFrame);
  void saveProgress();
});
</script>

<template>
  <main class="reader-shell" :class="{ dark: darkMode }">
    <header class="reader-toolbar">
      <button type="button" aria-label="Back to book" title="Back to book" @click="emit('navigate', metadata ? `/books/${metadata.book.slug}` : '/explore')"><ArrowLeft :size="19" /></button>
      <div><strong>{{ metadata?.book.title || 'Litera Reader' }}</strong><small>{{ currentChapter?.title || 'Digital edition' }}</small></div>
      <nav aria-label="Reader controls">
        <button type="button" aria-label="Decrease text size" title="Decrease text size" :disabled="textSize <= .875" @click="textSize = Math.max(.875, textSize - .125)"><Minus :size="18" /></button>
        <label class="text-control"><input v-model.number="textSize" type="range" min=".875" max="1.5" step=".125" aria-label="Text size" /><span>{{ textScale }}%</span></label>
        <button type="button" aria-label="Increase text size" title="Increase text size" :disabled="textSize >= 1.5" @click="textSize = Math.min(1.5, textSize + .125)"><Plus :size="18" /></button>
        <button type="button" :aria-label="darkMode ? 'Use light mode' : 'Use dark mode'" :title="darkMode ? 'Light mode' : 'Dark mode'" @click="emit('toggleTheme')"><Sun v-if="darkMode" :size="18" /><Moon v-else :size="18" /></button>
        <button type="button" :aria-label="bookmarked ? 'Remove bookmark' : 'Bookmark position'" :title="bookmarked ? 'Remove bookmark' : 'Bookmark position'" @click="toggleBookmark"><BookmarkCheck v-if="bookmarked" :size="19" /><Bookmark v-else :size="19" /></button>
        <button type="button" aria-label="Toggle chapters" title="Chapters" @click="sidebar = !sidebar"><X v-if="sidebar" :size="19" /><List v-else :size="19" /></button>
      </nav>
    </header>
    <div class="reading-progress" :style="{ width: `${readingPercent}%` }"></div>

    <div v-if="loading" class="reader-state"><LoaderCircle class="spin" :size="28" /> Preparing your book</div>
    <div v-else-if="error" class="reader-state"><h1>Unable to open this book.</h1><p>{{ error }}</p><button type="button" @click="load">Try again</button></div>
    <div v-else class="reader-body" :class="{ 'sidebar-open': sidebar }">
      <aside v-if="sidebar">
        <h2>Contents</h2>
        <button v-for="chapter in metadata?.chapters" :key="chapter.id" type="button" :class="{ active: currentChapter?.id === chapter.id }" @click="go(chapter.page_start)"><span>{{ chapter.chapter_number }}</span>{{ chapter.title }}</button>
        <h2 v-if="bookmarks.length">Bookmarks</h2>
        <button v-for="item in bookmarks" :key="item.id" type="button" @click="go(item.page_number, true, offsetFrom(item.position_data))"><Bookmark :size="14" /> Position {{ item.page_number }}</button>
        <template v-if="metadata?.learning_available"><h2>Learning</h2><button type="button" @click="emit('navigate', `/learn/${editionId}`)"><GraduationCap :size="15" /> Practice chapters</button></template>
        <template v-if="currentChapter && metadata?.summary_chapter_ids.includes(currentChapter.id)"><h2>Summary</h2><button type="button" @click="loadSummary"><LoaderCircle v-if="summaryLoading" class="spin" :size="14" /><AlignLeft v-else :size="15" />{{ summary ? 'Close chapter summary' : 'Chapter summary' }}</button><p v-if="summaryError" class="summary-error">{{ summaryError }}</p><pre v-if="summary?.content" class="chapter-summary">{{ summary.content }}</pre></template>
      </aside>
      <section ref="stage" class="document-stage" @scroll.passive="handleScroll">
        <div class="reading-column" :style="{ fontSize: `${textSize}rem` }">
          <article v-for="item in formattedPages" :key="item.page_number" :ref="setPageElement" class="text-page" :data-page="item.page_number">
            <template v-for="(block, index) in item.blocks" :key="index">
              <h2 v-if="block.heading">{{ block.text }}</h2>
              <p v-else>{{ block.text }}</p>
            </template>
            <span v-for="marker in bookmarks.filter((saved) => saved.page_number === item.page_number)" :key="marker.id" class="bookmark-ribbon" :style="{ top: `${offsetFrom(marker.position_data) * 100}%` }" title="Reading marker"><BookmarkCheck :size="16" /></span>
            <span class="position-marker">{{ item.page_number }}</span>
          </article>
          <p v-if="!formattedPages.some((item) => item.blocks.length)" class="empty-text">This document does not contain extractable text.</p>
        </div>
      </section>
    </div>

    <footer v-if="metadata && !loading && !error" class="page-controls">
      <button type="button" aria-label="Previous position" :disabled="page <= 1" @click="go(page - 1)"><ChevronLeft :size="20" /></button>
      <label>Position <input :value="page" type="number" min="1" :max="metadata.page_count" @change="go(Number(($event.target as HTMLInputElement).value))" /> of {{ metadata.page_count }}</label>
      <button type="button" aria-label="Next position" :disabled="page >= metadata.page_count" @click="go(page + 1)"><ChevronRight :size="20" /></button>
      <button class="marker-button" type="button" @click="toggleBookmark"><BookmarkCheck v-if="bookmarked" :size="17" /><Bookmark v-else :size="17" />{{ bookmarked ? 'Remove marker' : 'Mark this spot' }}</button>
    </footer>
  </main>
</template>

<style scoped>
.chapter-summary { margin: 10px; white-space: pre-wrap; color: #c9d0cb; font: inherit; font-size: .76rem; line-height: 1.65; }.summary-error { margin: 10px; color: #e0a69c; font-size: .72rem; line-height: 1.45; }
.reader-shell { display: grid; grid-template-rows: 64px 1fr 58px; height: 100vh; overflow: hidden; background: #dfe3e0; color: #edf0ed; }.reader-toolbar { z-index: 4; display: grid; grid-template-columns: 44px minmax(0,1fr) auto; gap: 14px; align-items: center; padding: 0 18px; border-bottom: 1px solid #424744; background: #202422; }.reader-toolbar button,.page-controls button { display: grid; width: 38px; height: 38px; place-items: center; background: transparent; color: inherit; }.reader-toolbar > div { display: grid; min-width: 0; }.reader-toolbar strong,.reader-toolbar small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.reader-toolbar small { color: #aeb5b0; font-size: .68rem; }.reader-toolbar nav { display: flex; align-items: center; gap: 3px; }.reader-toolbar button:disabled,.page-controls button:disabled { opacity: .35; }.text-control { display: flex; width: 150px; align-items: center; gap: 8px; }.text-control input { width: 94px; accent-color: #d8e6dc; }.text-control span { width: 42px; color: #b9c0bb; text-align: right; font-size: .72rem; }.reader-body { display: grid; min-height: 0; grid-template-columns: 1fr; }.reader-body.sidebar-open { grid-template-columns: 250px minmax(0,1fr); }.reader-body aside { overflow-y: auto; padding: 26px 14px; border-right: 1px solid #424744; background: #202422; }.reader-body aside h2 { margin: 0 10px 15px; color: #8f9892; font-size: .68rem; text-transform: uppercase; }.reader-body aside h2:not(:first-child) { margin-top: 30px; }.reader-body aside button { display: flex; width: 100%; gap: 10px; align-items: center; padding: 11px 10px; background: transparent; color: #c6ccc8; text-align: left; font-size: .78rem; line-height: 1.35; }.reader-body aside button.active { background: #35433d; color: white; }.reader-body aside button span { color: #87918b; }.document-stage { min-width: 0; overflow: auto; scroll-behavior: smooth; background: #dfe3e0; }.reading-column { width: min(100%, 820px); min-height: 100%; margin: 0 auto; padding: 72px clamp(32px,8vw,96px) 110px; background: #fbfcfa; color: #202522; font-family: Georgia, "Times New Roman", serif; line-height: 1.85; }.text-page { position: relative; }.text-page p { margin: 0 0 1.15em; text-align: left; }.text-page h2 { margin: 2.4em 0 1em; color: #18201c; font-family: inherit; font-size: 1.3em; line-height: 1.35; text-align: center; letter-spacing: 0; }.text-page:first-child h2:first-child { margin-top: 0; }.position-marker { position: absolute; right: -54px; top: 0; color: #98a09b; font-family: ui-sans-serif, system-ui, sans-serif; font-size: .62rem; }.empty-text { padding: 20vh 0; color: #59615c; text-align: center; }.page-controls { display: flex; z-index: 4; justify-content: center; align-items: center; gap: 14px; border-top: 1px solid #424744; background: #202422; }.page-controls label { display: flex; align-items: center; gap: 7px; color: #b9c0bb; font-size: .75rem; }.page-controls input { width: 52px; height: 32px; border: 1px solid #59605b; background: #2b302d; color: white; text-align: center; }.reader-state { display: grid; grid-row: 2; place-content: center; justify-items: center; gap: 14px; padding: 30px; background: #272b29; text-align: center; }.reader-state h1 { margin: 0; }.reader-state p { color: #b8beb9; }.reader-state button { padding: 10px 16px; background: #edf0ed; color: #202422; }
.reading-progress { position: fixed; z-index: 7; top: 63px; left: 0; height: 2px; background: #9bc9ad; transition: width .15s linear; }.reader-shell.dark,.reader-shell.dark .document-stage { background: #171b19; }.reader-shell.dark .reading-column { background: #202522; color: #dce2dd; }.reader-shell.dark .text-page h2 { color: #f0f3f1; }.reader-shell.dark .position-marker { color: #747d77; }.reader-shell.dark .page-controls,.reader-shell.dark .reader-toolbar,.reader-shell.dark aside { background: #151917; }
.bookmark-ribbon { position: absolute; right: -76px; display: grid; width: 34px; height: 46px; place-items: center; background: #b94f45; color: white; clip-path: polygon(0 0,100% 0,100% 100%,50% 78%,0 100%); transform: translateY(-10px); filter: drop-shadow(0 3px 4px rgba(0,0,0,.2)); }.page-controls .marker-button { display: flex; width: auto; min-width: 142px; gap: 8px; padding: 0 13px; border-left: 1px solid #424744; color: #edf0ed; font-size: .72rem; }
@media (max-width: 760px) { .reader-shell { grid-template-rows: 58px 1fr 54px; }.reader-toolbar { grid-template-columns: 38px minmax(0,1fr) auto; padding: 0 8px; gap: 7px; }.reading-progress { top: 57px; }.text-control { display: none; }.reader-body.sidebar-open { grid-template-columns: minmax(0,1fr); }.reader-body aside { position: absolute; z-index: 5; top: 58px; bottom: 54px; width: min(82vw,280px); box-shadow: 12px 0 28px rgba(0,0,0,.3); }.reader-toolbar nav button:first-child { display: none; }.reading-column { padding: 48px 24px 80px; line-height: 1.75; }.position-marker { display: none; }.bookmark-ribbon { right: -18px; }.page-controls { gap: 4px; }.page-controls .marker-button { min-width: 42px; padding: 0 10px; font-size: 0; }.page-controls .marker-button svg { width: 18px; height: 18px; } }
</style>
