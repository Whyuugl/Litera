<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { ArrowLeft, ArrowRight, BookOpen, FileText, Library, LockKeyhole } from "@lucide/vue";
import { api, formatEnum, type BookDetail, type Membership, type Reservation, type User } from "../api";
import { notify } from "../toast";

const props = defineProps<{ slug: string; user: User | null }>();
const emit = defineEmits<{ navigate: [path: string] }>();
const book = ref<BookDetail | null>(null);
const membership = ref<Membership | null>(null);
const reservations = ref<Reservation[]>([]);
const reserving = ref("");
const loading = ref(true);
const error = ref("");

const digital = computed(() => book.value?.editions.flatMap((edition) => edition.digital.map((file) => ({ ...file, edition_id: edition.id }))) || []);
const primaryDigital = computed(() => digital.value.find((file) => file.available) || null);
const physicalEditions = computed(() => (book.value?.editions || []).filter((edition) => edition.physical.total_copies > 0));
const activeMember = computed(() => membership.value?.status === "ACTIVE");

function hasDigitalAccess(level: "PUBLIC" | "REGISTERED" | "MEMBER") {
  return level === "PUBLIC" || (level === "REGISTERED" && Boolean(props.user)) || (level === "MEMBER" && activeMember.value);
}

function requestAccess(level: "PUBLIC" | "REGISTERED" | "MEMBER") {
  if (level === "REGISTERED" && !props.user) emit("navigate", `/login?redirect=${encodeURIComponent(`/books/${props.slug}`)}`);
  if (level === "MEMBER") emit("navigate", props.user ? "/membership" : `/login?redirect=${encodeURIComponent(`/books/${props.slug}`)}`);
}

function existingReservation(editionId: string) {
  return reservations.value.find((item) => item.edition_id === editionId && ["WAITING", "READY"].includes(item.status));
}

async function reserve(editionId: string) {
  reserving.value = editionId;
  try {
    const reservation = await api<Reservation>("/api/v1/reservations", { method: "POST", body: JSON.stringify({ edition_id: editionId }) });
    reservations.value.unshift(reservation);
    notify(`Reserved. You are #${reservation.queue_position} in the queue.`);
  } catch (caught) { notify(caught instanceof Error ? caught.message : "Unable to reserve this edition.", "error"); }
  finally { reserving.value = ""; }
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    book.value = await api<BookDetail>(`/api/v1/books/${encodeURIComponent(props.slug)}`);
    if (props.user) {
      try {
        [membership.value, reservations.value] = await Promise.all([
          api<{ membership: Membership | null }>("/api/v1/memberships/me").then((result) => result.membership),
          api<Reservation[]>("/api/v1/reservations/me"),
        ]);
      }
      catch { membership.value = null; }
    }
  } catch (caught) { error.value = caught instanceof Error ? caught.message : "Unable to load this book."; }
  finally { loading.value = false; }
}

watch(() => props.slug, load);
onMounted(load);
</script>

<template>
  <main class="detail-page">
    <div v-if="loading" class="detail-skeleton" aria-label="Loading book details"><span></span><div><i></i><i></i><i></i><i></i></div></div>
    <section v-else-if="error" class="detail-state"><button type="button" @click="emit('navigate', '/explore')"><ArrowLeft :size="17" /> Back to explore</button><h1>This book is out of view.</h1><p>{{ error }}</p></section>
    <template v-else-if="book">
      <button class="back-link" type="button" @click="emit('navigate', '/explore')"><ArrowLeft :size="17" /> Explore</button>
      <section class="book-intro">
        <div class="detail-cover"><img v-if="book.cover_url" :src="book.cover_url" :alt="`${book.title} cover`" /><span v-else><BookOpen :size="48" /><small>{{ book.title }}</small></span></div>
        <div class="detail-copy">
          <p class="eyebrow">{{ book.category.name }}</p>
          <h1>{{ book.title }}</h1>
          <p class="authors">{{ book.authors.map((author) => author.name).join(', ') }}</p>
          <div class="primary-tags"><span>{{ formatEnum(book.book_type) }}</span><span>{{ book.language.toUpperCase() }}</span></div>
          <p v-if="book.description" class="description">{{ book.description }}</p>
          <p v-else class="description muted">A description has not been added for this title yet.</p>
          <div v-if="primaryDigital" class="read-actions">
            <button v-if="hasDigitalAccess(primaryDigital.access_level)" type="button" @click="emit('navigate', '/read/' + primaryDigital.edition_id)"><BookOpen :size="18" /> Read online <ArrowRight :size="17" /></button>
            <button v-else type="button" @click="requestAccess(primaryDigital.access_level)"><LockKeyhole :size="17" /> {{ primaryDigital.access_level === 'REGISTERED' ? 'Sign in to read' : 'Join to read' }} <ArrowRight :size="17" /></button>
            <small>Open this e-book directly in the Litera reader.</small>
          </div>
        </div>
      </section>

      <section class="availability-section">
        <div class="availability-heading"><p class="eyebrow">Choose your format</p><h2>Read this book</h2></div>
        <div class="availability-list">
          <article v-for="item in digital" :key="item.id">
            <FileText :size="25" /><div><span>Digital / {{ item.file_type }}</span><h3>{{ item.access_level === 'PUBLIC' ? 'Available to everyone' : item.access_level === 'REGISTERED' ? 'Registered reader access' : 'Member access' }}</h3><p v-if="!item.available">This edition is still being prepared.</p><p v-else-if="hasDigitalAccess(item.access_level)">Open the digital edition and continue from where you left off.</p><p v-else>{{ item.access_level === 'REGISTERED' ? 'Sign in to access this digital edition.' : 'This edition is available to active Litera members.' }}</p><button v-if="item.available && hasDigitalAccess(item.access_level)" type="button" @click="emit('navigate', `/read/${item.edition_id}`)">Read now <ArrowRight :size="16" /></button><button v-else-if="item.available" type="button" @click="requestAccess(item.access_level)">{{ item.access_level === 'REGISTERED' ? 'Sign in' : 'View membership' }} <ArrowRight :size="16" /></button><span v-else class="availability-note">{{ formatEnum(item.processing_status) }}</span></div>
          </article>
          <article v-for="edition in physicalEditions" :key="`physical-${edition.id}`">
            <Library :size="25" /><div><span>Printed copy / optional</span><h3>{{ edition.physical.available_copies }} of {{ edition.physical.total_copies }} copies available</h3>
              <template v-if="existingReservation(edition.id)"><p>{{ existingReservation(edition.id)?.status === 'READY' ? 'Your copy is ready for pickup.' : `Reserved. You're #${existingReservation(edition.id)?.queue_position} in the queue.` }}</p><button type="button" @click="emit('navigate', '/library')">View My Library <ArrowRight :size="16" /></button></template>
              <template v-else-if="activeMember"><p>{{ edition.physical.available_copies ? 'A copy is currently on the shelf.' : 'All copies are in use. You can still join the reservation queue.' }}</p><button type="button" :disabled="reserving === edition.id" @click="reserve(edition.id)">{{ reserving === edition.id ? 'Reserving...' : 'Reserve' }} <ArrowRight :size="16" /></button></template>
              <template v-else-if="user"><p>Physical borrowing requires an active membership.</p><button type="button" @click="emit('navigate', '/membership')">View membership <ArrowRight :size="16" /></button></template>
              <template v-else><p>Sign in and become a member to borrow physical books.</p><button type="button" @click="emit('navigate', `/login?redirect=${encodeURIComponent(`/books/${slug}`)}`)">Sign in <ArrowRight :size="16" /></button></template>
            </div>
          </article>
          <article v-if="!digital.length && !physicalEditions.length">
            <LockKeyhole :size="25" /><div><span>Availability</span><h3>No reading edition yet</h3><p>This title is in the catalog, but no digital file or physical copy is currently available.</p></div>
          </article>
        </div>
      </section>

      <section v-if="book.editions.length" class="edition-section">
        <div><p class="eyebrow">Publication details</p><h2>About this edition</h2></div>
        <div class="edition-list">
          <article v-for="(edition, index) in book.editions" :key="edition.id"><span v-if="book.editions.length > 1" class="edition-label">Edition {{ index + 1 }}</span><dl><template v-if="edition.publisher"><dt>Publisher</dt><dd>{{ edition.publisher }}</dd></template><template v-if="edition.publication_year"><dt>Published</dt><dd>{{ edition.publication_year }}</dd></template><template v-if="edition.edition_number"><dt>Edition</dt><dd>{{ edition.edition_number }}</dd></template><template v-if="edition.page_count"><dt>Length</dt><dd>{{ edition.page_count }} pages</dd></template><template v-if="edition.language"><dt>Language</dt><dd>{{ edition.language.toUpperCase() }}</dd></template><template v-if="edition.isbn"><dt>ISBN</dt><dd>{{ edition.isbn }}</dd></template></dl></article>
        </div>
      </section>
    </template>
  </main>
</template>

<style scoped>
.detail-page { width: min(1240px, 88vw); min-height: 75vh; margin: auto; padding: 55px 0 130px; }
.back-link, .detail-state > button { display: inline-flex; align-items: center; gap: 9px; padding: 8px 0; background: transparent; color: #606762; }
.book-intro { display: grid; grid-template-columns: minmax(260px, 390px) 1fr; gap: clamp(65px, 10vw, 145px); align-items: center; padding: 55px 4vw 130px; }
.detail-cover { aspect-ratio: 2 / 3; background: #dce8e3; box-shadow: 0 28px 55px rgba(31,39,34,.16); }
.detail-cover img { width: 100%; height: 100%; object-fit: cover; }
.detail-cover > span { display: grid; height: 100%; padding: 35px; place-content: center; gap: 25px; color: #315044; text-align: center; }
.detail-cover small { max-width: 210px; font-size: 1rem; font-weight: 700; line-height: 1.4; }
.detail-copy h1 { max-width: 720px; margin: 0; overflow-wrap: anywhere; font-size: clamp(3rem, 5.5vw, 5.8rem); font-weight: 560; line-height: .96; }
.authors { margin: 22px 0; color: #4e5651; font-size: 1.15rem; }
.primary-tags { display: flex; gap: 9px; }
.primary-tags span { padding: 7px 10px; background: #e3e8e4; font-size: .7rem; text-transform: uppercase; }
.description { max-width: 680px; margin: 35px 0 0; color: #545c57; line-height: 1.8; white-space: pre-line; }
.description.muted { color: #858b86; }
.read-actions { display: flex; flex-wrap: wrap; gap: 12px 18px; align-items: center; margin-top: 30px; }
.read-actions button { display: inline-flex; gap: 9px; align-items: center; min-height: 46px; padding: 0 17px; background: #173d32; color: white; }
.read-actions small { color: #727a74; }
.availability-section, .edition-section { display: grid; grid-template-columns: .65fr 1.35fr; gap: 9vw; padding: 110px 4vw; border-top: 1px solid #d3d7d3; }
.availability-heading h2, .edition-section h2 { margin: 0; font-size: clamp(2rem, 3.5vw, 3.5rem); font-weight: 560; }
.availability-list { border-top: 1px solid #c9ceca; }
.availability-list article { display: grid; grid-template-columns: 42px 1fr; gap: 18px; padding: 28px 0; border-bottom: 1px solid #c9ceca; }
.availability-list article > div > span:first-child, .edition-label { color: #7a817c; font-size: .68rem; font-weight: 700; text-transform: uppercase; }
.availability-list h3 { margin: 8px 0 10px; font-size: 1.18rem; }
.availability-list p { max-width: 570px; margin: 0; color: #69706b; line-height: 1.6; }
.availability-list button { display: inline-flex; align-items: center; gap: 8px; margin-top: 18px; padding: 8px 0; border-bottom: 1px solid; background: transparent; }
.availability-list button:disabled { cursor: wait; opacity: .55; }
.availability-note { display: inline-block; margin-top: 17px; color: #8a8f8b; font-size: .72rem; }
.edition-list article { padding: 25px 0; border-top: 1px solid #c9ceca; }
.edition-list dl { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 45px; margin: 10px 0 0; }
.edition-list dl template { display: contents; }
.edition-list dt, .edition-list dd { margin: 0; padding: 14px 0; border-bottom: 1px solid #e0e3e0; }
.edition-list dt { color: #7b817c; font-size: .78rem; }
.edition-list dd { text-align: right; }
.detail-state { padding: 120px 0; }
.detail-state h1 { margin: 45px 0 10px; font-size: clamp(2.5rem, 5vw, 5rem); font-weight: 560; }
.detail-state p { color: #6a706b; }
.detail-skeleton { display: grid; grid-template-columns: 35% 1fr; gap: 10vw; padding: 70px 4vw; }
.detail-skeleton > span { aspect-ratio: 2 / 3; background: #e2e5e1; animation: pulse 1.3s infinite; }
.detail-skeleton i { display: block; width: 80%; height: 45px; margin: 25px 0; background: #e2e5e1; animation: pulse 1.3s infinite; }
.detail-skeleton i:first-child { width: 30%; height: 12px; }.detail-skeleton i:last-child { width: 95%; height: 130px; }
@keyframes pulse { 50% { opacity: .45; } }
@media (max-width: 750px) { .detail-page { width: calc(100% - 44px); padding-top: 25px; } .book-intro { grid-template-columns: 1fr; gap: 50px; padding: 38px 0 85px; } .detail-cover { width: min(280px, 78vw); } .detail-copy h1 { font-size: clamp(2.7rem, 14vw, 4.5rem); } .availability-section, .edition-section { grid-template-columns: 1fr; gap: 45px; padding: 80px 0; } .detail-skeleton { grid-template-columns: 1fr; } .detail-skeleton > span { width: 70%; } }
</style>
