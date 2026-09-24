<script setup lang="ts">
import { BookOpen } from "@lucide/vue";
import type { BookSummary } from "../api";
import { formatEnum } from "../api";

defineProps<{ book: BookSummary; index?: number }>();
defineEmits<{ open: [slug: string] }>();
</script>

<template>
  <article class="catalog-book">
    <button type="button" class="book-link" @click="$emit('open', book.slug)">
      <span class="catalog-cover">
        <img v-if="book.cover_url" :src="book.cover_url" :alt="`${book.title} cover`" />
        <span v-else class="cover-fallback"><BookOpen :size="31" /><small>{{ book.title }}</small></span>
        <span v-if="index !== undefined" class="catalog-index">{{ String(index + 1).padStart(2, '0') }}</span>
      </span>
      <span class="catalog-meta">
        <strong>{{ book.title }}</strong>
        <span>{{ book.authors.map((author) => author.name).join(', ') }}</span>
        <small>{{ book.category.name }} / {{ formatEnum(book.book_type) }}</small>
      </span>
    </button>
  </article>
</template>

<style scoped>
.catalog-book { min-width: 0; }
.book-link { display: block; width: 100%; padding: 0; background: transparent; text-align: left; }
.catalog-cover { position: relative; display: block; aspect-ratio: 2 / 3; overflow: hidden; background: #dfe6e1; transition: transform .2s ease; }
.catalog-cover img { width: 100%; height: 100%; object-fit: cover; }
.cover-fallback { display: grid; height: 100%; padding: 24px; place-content: center; gap: 22px; background: #dce8e3; color: #315044; text-align: center; }
.cover-fallback small { max-width: 150px; font-size: .83rem; font-weight: 700; line-height: 1.35; }
.catalog-index { position: absolute; top: 10px; left: 10px; display: grid; width: 30px; height: 30px; place-items: center; background: rgba(255,255,255,.92); color: #4f5651; font-size: .68rem; }
.catalog-meta { display: grid; gap: 6px; padding-top: 18px; }
.catalog-meta strong { overflow-wrap: anywhere; font-size: 1.02rem; line-height: 1.25; }
.catalog-meta > span { color: #535a55; font-size: .88rem; }
.catalog-meta small { color: #7b817c; font-size: .68rem; text-transform: uppercase; }
.book-link:hover .catalog-cover { transform: translateY(-6px); }
.book-link:focus-visible { outline: 2px solid #566b5d; outline-offset: 7px; }
@media (max-width: 520px) { .catalog-meta strong { font-size: .92rem; } .catalog-meta > span { font-size: .8rem; } }
</style>
