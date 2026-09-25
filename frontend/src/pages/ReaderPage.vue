<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { AlignLeft, ArrowLeft, Bookmark, BookmarkCheck, ChevronLeft, ChevronRight, GraduationCap, List, LoaderCircle, Minus, Plus, X } from "@lucide/vue";
import { getDocument, GlobalWorkerOptions, type PDFDocumentProxy } from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { api, apiBase, hasSession, type Reader, type ReaderBookmark, type ReadingProgress, type SummaryResponse } from "../api";
import { notify } from "../toast";

GlobalWorkerOptions.workerSrc = workerUrl;

const props = defineProps<{ editionId: string }>();
const emit = defineEmits<{ navigate: [path: string] }>();
const metadata = ref<Reader | null>(null);
const bookmarks = ref<ReaderBookmark[]>([]);
const page = ref(1);
const zoom = ref(1.1);
const loading = ref(true);
const rendering = ref(false);
const error = ref("");
const sidebar = ref(true);
const canvas = ref<HTMLCanvasElement | null>(null);
const summary = ref<SummaryResponse | null>(null);
const summaryLoading = ref(false);
const summaryError = ref("");
let pdf: PDFDocumentProxy | null = null;
let saveTimer: ReturnType<typeof setTimeout> | undefined;
let renderVersion = 0;

const currentChapter = computed(() => metadata.value?.chapters.find((item) => page.value >= item.page_start && page.value <= item.page_end) || null);
const bookmarked = computed(() => bookmarks.value.some((item) => item.page_number === page.value));

async function renderPage() {
  if (!pdf || !canvas.value) return;
  const version = ++renderVersion;
  rendering.value = true;
  try {
    const pdfPage = await pdf.getPage(page.value);
    const viewport = pdfPage.getViewport({ scale: zoom.value });
    const ratio = window.devicePixelRatio || 1;
    const target = canvas.value;
    target.width = Math.floor(viewport.width * ratio);
    target.height = Math.floor(viewport.height * ratio);
    target.style.width = `${viewport.width}px`;
    target.style.height = `${viewport.height}px`;
    const context = target.getContext("2d");
    if (context) await pdfPage.render({ canvasContext: context, viewport, transform: ratio === 1 ? undefined : [ratio, 0, 0, ratio, 0, 0] }).promise;
  } finally {
    if (version === renderVersion) rendering.value = false;
  }
}

function go(next: number) {
  if (!metadata.value) return;
  page.value = Math.min(metadata.value.page_count, Math.max(1, Math.round(next) || 1));
}

async function saveProgress() {
  if (!hasSession() || !metadata.value) return;
  await api(`/api/v1/reading-progress/${props.editionId}`, {
    method: "PUT",
    body: JSON.stringify({ current_page: page.value, chapter_id: currentChapter.value?.id || null }),
  }).catch(() => {});
}

function queueSave() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(saveProgress, 500);
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
  if (!hasSession()) {
    emit("navigate", `/login?redirect=${encodeURIComponent(`/read/${props.editionId}`)}`);
    return;
  }
  const existing = bookmarks.value.find((item) => item.page_number === page.value);
  try {
    if (existing) {
      await api(`/api/v1/bookmarks/${existing.id}`, { method: "DELETE" });
      bookmarks.value = bookmarks.value.filter((item) => item.id !== existing.id);
      notify("Bookmark removed.");
    } else {
      const created = await api<ReaderBookmark>("/api/v1/bookmarks", { method: "POST", body: JSON.stringify({ edition_id: props.editionId, chapter_id: currentChapter.value?.id || null, page_number: page.value }) });
      bookmarks.value.push(created);
      notify("Page bookmarked.");
    }
  } catch (caught) { notify(caught instanceof Error ? caught.message : "Unable to update bookmark.", "error"); }
}

async function load() {
  loading.value = true; error.value = "";
  try {
    metadata.value = await api<Reader>(`/api/v1/editions/${props.editionId}/reader`);
    if (hasSession()) {
      const [progress, saved] = await Promise.all([
        api<ReadingProgress | null>(`/api/v1/reading-progress/${props.editionId}`),
        api<ReaderBookmark[]>(`/api/v1/editions/${props.editionId}/bookmarks`),
      ]);
      page.value = progress?.current_page || 1;
      bookmarks.value = saved;
    }
    const token = sessionStorage.getItem("litera_access");
    pdf = await getDocument({ url: `${apiBase}/api/v1/digital-files/${metadata.value.digital_file_id}/content`, httpHeaders: token ? { Authorization: `Bearer ${token}` } : undefined }).promise;
    await nextTick();
    await renderPage();
  } catch (caught) { error.value = caught instanceof Error ? caught.message : "Unable to open this edition."; }
  finally { loading.value = false; }
}

watch(page, async () => { await renderPage(); queueSave(); });
watch(zoom, renderPage);
watch(() => currentChapter.value?.id, () => { summary.value = null; summaryError.value = ""; });
onMounted(load);
onBeforeUnmount(() => { clearTimeout(saveTimer); void saveProgress(); void pdf?.destroy(); });
</script>

<template>
  <main class="reader-shell">
    <header class="reader-toolbar">
      <button type="button" aria-label="Back to book" title="Back to book" @click="emit('navigate', metadata ? `/books/${metadata.book.slug}` : '/explore')"><ArrowLeft :size="19" /></button>
      <div><strong>{{ metadata?.book.title || 'Litera Reader' }}</strong><small>{{ currentChapter?.title || 'Digital edition' }}</small></div>
      <nav aria-label="Reader controls">
        <button type="button" aria-label="Zoom out" title="Zoom out" :disabled="zoom <= .7" @click="zoom = Math.max(.7, zoom - .15)"><Minus :size="18" /></button>
        <span>{{ Math.round(zoom * 100) }}%</span>
        <button type="button" aria-label="Zoom in" title="Zoom in" :disabled="zoom >= 2" @click="zoom = Math.min(2, zoom + .15)"><Plus :size="18" /></button>
        <button type="button" :aria-label="bookmarked ? 'Remove bookmark' : 'Bookmark page'" :title="bookmarked ? 'Remove bookmark' : 'Bookmark page'" @click="toggleBookmark"><BookmarkCheck v-if="bookmarked" :size="19" /><Bookmark v-else :size="19" /></button>
        <button type="button" aria-label="Toggle chapters" title="Chapters" @click="sidebar = !sidebar"><X v-if="sidebar" :size="19" /><List v-else :size="19" /></button>
      </nav>
    </header>

    <div v-if="loading" class="reader-state"><LoaderCircle class="spin" :size="28" /> Preparing your book</div>
    <div v-else-if="error" class="reader-state"><h1>Unable to open this book.</h1><p>{{ error }}</p><button type="button" @click="load">Try again</button></div>
    <div v-else class="reader-body" :class="{ 'sidebar-open': sidebar }">
      <aside v-if="sidebar">
        <h2>Contents</h2>
        <button v-for="chapter in metadata?.chapters" :key="chapter.id" type="button" :class="{ active: currentChapter?.id === chapter.id }" @click="go(chapter.page_start)"><span>{{ chapter.chapter_number }}</span>{{ chapter.title }}</button>
        <h2 v-if="bookmarks.length">Bookmarks</h2>
        <button v-for="item in bookmarks" :key="item.id" type="button" @click="go(item.page_number)"><Bookmark :size="14" /> Page {{ item.page_number }}</button>
        <template v-if="metadata?.learning_available"><h2>Learning</h2><button type="button" @click="emit('navigate', `/learn/${editionId}`)"><GraduationCap :size="15" /> Practice chapters</button></template>
        <template v-if="currentChapter && metadata?.summary_chapter_ids.includes(currentChapter.id)"><h2>Summary</h2><button type="button" @click="loadSummary"><LoaderCircle v-if="summaryLoading" class="spin" :size="14" /><AlignLeft v-else :size="15" />{{ summary ? 'Close chapter summary' : 'Chapter summary' }}</button><p v-if="summaryError" class="summary-error">{{ summaryError }}</p><pre v-if="summary?.content" class="chapter-summary">{{ summary.content }}</pre></template>
      </aside>
      <section class="document-stage">
        <div class="canvas-wrap"><canvas ref="canvas"></canvas><span v-if="rendering" class="rendering"><LoaderCircle class="spin" :size="22" /></span></div>
      </section>
    </div>

    <footer v-if="metadata && !loading && !error" class="page-controls">
      <button type="button" aria-label="Previous page" :disabled="page <= 1" @click="go(page - 1)"><ChevronLeft :size="20" /></button>
      <label>Page <input :value="page" type="number" min="1" :max="metadata.page_count" @change="go(Number(($event.target as HTMLInputElement).value))" /> of {{ metadata.page_count }}</label>
      <button type="button" aria-label="Next page" :disabled="page >= metadata.page_count" @click="go(page + 1)"><ChevronRight :size="20" /></button>
    </footer>
  </main>
</template>

<style scoped>
.chapter-summary { margin: 10px; white-space: pre-wrap; color: #c9d0cb; font: inherit; font-size: .76rem; line-height: 1.65; }.summary-error { margin: 10px; color: #e0a69c; font-size: .72rem; line-height: 1.45; }
.reader-shell { display: grid; grid-template-rows: 64px 1fr 58px; height: 100vh; overflow: hidden; background: #272b29; color: #edf0ed; }.reader-toolbar { z-index: 2; display: grid; grid-template-columns: 44px minmax(0,1fr) auto; gap: 14px; align-items: center; padding: 0 18px; border-bottom: 1px solid #424744; background: #202422; }.reader-toolbar button,.page-controls button { display: grid; width: 38px; height: 38px; place-items: center; background: transparent; color: inherit; }.reader-toolbar > div { display: grid; min-width: 0; }.reader-toolbar strong,.reader-toolbar small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.reader-toolbar small { color: #aeb5b0; font-size: .68rem; }.reader-toolbar nav { display: flex; align-items: center; gap: 3px; }.reader-toolbar nav span { width: 48px; color: #b9c0bb; text-align: center; font-size: .72rem; }.reader-toolbar button:disabled,.page-controls button:disabled { opacity: .35; }.reader-body { display: grid; min-height: 0; grid-template-columns: 1fr; }.reader-body.sidebar-open { grid-template-columns: 250px minmax(0,1fr); }.reader-body aside { overflow-y: auto; padding: 26px 14px; border-right: 1px solid #424744; background: #202422; }.reader-body aside h2 { margin: 0 10px 15px; color: #8f9892; font-size: .68rem; text-transform: uppercase; }.reader-body aside h2:not(:first-child) { margin-top: 30px; }.reader-body aside button { display: flex; width: 100%; gap: 10px; align-items: center; padding: 11px 10px; background: transparent; color: #c6ccc8; text-align: left; font-size: .78rem; line-height: 1.35; }.reader-body aside button.active { background: #35433d; color: white; }.reader-body aside button span { color: #87918b; }.document-stage { min-width: 0; overflow: auto; padding: 34px; }.canvas-wrap { position: relative; width: max-content; min-width: 100%; min-height: 100%; display: grid; align-content: start; justify-content: center; }.canvas-wrap canvas { display: block; background: white; box-shadow: 0 15px 40px rgba(0,0,0,.3); }.rendering { position: fixed; inset: 64px 0 58px; display: grid; place-items: center; pointer-events: none; background: rgba(32,36,34,.18); }.page-controls { display: flex; z-index: 2; justify-content: center; align-items: center; gap: 14px; border-top: 1px solid #424744; background: #202422; }.page-controls label { display: flex; align-items: center; gap: 7px; color: #b9c0bb; font-size: .75rem; }.page-controls input { width: 52px; height: 32px; border: 1px solid #59605b; background: #2b302d; color: white; text-align: center; }.reader-state { display: grid; grid-row: 2; place-content: center; justify-items: center; gap: 14px; padding: 30px; text-align: center; }.reader-state h1 { margin: 0; }.reader-state p { color: #b8beb9; }.reader-state button { padding: 10px 16px; background: #edf0ed; color: #202422; }
@media (max-width: 700px) { .reader-shell { grid-template-rows: 58px 1fr 54px; }.reader-toolbar { grid-template-columns: 38px minmax(0,1fr) auto; padding: 0 8px; gap: 7px; }.reader-toolbar nav span,.reader-toolbar nav button:nth-child(-n+3) { display: none; }.reader-body.sidebar-open { grid-template-columns: 210px minmax(100%,1fr); }.reader-body aside { position: absolute; z-index: 3; top: 58px; bottom: 54px; width: min(82vw,280px); box-shadow: 12px 0 28px rgba(0,0,0,.3); }.document-stage { padding: 18px; }.rendering { inset: 58px 0 54px; } }
</style>
