<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { ArrowLeft, ArrowRight, BookOpen, MoreHorizontal, Plus, Search, X } from "@lucide/vue";
import { api, formatEnum, type AdminBook, type Author, type Category, type Page } from "../../api";
import ConfirmDialog from "../../components/ConfirmDialog.vue";
import { notify } from "../../toast";

const emit = defineEmits<{ navigate: [path: string] }>();
const books = ref<Page<AdminBook> | null>(null);
const categories = ref<Category[]>([]);
const authors = ref<Author[]>([]);
const search = ref(""); const status = ref(""); const page = ref(1);
const loading = ref(true); const error = ref(""); const saving = ref(false);
const showForm = ref(false); const editing = ref<AdminBook | null>(null); const formError = ref(""); const authorSearch = ref("");
const deleting = ref<AdminBook | null>(null); const deletingBusy = ref(false);
const form = ref({ title: "", description: "", category_id: "", author_ids: [] as string[], language: "id", cover_url: "", book_type: "EDUCATIONAL", status: "DRAFT" });
let timer = 0;
const visibleAuthors = computed(() => authors.value.filter((author) => author.name.toLowerCase().includes(authorSearch.value.toLowerCase())));

async function load() {
  loading.value = true; error.value = "";
  const params = new URLSearchParams({ page: String(page.value), page_size: "15" });
  if (search.value.trim()) params.set("search", search.value.trim()); if (status.value) params.set("status", status.value);
  try { books.value = await api<Page<AdminBook>>(`/api/v1/admin/books?${params}`); }
  catch (caught) { error.value = caught instanceof Error ? caught.message : "Unable to load books."; }
  finally { loading.value = false; }
}
function blankForm() { return { title: "", description: "", category_id: categories.value[0]?.id || "", author_ids: [] as string[], language: "id", cover_url: "", book_type: "EDUCATIONAL", status: "DRAFT" }; }
function createBook() { editing.value = null; form.value = blankForm(); formError.value = ""; showForm.value = true; }
function editBook(book: AdminBook) { editing.value = book; form.value = { title: book.title, description: book.description || "", category_id: book.category.id, author_ids: book.authors.map((author) => author.id), language: book.language, cover_url: book.cover_url || "", book_type: book.book_type, status: book.status }; formError.value = ""; showForm.value = true; }
async function save() {
  if (!form.value.category_id || !form.value.author_ids.length) { formError.value = "Choose a category and at least one author."; return; }
  saving.value = true; formError.value = "";
  const payload = { ...form.value, description: form.value.description || null, cover_url: form.value.cover_url || null };
  try {
    if (editing.value) await api(`/api/v1/admin/books/${editing.value.id}`, { method: "PATCH", body: JSON.stringify(payload) });
    else await api("/api/v1/admin/books", { method: "POST", body: JSON.stringify(payload) });
    notify(editing.value ? "Book changes saved" : "Book created"); showForm.value = false; load();
  } catch (caught) { formError.value = caught instanceof Error ? caught.message : "Unable to save the book."; }
  finally { saving.value = false; }
}
async function confirmDelete() {
  if (!deleting.value) return; deletingBusy.value = true;
  try { await api(`/api/v1/admin/books/${deleting.value.id}`, { method: "DELETE" }); notify("Book deleted"); deleting.value = null; load(); }
  catch (caught) { notify(caught instanceof Error ? caught.message : "Unable to delete book.", "error"); }
  finally { deletingBusy.value = false; }
}
function changePage(next: number) { page.value = next; load(); }
watch(search, () => { clearTimeout(timer); timer = window.setTimeout(() => { page.value = 1; load(); }, 350); });
onMounted(async () => {
  try {
    const [categoryPage, authorPage] = await Promise.all([api<Page<Category>>("/api/v1/categories?page_size=100"), api<Page<Author>>("/api/v1/authors?page_size=100")]);
    categories.value = categoryPage.items; authors.value = authorPage.items;
  } catch (caught) { notify(caught instanceof Error ? caught.message : "Unable to load book form options.", "error"); }
  await load();
  const routeParams = new URLSearchParams(location.search);
  if (routeParams.has("create")) createBook();
  const editId = routeParams.get("edit");
  if (editId) {
    try { editBook(await api<AdminBook>(`/api/v1/admin/books/${editId}`)); }
    catch (caught) { notify(caught instanceof Error ? caught.message : "Unable to open book.", "error"); }
  }
});
</script>
<template>
  <main class="admin-page books-page">
    <header class="page-heading"><div><p class="eyebrow">Library</p><h1>Books</h1><p>Manage catalog metadata, publication status, and editions.</p></div><button type="button" @click="createBook"><Plus :size="18" />Add book</button></header>
    <section class="list-tools"><label><Search :size="18" /><span class="sr-only">Search books</span><input v-model="search" type="search" placeholder="Search title or author" /></label><select v-model="status" aria-label="Filter by status" @change="page = 1; load()"><option value="">All statuses</option><option>DRAFT</option><option>PUBLISHED</option><option>ARCHIVED</option></select></section>
    <div v-if="loading" class="table-loading"><span v-for="i in 6" :key="i"></span></div>
    <div v-else-if="error" class="list-state"><h2>Books could not be loaded.</h2><p>{{ error }}</p><button type="button" @click="load">Try again</button></div>
    <div v-else-if="!books?.items.length" class="list-state"><BookOpen :size="30" /><h2>No books found.</h2><p>{{ search || status ? 'Try changing the search or status filter.' : 'Add the first book to the Litera catalog.' }}</p></div>
    <template v-else>
      <div class="admin-table book-table"><div class="table-head"><span>Book</span><span>Category</span><span>Type</span><span>Status</span><span></span></div><article v-for="book in books.items" :key="book.id"><button class="book-cell" type="button" @click="emit('navigate', `/admin/books/${book.id}`)"><span class="mini-cover"><img v-if="book.cover_url" :src="book.cover_url" alt="" /><BookOpen v-else :size="18" /></span><span><strong>{{ book.title }}</strong><small>{{ book.authors.map((author) => author.name).join(', ') }}</small></span></button><span data-label="Category">{{ book.category.name }}</span><span data-label="Type">{{ formatEnum(book.book_type) }}</span><span data-label="Status"><em class="status-badge" :class="book.status.toLowerCase()">{{ book.status }}</em></span><details class="action-menu"><summary aria-label="Book actions"><MoreHorizontal :size="19" /></summary><div><button type="button" @click="editBook(book)">Edit metadata</button><button type="button" @click="emit('navigate', `/admin/books/${book.id}`)">Manage editions</button><button class="danger-text" type="button" @click="deleting = book">Delete</button></div></details></article></div>
      <nav v-if="books.total_pages > 1" class="admin-pagination"><button type="button" :disabled="page === 1" @click="changePage(page - 1)"><ArrowLeft :size="17" /></button><span>Page {{ page }} of {{ books.total_pages }}</span><button type="button" :disabled="page === books.total_pages" @click="changePage(page + 1)"><ArrowRight :size="17" /></button></nav>
    </template>

    <Teleport to="body"><div v-if="showForm" class="form-backdrop" @click.self="showForm = false"><section class="book-form" role="dialog" aria-modal="true" aria-labelledby="book-form-title"><header><div><p class="eyebrow">{{ editing ? 'Edit catalog entry' : 'New catalog entry' }}</p><h2 id="book-form-title">{{ editing ? editing.title : 'Add a book' }}</h2></div><button type="button" aria-label="Close form" @click="showForm = false"><X :size="21" /></button></header><form @submit.prevent="save"><label class="wide">Title<input v-model="form.title" required maxlength="500" /></label><label class="wide">Description<textarea v-model="form.description" rows="4"></textarea></label><label>Category<select v-model="form.category_id" required><option disabled value="">Choose category</option><option v-for="item in categories" :key="item.id" :value="item.id">{{ item.name }}</option></select></label><label>Language<input v-model="form.language" required maxlength="50" placeholder="id or en" /></label><label>Book type<select v-model="form.book_type"><option value="FICTION">Fiction</option><option value="NON_FICTION">Non-fiction</option><option value="EDUCATIONAL">Educational</option><option value="REFERENCE">Reference</option></select></label><label>Status<select v-model="form.status"><option>DRAFT</option><option>PUBLISHED</option><option>ARCHIVED</option></select></label><label class="wide">Cover URL<input v-model="form.cover_url" type="url" maxlength="2048" placeholder="https://..." /></label><fieldset class="wide"><legend>Authors</legend><input v-model="authorSearch" type="search" placeholder="Find an author" /><div><label v-for="author in visibleAuthors" :key="author.id"><input v-model="form.author_ids" type="checkbox" :value="author.id" />{{ author.name }}</label></div><small v-if="!authors.length">Create an author before adding a book.</small></fieldset><p v-if="formError" class="form-error wide" role="alert">{{ formError }}</p><footer class="wide"><button type="button" @click="showForm = false">Cancel</button><button type="submit" :disabled="saving">{{ saving ? 'Saving...' : editing ? 'Save changes' : 'Create book' }}</button></footer></form></section></div></Teleport>
    <ConfirmDialog :open="Boolean(deleting)" :title="`Delete &quot;${deleting?.title || ''}&quot;?`" message="This will only succeed when the book has no editions. Litera will not cascade-delete catalog resources." confirm-label="Delete book" destructive :busy="deletingBusy" @cancel="deleting = null" @confirm="confirmDelete" />
  </main>
</template>
<style scoped>
.admin-page { padding: 58px clamp(28px, 5vw, 75px) 100px; }.page-heading { display: flex; justify-content: space-between; gap: 30px; align-items: end; }.page-heading h1 { margin: 0; font-size: clamp(3rem, 5vw, 5rem); font-weight: 560; }.page-heading p:not(.eyebrow) { color: #707771; }.page-heading > button { display: flex; align-items: center; gap: 8px; min-height: 43px; padding: 0 16px; border-radius: 3px; background: #173d32; color: white; }.list-tools { display: flex; gap: 16px; margin: 50px 0 25px; }.list-tools label { display: flex; align-items: center; gap: 10px; width: min(430px, 100%); padding: 0 3px; border-bottom: 1px solid #9da49e; }.list-tools input { width: 100%; height: 42px; border: 0; outline: 0; background: transparent; }.list-tools select { min-width: 160px; border: 0; border-bottom: 1px solid #9da49e; background: transparent; }.admin-table { border-top: 1px solid #cbd0cb; }.table-head, .admin-table article { display: grid; grid-template-columns: minmax(250px, 2fr) 1fr .8fr .7fr 40px; gap: 22px; align-items: center; padding: 14px 10px; border-bottom: 1px solid #d5d9d5; }.table-head { color: #818781; font-size: .67rem; text-transform: uppercase; }.book-cell { display: flex; align-items: center; gap: 13px; min-width: 0; padding: 0; background: transparent; text-align: left; }.book-cell > span:last-child { display: grid; min-width: 0; gap: 5px; }.book-cell strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.book-cell small { overflow: hidden; color: #777e78; text-overflow: ellipsis; white-space: nowrap; }.mini-cover { display: grid; width: 42px; height: 58px; flex: none; overflow: hidden; place-items: center; background: #dce8e3; }.mini-cover img { width: 100%; height: 100%; object-fit: cover; }.status-badge { padding: 5px 8px; background: #e2e5e2; color: #5d645f; font-size: .62rem; font-style: normal; }.status-badge.published { background: #d8e8df; color: #315a46; }.status-badge.archived { background: #e6dfdc; color: #725148; }.action-menu { position: relative; }.action-menu summary { display: grid; width: 34px; height: 34px; cursor: pointer; place-items: center; list-style: none; }.action-menu summary::-webkit-details-marker { display: none; }.action-menu > div { position: absolute; z-index: 5; top: 34px; right: 0; display: grid; width: 165px; padding: 7px; border: 1px solid #d3d8d3; background: white; box-shadow: 0 10px 25px rgba(20,26,22,.12); }.action-menu button { padding: 9px; background: transparent; text-align: left; }.danger-text { color: #a14539; }.admin-pagination { display: flex; justify-content: flex-end; gap: 14px; align-items: center; margin-top: 35px; }.admin-pagination button { display: grid; width: 38px; height: 38px; place-items: center; background: transparent; border: 1px solid #cbd0cb; }.admin-pagination span { color: #747b75; font-size: .78rem; }.list-state { padding: 75px 0; border-block: 1px solid #d1d5d1; }.list-state h2 { margin: 14px 0 8px; }.list-state p { color: #717872; }.list-state button { padding: 8px 0; border-bottom: 1px solid; background: transparent; }.table-loading { display: grid; gap: 1px; }.table-loading span { height: 76px; background: #e4e7e3; animation: pulse 1.2s infinite; }
.form-backdrop { position: fixed; z-index: 70; inset: 0; display: grid; padding: 20px; place-items: center; background: rgba(20,26,22,.48); }.book-form { width: min(780px, 100%); max-height: calc(100vh - 40px); overflow-y: auto; padding: 34px; background: #f7f8f5; }.book-form > header { display: flex; justify-content: space-between; gap: 25px; }.book-form h2 { margin: 0 0 28px; font-size: 2rem; }.book-form header button { align-self: start; padding: 5px; background: transparent; }.book-form form { display: grid; grid-template-columns: 1fr 1fr; gap: 21px; }.book-form label { display: grid; gap: 8px; color: #555d57; font-size: .75rem; font-weight: 650; }.book-form input, .book-form select, .book-form textarea { width: 100%; min-height: 43px; padding: 8px 10px; border: 1px solid #bfc5c0; border-radius: 2px; background: white; font: inherit; }.book-form textarea { resize: vertical; }.book-form .wide { grid-column: 1 / -1; }.book-form fieldset { margin: 0; padding: 15px; border: 1px solid #bfc5c0; }.book-form legend { padding: 0 6px; font-size: .75rem; font-weight: 650; }.book-form fieldset > div { display: grid; grid-template-columns: repeat(2, 1fr); max-height: 145px; overflow-y: auto; margin-top: 10px; }.book-form fieldset > div label { display: flex; align-items: center; gap: 8px; padding: 6px; }.book-form fieldset input[type=checkbox] { width: 16px; min-height: 16px; }.book-form footer { display: flex; justify-content: flex-end; gap: 9px; }.book-form footer button { min-height: 43px; padding: 0 16px; border: 1px solid #aeb5af; border-radius: 3px; background: transparent; }.book-form footer button:last-child { background: #173d32; color: white; }.form-error { margin: 0; color: #a14539; }
@keyframes pulse { 50% { opacity: .5; } }
@media (max-width: 900px) { .table-head { display: none; }.admin-table article { grid-template-columns: 1fr auto; gap: 10px 20px; padding: 18px 5px; }.admin-table article > span { padding-left: 55px; }.admin-table article > span::before { margin-right: 8px; color: #898f89; content: attr(data-label) ":"; font-size: .67rem; }.action-menu { grid-column: 2; grid-row: 1; } }
@media (max-width: 600px) { .admin-page { padding: 75px 22px; }.page-heading { display: block; }.page-heading > button { margin-top: 25px; }.list-tools { flex-direction: column; }.list-tools select { height: 42px; }.book-form { padding: 25px 20px; }.book-form form { grid-template-columns: 1fr; }.book-form .wide { grid-column: auto; }.book-form fieldset > div { grid-template-columns: 1fr; } }
</style>
