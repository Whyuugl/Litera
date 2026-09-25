<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { AlignLeft, ArrowLeft, ArrowRight, BookOpen, Check, LoaderCircle, LockKeyhole } from "@lucide/vue";
import { ApiError, api, type LearningProgress, type SummaryResponse } from "../api";

const props = defineProps<{ editionId: string }>();
const emit = defineEmits<{ navigate: [path: string] }>();
const progress = ref<LearningProgress | null>(null);
const loading = ref(true);
const memberRequired = ref(false);
const error = ref("");
const bookSummary = ref<SummaryResponse | null>(null);
const chapterSummary = ref<SummaryResponse | null>(null);
const summaryLoading = ref("");

async function openChapterSummary(chapterId: string) {
  if (chapterSummary.value?.chapter_id === chapterId) { chapterSummary.value = null; return; }
  summaryLoading.value = chapterId;
  try { chapterSummary.value = await api<SummaryResponse>("/api/v1/chapters/" + chapterId + "/summary"); }
  catch { chapterSummary.value = null; }
  finally { summaryLoading.value = ""; }
}

async function load() {
  loading.value = true; error.value = ""; memberRequired.value = false;
  try {
    progress.value = await api<LearningProgress>("/api/v1/learning/editions/" + props.editionId + "/progress");
    bookSummary.value = progress.value.book_summary_available ? await api<SummaryResponse>("/api/v1/editions/" + props.editionId + "/summary") : null;
  }
  catch (caught) {
    if (caught instanceof ApiError && caught.status === 403) memberRequired.value = true;
    else error.value = caught instanceof Error ? caught.message : "Unable to load Learning Mode.";
  } finally { loading.value = false; }
}
watch(() => props.editionId, load); onMounted(load);
</script>

<template>
  <main class="learning-page">
    <button class="back" type="button" @click="emit('navigate', progress ? `/books/${progress.book.slug}` : '/library')"><ArrowLeft :size="17" /> Back</button>
    <section v-if="loading" class="learning-state"><LoaderCircle class="spin" :size="26" /> Loading Learning Mode</section>
    <section v-else-if="memberRequired" class="learning-state"><LockKeyhole :size="36" /><p class="eyebrow">Membership benefit</p><h1>Learning Mode is for active members.</h1><p>Become a member to practice chapter quizzes and keep your learning history.</p><button type="button" @click="emit('navigate', '/membership')">View membership <ArrowRight :size="17" /></button></section>
    <section v-else-if="error" class="learning-state"><h1>Learning Mode is unavailable.</h1><p>{{ error }}</p><button type="button" @click="load">Try again</button></section>
    <template v-else-if="progress">
      <header class="learning-heading"><div><p class="eyebrow">Learning Mode</p><h1>{{ progress.book.title }}</h1></div><dl><div><dt>Read</dt><dd>{{ progress.chapters_read }} / {{ progress.chapters_total }}</dd></div><div><dt>Quizzes</dt><dd>{{ progress.quizzes_completed }} / {{ progress.quizzes_available }}</dd></div><div><dt>Average</dt><dd>{{ progress.average_score === null ? '-' : `${Math.round(progress.average_score)}%` }}</dd></div></dl></header>
      <section v-if="bookSummary?.content" class="learning-summary"><p class="eyebrow">Book summary</p><pre>{{ bookSummary.content }}</pre><small>Generated from this book / {{ bookSummary.model }}</small></section>
      <section v-if="progress.chapters.some(chapter => chapter.summary_available)" class="summary-picker"><div><p class="eyebrow">Chapter summaries</p><h2>Review before you practice.</h2></div><nav><button v-for="chapter in progress.chapters.filter(item => item.summary_available)" :key="chapter.id" type="button" :class="{ active: chapterSummary?.chapter_id === chapter.id }" @click="openChapterSummary(chapter.id)"><LoaderCircle v-if="summaryLoading === chapter.id" class="spin" :size="14" /><AlignLeft v-else :size="15" />{{ chapter.title }}</button></nav><pre v-if="chapterSummary?.content">{{ chapterSummary.content }}</pre></section>
      <section class="chapter-list">
        <article v-for="chapter in progress.chapters" :key="chapter.id">
          <span class="chapter-number">{{ String(chapter.chapter_number).padStart(2, '0') }}</span>
          <div><h2>{{ chapter.title }}</h2><p><Check v-if="chapter.is_read" :size="14" />{{ chapter.is_read ? 'Read' : `Pages ${chapter.page_start}-${chapter.page_end}` }}</p></div>
          <div class="chapter-action"><template v-if="chapter.quizzes.length"><strong v-if="chapter.best_score !== null">Best {{ Math.round(chapter.best_score) }}%</strong><span v-else>Quiz available</span><button type="button" @click="emit('navigate', `/quiz/${chapter.quizzes[0].id}`)">{{ chapter.best_score === null ? 'Practice' : 'Retake' }} <ArrowRight :size="16" /></button></template><span v-else>No quiz yet</span></div>
        </article>
      </section>
    </template>
  </main>
</template>

<style scoped>
.learning-summary,.summary-picker { margin-bottom: 55px; padding: 30px; border-block: 1px solid #cbd0cb; }.learning-summary pre,.summary-picker pre { margin: 18px 0; white-space: pre-wrap; font: inherit; line-height: 1.75; }.learning-summary small { color: #747b76; }.summary-picker { display: grid; grid-template-columns: 220px 1fr; gap: 30px; }.summary-picker h2 { margin: 5px 0; font-size: 1.45rem; }.summary-picker nav { display: flex; flex-wrap: wrap; gap: 7px; }.summary-picker button { display: inline-flex; gap: 7px; align-items: center; padding: 9px 11px; border: 1px solid #bbc2bc; background: transparent; }.summary-picker button.active { background: #173d32; color: white; }.summary-picker pre { grid-column: 2; }
.learning-page { width: min(1120px,88vw); min-height: 80vh; margin: auto; padding: 55px 0 130px; }.back { display: inline-flex; align-items: center; gap: 8px; padding: 8px 0; background: transparent; color: #68706a; }.learning-heading { display: grid; grid-template-columns: 1fr auto; gap: 55px; align-items: end; padding: 65px 0 70px; }.learning-heading h1 { max-width: 700px; margin: 0; font-size: clamp(3rem,6vw,6rem); font-weight: 560; line-height: .95; }.learning-heading dl { display: flex; margin: 0; border-block: 1px solid #cbd0cb; }.learning-heading dl div { min-width: 105px; padding: 15px; border-right: 1px solid #cbd0cb; }.learning-heading dt { color: #7a817c; font-size: .65rem; text-transform: uppercase; }.learning-heading dd { margin: 6px 0 0; font-size: 1.25rem; }.chapter-list { border-bottom: 1px solid #cbd0cb; }.chapter-list article { display: grid; grid-template-columns: 65px 1fr 210px; gap: 25px; align-items: center; min-height: 135px; border-top: 1px solid #cbd0cb; }.chapter-number { color: #8c938e; font-size: .75rem; }.chapter-list h2 { margin: 0 0 9px; font-size: 1.35rem; }.chapter-list p { display: flex; gap: 6px; align-items: center; margin: 0; color: #737b75; font-size: .76rem; }.chapter-action { display: grid; justify-items: end; gap: 7px; color: #717973; font-size: .75rem; }.chapter-action strong { color: #2e604c; }.chapter-action button,.learning-state button { display: inline-flex; gap: 8px; align-items: center; padding: 8px 0; border-bottom: 1px solid; background: transparent; color: #173d32; }.learning-state { display: grid; min-height: 65vh; place-content: center; justify-items: center; gap: 13px; text-align: center; }.learning-state h1 { max-width: 700px; margin: 5px 0; font-size: clamp(2.4rem,5vw,4.5rem); font-weight: 560; }.learning-state > p:not(.eyebrow) { max-width: 520px; color: #707772; line-height: 1.7; }
@media (max-width: 720px) { .learning-page { width: calc(100% - 44px); padding-top: 30px; }.learning-heading { grid-template-columns: 1fr; padding: 45px 0; }.learning-heading dl { overflow-x: auto; }.chapter-list article { grid-template-columns: 38px 1fr; padding: 24px 0; }.chapter-action { grid-column: 2; justify-items: start; } }
@media (max-width: 720px) { .summary-picker { grid-template-columns: 1fr; }.summary-picker pre { grid-column: 1; } }
</style>
