<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ArrowRight, BookOpen, LoaderCircle } from "@lucide/vue";
import { api, type ReadingProgressItem } from "../api";

const emit = defineEmits<{ navigate: [path: string] }>();
const items = ref<ReadingProgressItem[]>([]);
const loading = ref(true);
onMounted(async () => {
  try { items.value = await api<ReadingProgressItem[]>("/api/v1/reading-progress"); }
  finally { loading.value = false; }
});
</script>

<template>
  <section v-if="loading || items.length" class="continue-section">
    <header><div><p class="eyebrow">Continue reading</p><h2>Pick up where you left off.</h2></div><LoaderCircle v-if="loading" class="spin" :size="22" /></header>
    <div v-if="!loading" class="continue-list">
      <article v-for="item in items.slice(0, 3)" :key="item.id">
        <div class="continue-cover"><img v-if="item.book.cover_url" :src="item.book.cover_url" :alt="`${item.book.title} cover`" /><BookOpen v-else :size="25" /></div>
        <div><span>{{ item.chapter?.title || `Page ${item.current_page}` }}</span><h3>{{ item.book.title }}</h3><div class="progress"><i :style="{ width: `${item.progress_percentage}%` }"></i></div><small>{{ Math.round(item.progress_percentage) }}% read</small></div>
        <button type="button" aria-label="Continue reading" @click="emit('navigate', `/read/${item.edition_id}`)"><ArrowRight :size="18" /></button>
      </article>
    </div>
  </section>
</template>

<style scoped>
.continue-section { width: min(1120px,88vw); margin: auto; padding: 95px 0 30px; }.continue-section > header { display: flex; justify-content: space-between; align-items: end; margin-bottom: 28px; }.continue-section h2 { margin: 0; font-size: 2.3rem; font-weight: 560; }.continue-list { border-bottom: 1px solid #cdd2cd; }.continue-list article { display: grid; grid-template-columns: 62px 1fr 42px; gap: 20px; align-items: center; padding: 20px 0; border-top: 1px solid #cdd2cd; }.continue-cover { display: grid; width: 54px; aspect-ratio: 2/3; overflow: hidden; place-items: center; background: #dce8e3; }.continue-cover img { width: 100%; height: 100%; object-fit: cover; }.continue-list h3 { margin: 5px 0 10px; font-size: 1.12rem; }.continue-list span,.continue-list small { color: #737b75; font-size: .7rem; }.progress { max-width: 420px; height: 3px; margin-bottom: 6px; background: #d8ddd9; }.progress i { display: block; height: 100%; background: #2f6953; }.continue-list button { display: grid; width: 40px; height: 40px; place-items: center; background: transparent; }
@media (max-width: 650px) { .continue-section { width: calc(100% - 44px); padding-top: 65px; }.continue-section h2 { font-size: 1.8rem; }.continue-list article { grid-template-columns: 50px 1fr 38px; gap: 13px; }.continue-cover { width: 46px; } }
</style>
