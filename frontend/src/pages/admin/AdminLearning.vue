<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { ArrowDown, ArrowLeft, ArrowUp, Check, ChevronRight, Eye, FileText, LoaderCircle, Pencil, Plus, RefreshCw, Sparkles, Trash2, X } from "@lucide/vue";
import { ApiError, api, formatEnum, type AdminQuiz, type Chapter, type QuizDifficulty, type SummaryResponse } from "../../api";
import { notify } from "../../toast";

type OptionDraft = { option_text: string; is_correct: boolean };
type QuestionDraft = { question: string; explanation: string; options: OptionDraft[] };
const props = defineProps<{ bookId: string; editionId: string }>();
const emit = defineEmits<{ navigate: [path: string] }>();
const chapters = ref<Chapter[]>([]);
const selected = ref<Chapter | null>(null);
const quizzes = ref<AdminQuiz[]>([]);
const editing = ref<AdminQuiz | null>(null);
const editorOpen = ref(false);
const previewing = ref(false);
const loading = ref(true);
const saving = ref(false);
const error = ref("");
const formError = ref("");
const chapterSummary = ref<SummaryResponse | null>(null);
const bookSummary = ref<SummaryResponse | null>(null);
const generating = ref<"book" | "chapter" | "">("");
const generatingQuiz = ref(false);
const aiDifficulty = ref<QuizDifficulty>("MEDIUM");
const aiQuestionCount = ref(5);
const aiError = ref("");
const form = ref<{ title: string; difficulty: QuizDifficulty; is_published: boolean; questions: QuestionDraft[] }>({ title: "Chapter Review", difficulty: "MEDIUM", is_published: false, questions: [] });

function blankQuestion(): QuestionDraft { return { question: "", explanation: "", options: [{ option_text: "", is_correct: true }, { option_text: "", is_correct: false }] }; }
async function loadChapters() {
  loading.value = true; error.value = "";
  try {
    chapters.value = await api<Chapter[]>(`/api/v1/admin/editions/${props.editionId}/chapters`);
    selected.value = chapters.value[0] || null;
    await Promise.all([loadBookSummary(), selected.value ? loadQuizzes() : Promise.resolve(), selected.value ? loadChapterSummary() : Promise.resolve()]);
  } catch (caught) { error.value = caught instanceof Error ? caught.message : "Unable to load chapters."; }
  finally { loading.value = false; }
}
async function loadQuizzes() { if (selected.value) quizzes.value = await api<AdminQuiz[]>(`/api/v1/admin/chapters/${selected.value.id}/quizzes`); }
async function selectChapter(chapter: Chapter) { selected.value = chapter; editing.value = null; await Promise.all([loadQuizzes(), loadChapterSummary()]); }
async function optionalSummary(path: string) { try { return await api<SummaryResponse>(path); } catch (caught) { if (caught instanceof ApiError && caught.status === 404) return null; throw caught; } }
async function loadBookSummary() { bookSummary.value = await optionalSummary("/api/v1/admin/editions/" + props.editionId + "/summary"); }
async function loadChapterSummary() { chapterSummary.value = selected.value ? await optionalSummary("/api/v1/admin/chapters/" + selected.value.id + "/summary") : null; }
async function generateSummary(kind: "book" | "chapter", regenerate = false) {
  if (kind === "chapter" && !selected.value) return;
  generating.value = kind;
  const target = kind === "book" ? "editions/" + props.editionId : "chapters/" + selected.value!.id;
  try {
    const suffix = regenerate ? "?regenerate=true" : "";
    const result = await api<SummaryResponse>("/api/v1/admin/" + target + "/summary/generate" + suffix, { method: "POST" });
    if (kind === "book") bookSummary.value = result; else chapterSummary.value = result;
    notify((kind === "book" ? "Book" : "Chapter") + " summary ready.");
  } catch (caught) {
    notify(caught instanceof Error ? caught.message : "Unable to generate summary.", "error");
    if (kind === "book") await loadBookSummary(); else await loadChapterSummary();
  } finally { generating.value = ""; }
}
async function generateQuiz(quiz?: AdminQuiz) {
  if (!selected.value || generatingQuiz.value) return;
  generatingQuiz.value = true; aiError.value = "";
  const path = quiz ? `/api/v1/admin/quizzes/${quiz.id}/regenerate` : `/api/v1/admin/chapters/${selected.value.id}/quiz/generate`;
  const payload = quiz
    ? { difficulty: quiz.difficulty, question_count: quiz.questions.length }
    : { difficulty: aiDifficulty.value, question_count: aiQuestionCount.value };
  try {
    const generated = await api<AdminQuiz>(path, { method: "POST", body: JSON.stringify(payload) });
    await loadQuizzes();
    openEditor(generated);
    notify("AI draft ready for review.");
  } catch (caught) { aiError.value = caught instanceof Error ? caught.message : "Unable to generate quiz."; }
  finally { generatingQuiz.value = false; }
}
function openEditor(quiz?: AdminQuiz) {
  editing.value = quiz || null; formError.value = ""; previewing.value = false; editorOpen.value = true;
  form.value = quiz ? {
    title: quiz.title, difficulty: quiz.difficulty, is_published: quiz.is_published,
    questions: quiz.questions.map((question) => ({ question: question.question, explanation: question.explanation || "", options: question.options.map((option) => ({ option_text: option.option_text, is_correct: option.is_correct })) })),
  } : { title: "Chapter Review", difficulty: "MEDIUM", is_published: false, questions: [blankQuestion()] };
}
function addOption(question: QuestionDraft) { question.options.push({ option_text: "", is_correct: false }); }
function setCorrect(question: QuestionDraft, index: number) { question.options.forEach((option, optionIndex) => { option.is_correct = optionIndex === index; }); }
function removeOption(question: QuestionDraft, index: number) { if (question.options.length > 2) question.options.splice(index, 1); }
function moveQuestion(from: number, to: number) {
  if (to < 0 || to >= form.value.questions.length) return;
  form.value.questions.splice(to, 0, ...form.value.questions.splice(from, 1));
}
async function save() {
  if (!selected.value) return; saving.value = true; formError.value = "";
  const payload = editing.value?.attempt_count ? { title: form.value.title, difficulty: form.value.difficulty, is_published: form.value.is_published } : { ...form.value, questions: form.value.questions.map((question) => ({ ...question, explanation: question.explanation.trim() || null })) };
  try {
    if (editing.value) await api(`/api/v1/admin/quizzes/${editing.value.id}`, { method: "PATCH", body: JSON.stringify(payload) });
    else await api(`/api/v1/admin/chapters/${selected.value.id}/quizzes`, { method: "POST", body: JSON.stringify(payload) });
    notify(editing.value ? "Quiz updated." : "Quiz created."); editorOpen.value = false; editing.value = null; await loadQuizzes();
  } catch (caught) { formError.value = caught instanceof Error ? caught.message : "Unable to save quiz."; }
  finally { saving.value = false; }
}
async function togglePublish(quiz: AdminQuiz) { try { await api(`/api/v1/admin/quizzes/${quiz.id}`, { method: "PATCH", body: JSON.stringify({ is_published: !quiz.is_published }) }); notify(quiz.is_published ? "Quiz unpublished." : "Quiz published."); await loadQuizzes(); } catch (caught) { notify(caught instanceof Error ? caught.message : "Unable to update quiz.", "error"); } }
async function removeQuiz(quiz: AdminQuiz) { if (!confirm(`Delete ${quiz.title}?`)) return; try { await api(`/api/v1/admin/quizzes/${quiz.id}`, { method: "DELETE" }); notify("Quiz deleted."); await loadQuizzes(); } catch (caught) { notify(caught instanceof Error ? caught.message : "Unable to delete quiz.", "error"); } }
watch(() => props.editionId, loadChapters); onMounted(loadChapters);
</script>

<template>
  <main class="admin-learning">
    <button class="back" type="button" @click="emit('navigate', `/admin/books/${bookId}`)"><ArrowLeft :size="17" /> Book details</button>
    <header><div><p class="eyebrow">Learning</p><h1>Chapter quizzes</h1><p>Build and publish focused practice for this edition.</p></div><button v-if="selected" type="button" @click="openEditor()"><Plus :size="17" /> New quiz</button></header>
    <div v-if="loading" class="admin-state"><LoaderCircle class="spin" :size="24" /> Loading chapters</div>
    <div v-else-if="error" class="admin-state"><p>{{ error }}</p><button type="button" @click="loadChapters">Try again</button></div>
    <div v-else-if="!chapters.length" class="admin-state"><h2>No chapters available.</h2><p>Upload and process a PDF first so Litera can create chapter structure.</p></div>
    <div v-else class="learning-workspace">
      <section class="summary-admin book-summary-admin">
        <div><p class="eyebrow">Edition summary</p><h2>Book summary</h2><p v-if="bookSummary?.status === 'READY'">Generated with {{ bookSummary.model }}<span v-if="bookSummary.is_stale"> / source changed</span></p><p v-else-if="bookSummary?.status === 'FAILED'">{{ bookSummary.error_message }}</p><p v-else>Not generated yet.</p></div>
        <pre v-if="bookSummary?.content">{{ bookSummary.content }}</pre>
        <button type="button" :disabled="generating === 'book'" @click="generateSummary('book', Boolean(bookSummary))"><RefreshCw v-if="bookSummary" :size="16" /><FileText v-else :size="16" />{{ generating === 'book' ? 'Generating...' : bookSummary ? 'Regenerate' : 'Generate summary' }}</button>
      </section>
      <aside><h2>Chapters</h2><button v-for="chapter in chapters" :key="chapter.id" type="button" :class="{ active: selected?.id === chapter.id }" @click="selectChapter(chapter)"><span>{{ String(chapter.chapter_number).padStart(2, '0') }}</span><strong>{{ chapter.title }}</strong><ChevronRight :size="15" /></button></aside>
      <section class="quiz-list"><div><p class="eyebrow">Chapter {{ selected?.chapter_number }}</p><h2>{{ selected?.title }}</h2></div><section class="summary-admin chapter-summary-admin"><div><p class="eyebrow">Chapter summary</p><p v-if="chapterSummary?.status === 'READY'">Generated with {{ chapterSummary.model }}<span v-if="chapterSummary.is_stale"> / source changed</span></p><p v-else-if="chapterSummary?.status === 'FAILED'">{{ chapterSummary.error_message }}</p><p v-else>Not generated yet.</p></div><pre v-if="chapterSummary?.content">{{ chapterSummary.content }}</pre><button type="button" :disabled="generating === 'chapter'" @click="generateSummary('chapter', Boolean(chapterSummary))"><RefreshCw v-if="chapterSummary" :size="16" /><FileText v-else :size="16" />{{ generating === 'chapter' ? 'Generating...' : chapterSummary ? 'Regenerate' : 'Generate summary' }}</button></section><section class="ai-quiz-generator"><div><p class="eyebrow">AI draft</p><h3>Generate from chapter</h3><p v-if="generatingQuiz">Using this chapter's content to create {{ aiQuestionCount }} practice questions.</p><p v-else>Creates an unpublished draft for review in the existing editor.</p></div><label>Difficulty<select v-model="aiDifficulty"><option value="EASY">Easy</option><option value="MEDIUM">Medium</option><option value="HARD">Hard</option></select></label><label>Questions<input v-model.number="aiQuestionCount" type="number" min="3" max="20" /></label><button type="button" :disabled="generatingQuiz || !Number.isInteger(aiQuestionCount) || aiQuestionCount < 3 || aiQuestionCount > 20" @click="generateQuiz()"><LoaderCircle v-if="generatingQuiz" class="spin" :size="16" /><Sparkles v-else :size="16" />{{ generatingQuiz ? 'Generating quiz...' : 'Generate draft' }}</button><p v-if="aiError" class="ai-error">{{ aiError }}</p></section><p v-if="!quizzes.length" class="empty">No quizzes for this chapter.</p><article v-for="quiz in quizzes" :key="quiz.id"><div><span :class="{ published: quiz.is_published }">{{ quiz.is_published ? 'Published' : 'Draft' }}</span><h3>{{ quiz.title }}</h3><p>{{ formatEnum(quiz.difficulty) }} / {{ quiz.questions.length }} questions / {{ quiz.attempt_count }} attempts<span v-if="quiz.generated_by === 'AI'"> / Generated with AI / {{ quiz.ai_model }}</span></p></div><div><button type="button" :title="quiz.is_published ? 'Unpublish' : 'Publish'" :aria-label="quiz.is_published ? 'Unpublish quiz' : 'Publish quiz'" @click="togglePublish(quiz)"><Check :size="16" /></button><button v-if="quiz.generated_by === 'AI' && !quiz.is_published" type="button" title="Regenerate AI draft" aria-label="Regenerate AI draft" :disabled="generatingQuiz" @click="generateQuiz(quiz)"><RefreshCw :size="16" /></button><button type="button" aria-label="Edit quiz" @click="openEditor(quiz)"><Pencil :size="16" /></button><button v-if="!quiz.attempt_count" type="button" aria-label="Delete quiz" @click="removeQuiz(quiz)"><Trash2 :size="16" /></button></div></article></section>
    </div>

    <Teleport to="body"><div v-if="editorOpen" class="editor-backdrop" @click.self="editorOpen = false"><section class="quiz-editor" role="dialog" aria-modal="true"><header><div><p class="eyebrow">Chapter {{ selected?.chapter_number }}</p><h2>{{ editing ? 'Edit quiz' : 'New quiz' }}</h2></div><div class="editor-actions"><button type="button" :aria-label="previewing ? 'Edit quiz' : 'Preview quiz'" :title="previewing ? 'Edit' : 'Preview'" @click="previewing = !previewing"><Pencil v-if="previewing" :size="18" /><Eye v-else :size="18" /></button><button type="button" aria-label="Close editor" @click="editorOpen = false"><X :size="20" /></button></div></header><p v-if="editing?.generated_by === 'AI'" class="ai-draft-notice"><Sparkles :size="17" /><span><strong>AI-generated draft</strong>Review every question, answer, and explanation before publishing. Model: {{ editing.ai_model }}</span></p><form @submit.prevent="save"><div class="editor-meta"><label>Quiz title<input v-model="form.title" required maxlength="500" /></label><label>Difficulty<select v-model="form.difficulty"><option value="EASY">Easy</option><option value="MEDIUM">Medium</option><option value="HARD">Hard</option></select></label><label class="publish-toggle"><input v-model="form.is_published" type="checkbox" /><span><strong>Published</strong><small>Visible to active members</small></span></label></div><p v-if="editing?.attempt_count" class="locked-note">This quiz has attempt history. Questions are locked, but title, difficulty, and publication can still change.</p><div v-if="previewing" class="quiz-preview"><p class="eyebrow">Member preview / {{ form.difficulty }}</p><h3>{{ form.title || 'Untitled quiz' }}</h3><article v-for="(question, questionIndex) in form.questions" :key="questionIndex"><span>Question {{ questionIndex + 1 }}</span><h4>{{ question.question || 'Untitled question' }}</h4><p v-for="(option, optionIndex) in question.options" :key="optionIndex"><i>{{ String.fromCharCode(65 + optionIndex) }}</i>{{ option.option_text || `Option ${optionIndex + 1}` }}</p></article></div><div v-else class="question-editor"><article v-for="(question, questionIndex) in form.questions" :key="questionIndex"><header><span>Question {{ questionIndex + 1 }}</span><div v-if="!editing?.attempt_count"><button type="button" :disabled="questionIndex === 0" aria-label="Move question up" @click="moveQuestion(questionIndex, questionIndex - 1)"><ArrowUp :size="15" /></button><button type="button" :disabled="questionIndex === form.questions.length - 1" aria-label="Move question down" @click="moveQuestion(questionIndex, questionIndex + 1)"><ArrowDown :size="15" /></button><button v-if="form.questions.length > 1" type="button" aria-label="Remove question" @click="form.questions.splice(questionIndex, 1)"><Trash2 :size="16" /></button></div></header><label>Question<textarea v-model="question.question" required :disabled="Boolean(editing?.attempt_count)" rows="3"></textarea></label><div class="option-editor"><label v-for="(option, optionIndex) in question.options" :key="optionIndex"><input type="radio" :name="`correct-${questionIndex}`" :checked="option.is_correct" :disabled="Boolean(editing?.attempt_count)" :aria-label="`Mark option ${optionIndex + 1} correct`" @change="setCorrect(question, optionIndex)" /><span>{{ String.fromCharCode(65 + optionIndex) }}</span><input v-model="option.option_text" required :disabled="Boolean(editing?.attempt_count)" :placeholder="`Option ${optionIndex + 1}`" /><button v-if="!editing?.attempt_count && question.options.length > 2" type="button" aria-label="Remove option" @click="removeOption(question, optionIndex)"><X :size="15" /></button></label><button v-if="!editing?.attempt_count" type="button" @click="addOption(question)"><Plus :size="15" /> Add option</button></div><label>Explanation<textarea v-model="question.explanation" :disabled="Boolean(editing?.attempt_count)" rows="3" placeholder="Explain why the correct answer is right"></textarea></label></article><button v-if="!editing?.attempt_count" class="add-question" type="button" @click="form.questions.push(blankQuestion())"><Plus :size="16" /> Add question</button></div><p v-if="formError" class="form-error">{{ formError }}</p><footer><button type="button" @click="editorOpen = false">Cancel</button><button type="submit" :disabled="saving">{{ saving ? 'Saving...' : form.is_published ? 'Save and publish' : 'Save draft' }}</button></footer></form></section></div></Teleport>
  </main>
</template>

<style scoped>
.admin-learning { padding: 52px clamp(28px,5vw,75px) 110px; }.back { display: inline-flex; gap: 8px; align-items: center; padding: 7px 0; background: transparent; color: #69716b; }.admin-learning > header { display: flex; justify-content: space-between; gap: 30px; align-items: end; padding: 45px 0 55px; }.admin-learning h1 { margin: 0; font-size: clamp(2.8rem,5vw,5rem); font-weight: 560; }.admin-learning > header p:last-child { color: #6f7771; }.admin-learning > header button { display: flex; gap: 8px; align-items: center; min-height: 42px; padding: 0 14px; background: #173d32; color: white; }.learning-workspace { display: grid; grid-template-columns: 280px 1fr; border-top: 1px solid #ccd2cd; }.learning-workspace aside { padding: 28px 22px 28px 0; border-right: 1px solid #ccd2cd; }.learning-workspace aside h2 { margin: 0 10px 18px; font-size: .72rem; text-transform: uppercase; }.learning-workspace aside button { display: grid; grid-template-columns: 28px 1fr 18px; gap: 8px; align-items: center; width: 100%; padding: 13px 10px; background: transparent; text-align: left; }.learning-workspace aside button.active { background: #e2e9e4; }.learning-workspace aside span { color: #8b928d; font-size: .65rem; }.quiz-list { padding: 30px 0 30px 40px; }.quiz-list > div h2 { margin: 0 0 30px; font-size: 2rem; }.quiz-list .empty { padding: 45px 0; border-block: 1px solid #d4d8d4; color: #767d78; }.quiz-list article { display: flex; justify-content: space-between; gap: 20px; align-items: center; padding: 22px 0; border-top: 1px solid #d4d8d4; }.quiz-list article h3 { margin: 8px 0; }.quiz-list article p { margin: 0; color: #777f79; font-size: .76rem; }.quiz-list article span { padding: 5px 7px; background: #e4e6e3; color: #6b726d; font-size: .62rem; text-transform: uppercase; }.quiz-list article span.published { background: #d9e9df; color: #315f4b; }.quiz-list article > div:last-child { display: flex; }.quiz-list article button { display: grid; width: 37px; height: 37px; place-items: center; background: transparent; }.admin-state { display: grid; min-height: 350px; place-content: center; justify-items: center; gap: 12px; color: #707772; text-align: center; }
.summary-admin { display: grid; grid-template-columns: minmax(180px,.45fr) 1fr auto; gap: 24px; align-items: start; padding: 26px; border: 1px solid #cbd1cc; background: #edf1ed; }.book-summary-admin { grid-column: 1 / -1; margin: 28px 0; }.chapter-summary-admin { margin-bottom: 30px; }.summary-admin h2 { margin: 0; font-size: 1.45rem; }.summary-admin p { margin: 7px 0 0; color: #6d756f; font-size: .75rem; }.summary-admin pre { max-height: 280px; overflow: auto; margin: 0; white-space: pre-wrap; font: inherit; font-size: .82rem; line-height: 1.65; }.summary-admin > button { display: inline-flex; gap: 7px; align-items: center; padding: 9px 11px; border: 1px solid #aeb7b0; background: transparent; white-space: nowrap; }.summary-admin > button:disabled { opacity: .5; }
.ai-quiz-generator { display: grid; grid-template-columns: minmax(210px,1fr) 130px 100px auto; gap: 14px; align-items: end; margin-bottom: 30px; padding: 22px; border: 1px solid #bdc9c1; background: #e8eee9; }.ai-quiz-generator h3 { margin: 2px 0 0; }.ai-quiz-generator p { margin: 5px 0 0; color: #68716b; font-size: .74rem; }.ai-quiz-generator label { display: grid; gap: 6px; color: #5f6862; font-size: .7rem; font-weight: 650; }.ai-quiz-generator select,.ai-quiz-generator input { width: 100%; min-height: 40px; padding: 8px; border: 1px solid #adb8b0; background: white; }.ai-quiz-generator button { display: inline-flex; min-height: 40px; gap: 7px; align-items: center; padding: 0 12px; background: #173d32; color: white; white-space: nowrap; }.ai-quiz-generator button:disabled { opacity: .5; }.ai-quiz-generator .ai-error { grid-column: 1 / -1; color: #a14539; }.ai-draft-notice { display: flex; gap: 10px; align-items: start; padding: 13px; background: #e6eee8; color: #536159; font-size: .76rem; }.ai-draft-notice span { display: grid; gap: 3px; }
.editor-backdrop { position: fixed; z-index: 80; inset: 0; overflow-y: auto; padding: 30px; background: rgba(20,26,22,.55); }.quiz-editor { width: min(820px,100%); margin: auto; padding: 32px; background: #f7f8f5; }.quiz-editor > header { display: flex; justify-content: space-between; margin-bottom: 28px; }.quiz-editor h2 { margin: 0; font-size: 2rem; }.quiz-editor header button { display: grid; width: 35px; height: 35px; place-items: center; background: transparent; }.editor-actions,.question-editor article > header > div { display: flex; }.editor-meta { display: grid; grid-template-columns: 1.3fr .7fr 1fr; gap: 16px; }.quiz-editor label { display: grid; gap: 7px; color: #59615b; font-size: .72rem; font-weight: 650; }.quiz-editor input,.quiz-editor select,.quiz-editor textarea { width: 100%; padding: 10px; border: 1px solid #b9c1bb; background: white; color: #18221d; resize: vertical; }.quiz-editor input,.quiz-editor select { min-height: 42px; }.publish-toggle { display: flex !important; grid-template-columns: 18px 1fr; align-items: center; }.publish-toggle input { width: 16px; min-height: 16px; }.publish-toggle span { display: grid; gap: 3px; }.publish-toggle small { color: #7a827c; font-weight: 400; }.locked-note { padding: 13px; background: #e8eae7; color: #626a64; font-size: .78rem; }.question-editor { display: grid; gap: 18px; margin-top: 30px; }.question-editor > article { padding: 22px; border: 1px solid #ccd2cd; }.question-editor article > header { display: flex; justify-content: space-between; margin-bottom: 16px; color: #737b75; font-size: .68rem; text-transform: uppercase; }.question-editor article > header button:disabled { opacity: .25; }.option-editor { display: grid; gap: 8px; margin: 15px 0; }.option-editor > label { display: grid; grid-template-columns: 18px 25px 1fr 32px; align-items: center; gap: 8px; }.option-editor > label > input[type=radio] { width: 16px; min-height: 16px; }.option-editor > label > span { text-align: center; }.option-editor button,.add-question { display: inline-flex; gap: 7px; align-items: center; width: max-content; padding: 7px 0; background: transparent; color: #315e4b; }.option-editor > label button { display: grid; width: 30px; height: 30px; place-items: center; }.quiz-preview { margin-top: 30px; padding: 28px; border: 1px solid #ccd2cd; }.quiz-preview > h3 { margin: 5px 0 30px; font-size: 2rem; }.quiz-preview article { padding: 25px 0; border-top: 1px solid #d3d8d4; }.quiz-preview article > span { color: #7a817c; font-size: .68rem; }.quiz-preview h4 { margin: 8px 0 20px; font-size: 1.2rem; }.quiz-preview article p { display: flex; gap: 12px; align-items: center; margin: 8px 0; }.quiz-preview article i { display: grid; width: 28px; height: 28px; place-items: center; border: 1px solid #bcc4be; border-radius: 50%; font-style: normal; font-size: .7rem; }.quiz-editor .form-error { color: #a14539; }.quiz-editor form > footer { display: flex; justify-content: flex-end; gap: 9px; margin-top: 28px; }.quiz-editor form > footer button { min-height: 42px; padding: 0 15px; border: 1px solid #b7beb8; background: transparent; }.quiz-editor form > footer button:last-child { background: #173d32; color: white; }
@media (max-width: 760px) { .admin-learning { padding: 70px 22px; }.admin-learning > header { display: block; }.admin-learning > header button { margin-top: 22px; }.learning-workspace { grid-template-columns: 1fr; }.learning-workspace aside { border-right: 0; border-bottom: 1px solid #ccd2cd; }.quiz-list { padding-left: 0; }.summary-admin,.ai-quiz-generator { grid-template-columns: 1fr; }.editor-backdrop { padding: 12px; }.quiz-editor { padding: 22px; }.editor-meta { grid-template-columns: 1fr; }.option-editor > label { grid-template-columns: 18px 22px 1fr 28px; } }
</style>
