<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ArrowRight, BookCheck, CalendarClock, LoaderCircle, RotateCcw, Search } from "@lucide/vue";
import { api, formatDate, formatEnum, type AdminLoan, type AdminReservation, type LoanPage, type ReservationPage } from "../../api";
import { notify } from "../../toast";

const tab = ref<"overview" | "reservations" | "loans" | "checkout">("overview");
const reservations = ref<ReservationPage>({ items: [], total: 0, page: 1, page_size: 20, total_pages: 0 });
const loans = ref<LoanPage>({ items: [], total: 0, page: 1, page_size: 20, total_pages: 0 });
const counts = ref({ waiting: 0, ready: 0, borrowed: 0, overdue: 0 });
const search = ref("");
const reservationStatus = ref("");
const loanStatus = ref("");
const page = ref(1);
const loading = ref(true);
const busy = ref("");
const error = ref("");
const checkoutForm = ref({ user_id: "", book_copy_id: "", reservation_id: "" });

async function loadCounts() {
  const [waiting, ready, borrowed, overdue] = await Promise.all([
    api<ReservationPage>("/api/v1/admin/reservations?status=WAITING&page_size=1"),
    api<ReservationPage>("/api/v1/admin/reservations?status=READY&page_size=1"),
    api<LoanPage>("/api/v1/admin/loans?status=BORROWED&page_size=1"),
    api<LoanPage>("/api/v1/admin/loans?status=OVERDUE&page_size=1"),
  ]);
  counts.value = { waiting: waiting.total, ready: ready.total, borrowed: borrowed.total, overdue: overdue.total };
}

async function load() {
  loading.value = true; error.value = "";
  const query = new URLSearchParams({ page: String(page.value), page_size: "20" });
  if (search.value.trim()) query.set("search", search.value.trim());
  try {
    if (tab.value === "reservations") {
      if (reservationStatus.value) query.set("status", reservationStatus.value);
      reservations.value = await api<ReservationPage>(`/api/v1/admin/reservations?${query}`);
    } else if (tab.value === "loans") {
      if (loanStatus.value) query.set("status", loanStatus.value);
      loans.value = await api<LoanPage>(`/api/v1/admin/loans?${query}`);
    } else await loadCounts();
  } catch (caught) { error.value = caught instanceof Error ? caught.message : "Unable to load circulation."; }
  finally { loading.value = false; }
}

function switchTab(next: typeof tab.value) { tab.value = next; page.value = 1; search.value = ""; load(); }

async function reservationAction(item: AdminReservation, action: "ready" | "cancel") {
  busy.value = item.id;
  try {
    await api(`/api/v1/admin/reservations/${item.id}/${action}`, { method: "POST" });
    notify(action === "ready" ? "Reservation is ready for pickup." : "Reservation cancelled.");
    await load();
  } catch (caught) { notify(caught instanceof Error ? caught.message : "Action failed.", "error"); }
  finally { busy.value = ""; }
}

function prepareCheckout(item: AdminReservation) {
  checkoutForm.value = { user_id: item.user.id, book_copy_id: item.book_copy_id || "", reservation_id: item.id };
  tab.value = "checkout";
}

async function checkout() {
  busy.value = "checkout";
  try {
    await api("/api/v1/admin/loans/checkout", { method: "POST", body: JSON.stringify({ ...checkoutForm.value, reservation_id: checkoutForm.value.reservation_id || null }) });
    notify("Checkout completed.");
    checkoutForm.value = { user_id: "", book_copy_id: "", reservation_id: "" };
    tab.value = "loans"; loanStatus.value = "BORROWED"; await load();
  } catch (caught) { notify(caught instanceof Error ? caught.message : "Checkout failed.", "error"); }
  finally { busy.value = ""; }
}

async function returnLoan(item: AdminLoan) {
  busy.value = item.id;
  try { await api(`/api/v1/admin/loans/${item.id}/return`, { method: "POST" }); notify("Return completed."); await load(); }
  catch (caught) { notify(caught instanceof Error ? caught.message : "Return failed.", "error"); }
  finally { busy.value = ""; }
}

onMounted(load);
</script>

<template>
  <main class="circulation-page">
    <header><div><p class="eyebrow">Physical library</p><h1>Circulation</h1><p>Move reservations and physical copies through checkout and return.</p></div><nav aria-label="Circulation views"><button v-for="item in ['overview','reservations','loans','checkout'] as const" :key="item" :class="{ active: tab === item }" type="button" @click="switchTab(item)">{{ formatEnum(item) }}</button></nav></header>
    <p v-if="error" class="circulation-error" role="alert">{{ error }}</p>
    <div v-if="loading" class="circulation-loading"><LoaderCircle class="spin" :size="22" /></div>

    <template v-else-if="tab === 'overview'">
      <section class="attention-grid">
        <button type="button" @click="reservationStatus = 'WAITING'; switchTab('reservations')"><span>Reservations waiting</span><strong>{{ counts.waiting }}</strong><ArrowRight :size="17" /></button>
        <button type="button" @click="reservationStatus = 'READY'; switchTab('reservations')"><span>Ready for pickup</span><strong>{{ counts.ready }}</strong><ArrowRight :size="17" /></button>
        <button type="button" @click="loanStatus = 'BORROWED'; switchTab('loans')"><span>Active loans</span><strong>{{ counts.borrowed }}</strong><ArrowRight :size="17" /></button>
        <button type="button" @click="loanStatus = 'OVERDUE'; switchTab('loans')"><span>Overdue</span><strong>{{ counts.overdue }}</strong><ArrowRight :size="17" /></button>
      </section>
      <section class="quick-actions"><div><p class="eyebrow">Daily desk</p><h2>Keep books moving.</h2></div><div><button type="button" @click="switchTab('checkout')"><BookCheck :size="20" /><span><strong>Checkout</strong><small>Confirm member and physical copy</small></span><ArrowRight :size="17" /></button><button type="button" @click="loanStatus = 'BORROWED'; switchTab('loans')"><RotateCcw :size="20" /><span><strong>Process return</strong><small>Find an active loan</small></span><ArrowRight :size="17" /></button><button type="button" @click="switchTab('reservations')"><CalendarClock :size="20" /><span><strong>Review reservations</strong><small>Prepare the next copy</small></span><ArrowRight :size="17" /></button></div></section>
    </template>

    <template v-else-if="tab === 'reservations'">
      <form class="circulation-filters" @submit.prevent="page = 1; load()"><label><Search :size="17" /><input v-model="search" type="search" placeholder="Member, email, or book" /></label><select v-model="reservationStatus" aria-label="Reservation status" @change="page = 1; load()"><option value="">All statuses</option><option v-for="status in ['WAITING','READY','FULFILLED','CANCELLED','EXPIRED']" :key="status">{{ status }}</option></select><button type="submit">Search</button></form>
      <section v-if="reservations.items.length" class="circulation-list"><article v-for="item in reservations.items" :key="item.id"><div><span class="status-badge" :class="item.status.toLowerCase()">{{ formatEnum(item.status) }}</span><h2>{{ item.edition.book.title }}</h2><p>{{ item.user.name }} · {{ item.user.email }}</p><small v-if="item.status === 'WAITING'">Queue #{{ item.queue_position }}</small><small v-if="item.book_copy">{{ item.book_copy.barcode }} · {{ item.book_copy.shelf_location || 'Pickup desk' }}</small></div><div class="row-actions"><button v-if="item.status === 'WAITING'" type="button" :disabled="busy === item.id" @click="reservationAction(item, 'ready')">Mark ready</button><button v-if="item.status === 'READY'" type="button" @click="prepareCheckout(item)">Checkout</button><button v-if="['WAITING','READY'].includes(item.status)" class="quiet" type="button" :disabled="busy === item.id" @click="reservationAction(item, 'cancel')">Cancel</button></div></article></section><p v-else class="table-empty">No reservations match these filters.</p>
      <div class="pager"><button type="button" :disabled="page <= 1" @click="page--; load()">Previous</button><span>Page {{ page }} of {{ reservations.total_pages || 1 }}</span><button type="button" :disabled="page >= reservations.total_pages" @click="page++; load()">Next</button></div>
    </template>

    <template v-else-if="tab === 'loans'">
      <form class="circulation-filters" @submit.prevent="page = 1; load()"><label><Search :size="17" /><input v-model="search" type="search" placeholder="Member, book, or barcode" /></label><select v-model="loanStatus" aria-label="Loan status" @change="page = 1; load()"><option value="">All statuses</option><option v-for="status in ['BORROWED','OVERDUE','RETURNED','LOST']" :key="status">{{ status }}</option></select><button type="submit">Search</button></form>
      <section v-if="loans.items.length" class="circulation-list"><article v-for="item in loans.items" :key="item.id"><div><span class="status-badge" :class="item.status.toLowerCase()">{{ formatEnum(item.status) }}</span><h2>{{ item.book_copy.edition.book.title }}</h2><p>{{ item.user.name }} · {{ item.book_copy.barcode }}</p><small>Borrowed {{ formatDate(item.borrowed_at) }} · Due {{ formatDate(item.due_at) }}</small></div><div class="row-actions"><button v-if="['BORROWED','OVERDUE'].includes(item.status)" type="button" :disabled="busy === item.id" @click="returnLoan(item)">Confirm return</button></div></article></section><p v-else class="table-empty">No loans match these filters.</p>
      <div class="pager"><button type="button" :disabled="page <= 1" @click="page--; load()">Previous</button><span>Page {{ page }} of {{ loans.total_pages || 1 }}</span><button type="button" :disabled="page >= loans.total_pages" @click="page++; load()">Next</button></div>
    </template>

    <section v-else class="checkout-panel"><div><p class="eyebrow">Desk action</p><h2>Checkout a physical copy</h2><p>Use the values from a ready reservation, or enter member and copy IDs for a direct walk-in checkout.</p></div><form @submit.prevent="checkout"><label>Member ID<input v-model="checkoutForm.user_id" required /></label><label>Physical copy ID<input v-model="checkoutForm.book_copy_id" required /></label><label>Reservation ID <small>Optional for direct checkout</small><input v-model="checkoutForm.reservation_id" /></label><button type="submit" :disabled="busy === 'checkout'">{{ busy === 'checkout' ? 'Processing...' : 'Confirm checkout' }}</button></form></section>
  </main>
</template>

<style scoped>
.circulation-page { padding: 58px clamp(28px, 5vw, 78px) 110px; }.circulation-page > header { display: flex; justify-content: space-between; gap: 45px; align-items: end; padding-bottom: 48px; border-bottom: 1px solid #cdd2cd; }.circulation-page h1 { margin: 0; font-size: clamp(3rem, 6vw, 5.5rem); font-weight: 560; line-height: .96; }.circulation-page header p:not(.eyebrow) { color: #69706b; }.circulation-page header nav { display: flex; gap: 22px; }.circulation-page header nav button { padding: 10px 0; border-bottom: 2px solid transparent; background: transparent; color: #727973; }.circulation-page header nav button.active { border-color: #173d32; color: #173d32; }.circulation-loading { display: grid; min-height: 350px; place-items: center; }.circulation-error { margin: 25px 0; color: #934337; }.attention-grid { display: grid; grid-template-columns: repeat(4, 1fr); margin-top: 55px; border-block: 1px solid #cdd2cd; }.attention-grid button { position: relative; display: grid; min-height: 145px; padding: 23px; border-right: 1px solid #cdd2cd; background: transparent; text-align: left; }.attention-grid button:last-child { border: 0; }.attention-grid span { color: #737a74; font-size: .72rem; text-transform: uppercase; }.attention-grid strong { align-self: end; font-size: 2.2rem; font-weight: 560; }.attention-grid svg { position: absolute; right: 20px; bottom: 28px; }.quick-actions { display: grid; grid-template-columns: .6fr 1.4fr; gap: 8vw; margin-top: 95px; }.quick-actions h2,.checkout-panel h2 { margin: 0; font-size: 2.8rem; font-weight: 560; }.quick-actions > div:last-child { border-top: 1px solid #cdd2cd; }.quick-actions button { display: grid; grid-template-columns: 30px 1fr auto; gap: 15px; align-items: center; width: 100%; padding: 23px 0; border-bottom: 1px solid #cdd2cd; background: transparent; text-align: left; }.quick-actions button span { display: grid; gap: 5px; }.quick-actions small { color: #777e78; }.circulation-filters { display: grid; grid-template-columns: 1fr 190px auto; gap: 10px; margin: 35px 0; }.circulation-filters label { display: flex; align-items: center; gap: 9px; padding: 0 12px; border: 1px solid #bdc4be; background: white; }.circulation-filters input { width: 100%; min-height: 42px; border: 0; outline: 0; }.circulation-filters select,.circulation-filters > button { min-height: 44px; padding: 0 12px; border: 1px solid #bdc4be; background: white; }.circulation-filters > button { background: #173d32; color: white; }.circulation-list { border-top: 1px solid #cdd2cd; }.circulation-list article { display: flex; justify-content: space-between; gap: 25px; align-items: center; min-height: 145px; padding: 24px 0; border-bottom: 1px solid #cdd2cd; }.circulation-list h2 { margin: 8px 0; font-size: 1.3rem; }.circulation-list p { margin: 0 0 7px; color: #626a64; }.circulation-list small { color: #7b827c; }.status-badge { display: inline-block; padding: 5px 8px; background: #e1e5e1; color: #616862; font-size: .63rem; font-weight: 700; text-transform: uppercase; }.status-badge.ready,.status-badge.returned { background: #d8e8df; color: #315a46; }.status-badge.overdue,.status-badge.cancelled { background: #f0ddd8; color: #884236; }.row-actions { display: flex; gap: 8px; }.row-actions button { min-height: 39px; padding: 0 13px; border: 1px solid #173d32; background: #173d32; color: white; }.row-actions button.quiet { background: transparent; color: #5e665f; }.row-actions button:disabled { opacity: .55; }.pager { display: flex; justify-content: space-between; align-items: center; padding-top: 25px; color: #767d77; font-size: .78rem; }.pager button { padding: 8px 0; border-bottom: 1px solid; background: transparent; }.pager button:disabled { border-color: transparent; opacity: .4; }.table-empty { padding: 75px 0; border-block: 1px solid #cdd2cd; color: #747b75; text-align: center; }.checkout-panel { display: grid; grid-template-columns: .75fr 1.25fr; gap: 8vw; margin-top: 65px; }.checkout-panel > div > p:last-child { color: #6c736d; line-height: 1.65; }.checkout-panel form { display: grid; gap: 20px; padding: 35px; background: #e2ebe6; }.checkout-panel label { display: grid; gap: 8px; color: #59635d; font-size: .75rem; font-weight: 700; }.checkout-panel label small { font-weight: 400; }.checkout-panel input { min-height: 44px; padding: 0 10px; border: 1px solid #aebbb3; background: white; }.checkout-panel form button { min-height: 46px; background: #173d32; color: white; font-weight: 700; }
@media (max-width: 900px) { .circulation-page > header { align-items: start; flex-direction: column; }.circulation-page header nav { width: 100%; overflow-x: auto; }.circulation-page header nav button { white-space: nowrap; }.attention-grid { grid-template-columns: repeat(2, 1fr); }.attention-grid button:nth-child(2) { border-right: 0; }.attention-grid button:nth-child(-n+2) { border-bottom: 1px solid #cdd2cd; }.quick-actions,.checkout-panel { grid-template-columns: 1fr; }.circulation-filters { grid-template-columns: 1fr 160px; }.circulation-filters > button { grid-column: 1/-1; } }
@media (max-width: 600px) { .circulation-page { padding: 75px 22px; }.attention-grid { grid-template-columns: 1fr 1fr; }.circulation-list article { align-items: start; flex-direction: column; }.row-actions { width: 100%; }.row-actions button { flex: 1; }.circulation-filters { grid-template-columns: 1fr; }.circulation-filters > button { grid-column: auto; }.checkout-panel form { padding: 24px; } }
</style>
