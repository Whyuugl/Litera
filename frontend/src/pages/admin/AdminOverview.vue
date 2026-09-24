<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ArrowRight, BookPlus, UsersRound } from "@lucide/vue";
import { api, type AdminBook, type Category, type MembershipPage, type Page, type User } from "../../api";

const props = defineProps<{ user: User }>();
const emit = defineEmits<{ navigate: [path: string] }>();
const counts = ref({ books: 0, categories: 0, authors: 0, pending: 0 });
const recent = ref<AdminBook[]>([]);
const loading = ref(true);
const error = ref("");

onMounted(async () => {
  try {
    const [books, categories, authors, pending] = await Promise.all([
      api<Page<AdminBook>>("/api/v1/admin/books?page_size=5"),
      api<Page<Category>>("/api/v1/categories?page_size=1"),
      api<Page<unknown>>("/api/v1/authors?page_size=1"),
      api<MembershipPage>("/api/v1/admin/memberships?status=PENDING&page_size=5"),
    ]);
    counts.value = { books: books.total, categories: categories.total, authors: authors.total, pending: pending.total };
    recent.value = books.items;
  } catch (caught) { error.value = caught instanceof Error ? caught.message : "Unable to load workspace summary."; }
  finally { loading.value = false; }
});
</script>
<template>
  <main class="admin-page overview-page">
    <header class="admin-hero"><p class="eyebrow">{{ new Date().getHours() < 12 ? 'Good morning' : new Date().getHours() < 18 ? 'Good afternoon' : 'Good evening' }}, {{ user.name.split(' ')[0] }}.</p><h1>Library workspace</h1><p>Manage the Litera catalog and review membership requests.</p><div><button type="button" @click="emit('navigate', '/admin/books?create=1')"><BookPlus :size="18" />Add book</button><button type="button" @click="emit('navigate', '/admin/members')"><UsersRound :size="18" />Review members</button></div></header>
    <p v-if="error" class="overview-error" role="alert">{{ error }}</p><section class="overview-counts" aria-label="Workspace counts"><div><span>Books</span><strong>{{ loading ? '...' : counts.books }}</strong></div><div><span>Categories</span><strong>{{ loading ? '...' : counts.categories }}</strong></div><div><span>Authors</span><strong>{{ loading ? '...' : counts.authors }}</strong></div><button type="button" @click="emit('navigate', '/admin/members?status=PENDING')"><span>Pending memberships</span><strong>{{ loading ? '...' : counts.pending }}</strong><ArrowRight :size="18" /></button></section>
    <section class="recent-section"><div><p class="eyebrow">Recently updated</p><h2>Books in the workspace</h2></div><div v-if="recent.length" class="recent-list"><button v-for="book in recent" :key="book.id" type="button" @click="emit('navigate', `/admin/books/${book.id}`)"><span><strong>{{ book.title }}</strong><small>{{ book.authors.map((author) => author.name).join(', ') }}</small></span><em :class="book.status.toLowerCase()">{{ book.status }}</em><ArrowRight :size="17" /></button></div><div v-else-if="!loading" class="overview-empty">No books have been added yet.</div></section>
  </main>
</template>
<style scoped>
.admin-page { padding: 65px clamp(28px, 6vw, 90px) 110px; }.admin-hero { max-width: 850px; }.admin-hero h1 { margin: 0; font-size: clamp(3rem, 6vw, 5.8rem); font-weight: 560; line-height: .98; }.admin-hero > p:not(.eyebrow) { color: #69706b; }.admin-hero > div { display: flex; gap: 10px; margin-top: 32px; }.admin-hero button { display: inline-flex; align-items: center; gap: 9px; min-height: 44px; padding: 0 16px; border: 1px solid #173d32; border-radius: 3px; background: #173d32; color: white; }.admin-hero button + button { background: transparent; color: #173d32; }.overview-error { margin: 35px 0 -35px; color: #a14539; }.overview-counts { display: grid; grid-template-columns: repeat(4, 1fr); margin: 75px 0 105px; border-block: 1px solid #cfd4cf; }.overview-counts > div, .overview-counts > button { display: grid; min-height: 130px; padding: 24px; border-right: 1px solid #cfd4cf; background: transparent; text-align: left; }.overview-counts > *:last-child { border: 0; }.overview-counts span { color: #6e756f; font-size: .72rem; text-transform: uppercase; }.overview-counts strong { align-self: end; font-size: 2rem; font-weight: 580; }.overview-counts button svg { position: absolute; align-self: end; justify-self: end; }.recent-section { display: grid; grid-template-columns: .55fr 1.45fr; gap: 7vw; }.recent-section h2 { margin: 0; font-size: 2rem; font-weight: 560; }.recent-list { border-top: 1px solid #ccd1cc; }.recent-list button { display: grid; grid-template-columns: 1fr auto auto; gap: 18px; align-items: center; width: 100%; padding: 19px 0; border-bottom: 1px solid #ccd1cc; background: transparent; text-align: left; }.recent-list button > span { display: grid; gap: 5px; }.recent-list small { color: #747b75; }.recent-list em { padding: 5px 8px; background: #e1e5e1; font-size: .64rem; font-style: normal; }.recent-list em.published { background: #d8e8df; color: #315a46; }.recent-list em.archived { background: #e6dfdc; color: #725148; }.overview-empty { padding: 45px 0; border-block: 1px solid #ccd1cc; color: #747b75; }
@media (max-width: 900px) { .overview-counts { grid-template-columns: repeat(2, 1fr); }.overview-counts > *:nth-child(2) { border-right: 0; }.overview-counts > *:nth-child(-n+2) { border-bottom: 1px solid #cfd4cf; }.recent-section { grid-template-columns: 1fr; } }
@media (max-width: 560px) { .admin-page { padding: 75px 22px; }.admin-hero > div { flex-direction: column; }.admin-hero button { justify-content: center; }.overview-counts { grid-template-columns: 1fr 1fr; margin: 55px 0 75px; }.overview-counts > div, .overview-counts > button { padding: 17px; }.recent-list button { grid-template-columns: 1fr auto; }.recent-list button svg { display: none; } }
</style>
