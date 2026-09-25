<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { ArrowLeft, ArrowRight, Check, ChevronLeft, ChevronRight, LoaderCircle, RotateCcw, X } from "@lucide/vue";
import { api, type AttemptResult, type AttemptStarted, type AttemptSummary } from "../api";
import { notify } from "../toast";

const props = defineProps<{ quizId: string }>();
const emit = defineEmits<{ navigate: [path: string] }>();
const attempt = ref<AttemptStarted | null>(null);
const result = ref<AttemptResult | null>(null);
const history = ref<AttemptSummary[]>([]);
const answers = ref<Record<string, string>>({});
const index = ref(0);
const loading = ref(true);
const saving = ref(false);
const error = ref("");
const question = computed(() => attempt.value?.quiz.questions[index.value] || null);
const answered = computed(() => Object.keys(answers.value).length);

async function start() {
  loading.value = true; error.value = ""; result.value = null; answers.value = {}; index.value = 0;
  try { attempt.value = await api<AttemptStarted>(`/api/v1/quizzes/${props.quizId}/attempts`, { method: "POST" }); }
  catch (caught) { error.value = caught instanceof Error ? caught.message : "Unable to start this quiz."; }
  finally { loading.value = false; }
}

async function choose(optionId: string) {
  if (!attempt.value || !question.value || saving.value) return;
  const previous = answers.value[question.value.id];
  answers.value = { ...answers.value, [question.value.id]: optionId };
  saving.value = true;
  try {
    await api(`/api/v1/quiz-attempts/${attempt.value.id}/answers/${question.value.id}`, { method: "PUT", body: JSON.stringify({ selected_option_id: optionId }) });
  } catch (caught) {
    if (previous) answers.value = { ...answers.value, [question.value.id]: previous };
    else { const next = { ...answers.value }; delete next[question.value.id]; answers.value = next; }
    notify(caught instanceof Error ? caught.message : "Unable to save answer.", "error");
  } finally { saving.value = false; }
}

async function submit() {
  if (!attempt.value) return;
  if (answered.value !== attempt.value.quiz.questions.length) {
    notify(`Answer all ${attempt.value.quiz.questions.length} questions before submitting.`, "error");
    const missing = attempt.value.quiz.questions.findIndex((item) => !answers.value[item.id]);
    if (missing >= 0) index.value = missing;
    return;
  }
  saving.value = true;
  try {
    result.value = await api<AttemptResult>(`/api/v1/quiz-attempts/${attempt.value.id}/submit`, { method: "POST" });
    history.value = await api<AttemptSummary[]>(`/api/v1/quizzes/${props.quizId}/attempts/me`);
    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch (caught) { notify(caught instanceof Error ? caught.message : "Unable to submit quiz.", "error"); }
  finally { saving.value = false; }
}

watch(() => props.quizId, start); onMounted(start);
</script>

<template>
  <main class="quiz-page">
    <header class="quiz-top"><button type="button" aria-label="Back to Learning Mode" @click="emit('navigate', attempt ? `/learn/${attempt.quiz.edition_id}` : '/library')"><ArrowLeft :size="19" /></button><strong>Litera Learning</strong><span v-if="attempt && !result">{{ answered }} of {{ attempt.quiz.questions.length }} answered</span></header>
    <section v-if="loading" class="quiz-state"><LoaderCircle class="spin" :size="27" /> Preparing quiz</section>
    <section v-else-if="error" class="quiz-state"><h1>Quiz unavailable.</h1><p>{{ error }}</p><button type="button" @click="start">Try again</button></section>

    <section v-else-if="attempt && !result && question" class="question-stage">
      <div class="question-progress"><i :style="{ width: `${((index + 1) / attempt.quiz.questions.length) * 100}%` }"></i></div>
      <p class="eyebrow">{{ attempt.quiz.title }} / {{ attempt.quiz.difficulty }}</p>
      <span class="question-count">Question {{ index + 1 }} of {{ attempt.quiz.questions.length }}</span>
      <h1>{{ question.question }}</h1>
      <fieldset :disabled="saving"><legend class="sr-only">Choose one answer</legend><label v-for="(option, optionIndex) in question.options" :key="option.id" :class="{ selected: answers[question.id] === option.id }"><input type="radio" :name="question.id" :checked="answers[question.id] === option.id" @change="choose(option.id)" /><span>{{ String.fromCharCode(65 + optionIndex) }}</span><strong>{{ option.option_text }}</strong></label></fieldset>
      <footer><button type="button" :disabled="index === 0" @click="index--"><ChevronLeft :size="18" /> Previous</button><button v-if="index < attempt.quiz.questions.length - 1" type="button" @click="index++">Next <ChevronRight :size="18" /></button><button v-else class="submit" type="button" :disabled="saving" @click="submit">{{ saving ? 'Submitting...' : 'Submit Quiz' }} <ArrowRight v-if="!saving" :size="18" /></button></footer>
      <nav aria-label="Questions"><button v-for="(_, number) in attempt.quiz.questions" :key="number" type="button" :class="{ active: index === number, answered: answers[attempt.quiz.questions[number].id] }" :aria-label="`Question ${number + 1}`" @click="index = number">{{ number + 1 }}</button></nav>
    </section>

    <section v-else-if="result" class="results">
      <header><p class="eyebrow">Quiz complete</p><div class="score"><strong>{{ Math.round(result.score || 0) }}%</strong><span>{{ result.correct_answers }} / {{ result.total_questions }} correct</span></div><h1>{{ (result.score || 0) >= 80 ? 'Nice work.' : (result.score || 0) >= 60 ? 'Good progress.' : 'Keep exploring.' }}</h1><div><button type="button" @click="start"><RotateCcw :size="17" /> Retake</button><button type="button" @click="emit('navigate', `/learn/${result.quiz.edition_id}`)">Back to learning <ArrowRight :size="17" /></button></div></header>
      <div class="review"><h2>Review your answers</h2><article v-for="(item, reviewIndex) in result.review" :key="item.question_id" :class="{ correct: item.is_correct }"><span>{{ String(reviewIndex + 1).padStart(2, '0') }}</span><div><h3>{{ item.question }}</h3><dl><div><dt>Your answer</dt><dd><Check v-if="item.is_correct" :size="16" /><X v-else :size="16" />{{ item.selected_answer }}</dd></div><div v-if="!item.is_correct"><dt>Correct answer</dt><dd><Check :size="16" />{{ item.correct_answer }}</dd></div></dl><section v-if="item.explanation"><strong>Why?</strong><p>{{ item.explanation }}</p></section></div></article></div>
      <footer v-if="history.length"><span>{{ history.filter(item => item.completed_at).length }} completed attempt{{ history.filter(item => item.completed_at).length === 1 ? '' : 's' }}</span><strong>Best {{ Math.round(Math.max(...history.map(item => item.score || 0))) }}%</strong></footer>
    </section>
  </main>
</template>

<style scoped>
.quiz-page { min-height: 100vh; background: #f3f5f1; color: #18221d; }.quiz-top { display: grid; grid-template-columns: 44px 1fr auto; gap: 14px; align-items: center; height: 66px; padding: 0 max(20px,4vw); border-bottom: 1px solid #d2d7d2; }.quiz-top button { display: grid; width: 38px; height: 38px; place-items: center; background: transparent; }.quiz-top span { color: #737b75; font-size: .72rem; }.quiz-state { display: grid; min-height: calc(100vh - 66px); place-content: center; justify-items: center; gap: 15px; text-align: center; }.quiz-state h1 { margin: 0; font-size: 3rem; }.quiz-state p { color: #707772; }.quiz-state button { padding: 10px 15px; background: #173d32; color: white; }.question-stage { width: min(820px,calc(100% - 44px)); margin: auto; padding: 70px 0 110px; }.question-progress { height: 3px; margin-bottom: 55px; background: #d9ddd9; }.question-progress i { display: block; height: 100%; background: #316850; transition: width .25s; }.question-count { display: block; margin: 22px 0 14px; color: #777f79; font-size: .75rem; }.question-stage h1 { max-width: 790px; margin: 0 0 45px; font-size: clamp(2rem,4vw,3.8rem); font-weight: 560; line-height: 1.15; }.question-stage fieldset { display: grid; gap: 10px; padding: 0; border: 0; }.question-stage label { display: grid; grid-template-columns: 34px 1fr; gap: 15px; align-items: center; min-height: 65px; padding: 12px 18px; border: 1px solid #c7cdc8; cursor: pointer; }.question-stage label:hover,.question-stage label.selected { border-color: #2e6650; background: #e4ece7; }.question-stage label input { position: absolute; opacity: 0; }.question-stage label > span { display: grid; width: 30px; height: 30px; place-items: center; border: 1px solid #aeb6b0; border-radius: 50%; font-size: .7rem; }.question-stage label.selected > span { border-color: #2e6650; background: #2e6650; color: white; }.question-stage footer { display: flex; justify-content: space-between; margin-top: 42px; }.question-stage footer button,.results header button { display: inline-flex; gap: 8px; align-items: center; padding: 11px 15px; border: 1px solid #b8c0ba; background: transparent; }.question-stage footer .submit { background: #173d32; color: white; }.question-stage footer button:disabled { opacity: .35; }.question-stage nav { display: flex; flex-wrap: wrap; gap: 7px; justify-content: center; margin-top: 55px; }.question-stage nav button { width: 34px; height: 34px; border: 1px solid #c3c9c4; background: transparent; }.question-stage nav button.answered { background: #dce8e1; }.question-stage nav button.active { border-color: #173d32; box-shadow: inset 0 0 0 1px #173d32; }.results { width: min(920px,calc(100% - 44px)); margin: auto; padding: 75px 0 120px; }.results > header { padding-bottom: 70px; text-align: center; }.score { display: grid; margin: 20px 0; }.score strong { font-size: clamp(4.5rem,10vw,8rem); font-weight: 520; line-height: 1; }.score span { color: #6c746e; }.results > header h1 { margin: 20px 0 35px; font-size: 2rem; font-weight: 560; }.results > header > div:last-child { display: flex; justify-content: center; gap: 10px; }.results > header button:last-child { background: #173d32; color: white; }.review > h2 { margin-bottom: 25px; font-size: 2rem; font-weight: 560; }.review article { display: grid; grid-template-columns: 44px 1fr; gap: 15px; padding: 32px 0; border-top: 1px solid #ccd2cd; }.review article > span { color: #8a918c; font-size: .7rem; }.review h3 { margin: 0 0 22px; font-size: 1.25rem; }.review dl { display: grid; gap: 10px; margin: 0; }.review dl div { display: grid; grid-template-columns: 120px 1fr; gap: 15px; }.review dt { color: #747c76; font-size: .7rem; }.review dd { display: flex; gap: 8px; align-items: center; margin: 0; color: #944d43; }.review .correct dd,.review dl div:last-child dd { color: #31634e; }.review article section { margin-top: 25px; padding: 20px; background: #e7ebe7; }.review article section p { margin: 8px 0 0; color: #5f6862; line-height: 1.65; }.results > footer { display: flex; justify-content: space-between; padding-top: 25px; border-top: 1px solid #ccd2cd; color: #68706a; }
@media (max-width: 600px) { .quiz-top strong { font-size: .85rem; }.quiz-top span { display: none; }.question-stage { padding-top: 45px; }.question-stage h1 { margin-bottom: 30px; }.question-stage footer button { padding-inline: 10px; }.results > header > div:last-child { align-items: stretch; flex-direction: column; }.review dl div { grid-template-columns: 1fr; gap: 4px; } }
</style>
