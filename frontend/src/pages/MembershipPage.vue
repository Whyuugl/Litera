<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ArrowRight, BookOpen, Check, Clock3, Library, RefreshCw, ShieldAlert } from "@lucide/vue";
import { api, formatDate, type Membership, type User } from "../api";

const props = defineProps<{ user: User }>();
const membership = ref<Membership | null>(null);
const loading = ref(true);
const applying = ref(false);
const error = ref("");
const canApply = computed(() => props.user.role === "USER" && (!membership.value || ["REJECTED", "EXPIRED"].includes(membership.value.status)));

async function load() {
  loading.value = true; error.value = "";
  try { membership.value = (await api<{ membership: Membership | null }>("/api/v1/memberships/me")).membership; }
  catch (caught) { error.value = caught instanceof Error ? caught.message : "Unable to load membership."; }
  finally { loading.value = false; }
}

async function apply() {
  applying.value = true; error.value = "";
  try { membership.value = await api<Membership>("/api/v1/memberships/apply", { method: "POST" }); }
  catch (caught) { error.value = caught instanceof Error ? caught.message : "Unable to submit your application."; }
  finally { applying.value = false; }
}

onMounted(load);
</script>

<template>
  <main class="membership-page">
    <header><p class="eyebrow">Litera membership</p><h1>More ways to<br />keep learning.</h1><p>Membership opens access to physical borrowing and member-only digital editions as those experiences become available.</p></header>
    <section v-if="loading" class="membership-skeleton" aria-label="Loading membership"><span></span><i></i><i></i><i></i></section>
    <section v-else-if="error && !membership" class="membership-error"><h2>We could not check your membership.</h2><p>{{ error }}</p><button type="button" @click="load">Try again <RefreshCw :size="16" /></button></section>
    <section v-else-if="!membership" class="membership-layout">
      <div class="status-panel"><span class="status-icon"><BookOpen :size="28" /></span><p class="status-label">Membership status</p><h2>No membership yet</h2><p>Apply when you are ready. An administrator will review your application before membership becomes active.</p><button v-if="canApply" type="button" :disabled="applying" @click="apply">{{ applying ? 'Submitting...' : 'Apply for membership' }} <ArrowRight :size="17" /></button><p v-else class="admin-note">Administrator accounts cannot apply for membership.</p></div>
      <div class="benefits"><h3>What membership is for</h3><article><Library :size="22" /><div><strong>Physical borrowing</strong><p>Borrow available copies when the borrowing workflow launches.</p></div></article><article><BookOpen :size="22" /><div><strong>Member digital access</strong><p>Qualify for editions marked for active Litera members.</p></div></article><article><Check :size="22" /><div><strong>Future learning tools</strong><p>Membership will support upcoming reading and learning experiences.</p></div></article></div>
    </section>
    <section v-else class="membership-layout">
      <div class="status-panel" :class="membership.status.toLowerCase()">
        <span class="status-icon"><Check v-if="membership.status === 'ACTIVE'" :size="28" /><Clock3 v-else-if="membership.status === 'PENDING'" :size="28" /><ShieldAlert v-else :size="28" /></span>
        <p class="status-label">Membership application</p>
        <h2 v-if="membership.status === 'PENDING'">Pending review</h2><h2 v-else-if="membership.status === 'ACTIVE'">Active member</h2><h2 v-else-if="membership.status === 'REJECTED'">Application not approved</h2><h2 v-else-if="membership.status === 'EXPIRED'">Membership expired</h2><h2 v-else>Membership suspended</h2>
        <p v-if="membership.status === 'PENDING'">Your application has been submitted. You cannot apply again while it is being reviewed.</p><p v-else-if="membership.status === 'ACTIVE'">Your Litera membership is active. Member-only catalog access is available to you.</p><p v-else-if="membership.status === 'REJECTED'">{{ membership.rejection_reason || 'Your application was not approved. You may submit a new application.' }}</p><p v-else-if="membership.status === 'EXPIRED'">Your previous membership period has ended. You may apply again for a new review.</p><p v-else>{{ membership.suspension_reason || 'Your membership has been suspended. Contact the library for more information.' }}</p>
        <button v-if="canApply" type="button" :disabled="applying" @click="apply">{{ applying ? 'Submitting...' : membership.status === 'EXPIRED' ? 'Apply for renewal' : 'Apply again' }} <ArrowRight :size="17" /></button>
        <p v-if="error" class="inline-error" role="alert">{{ error }}</p>
      </div>
      <div class="membership-facts">
        <div><span>Status</span><strong>{{ membership.status }}</strong></div><div v-if="membership.member_number"><span>Member number</span><strong>{{ membership.member_number }}</strong></div><div><span>Applied</span><strong>{{ formatDate(membership.applied_at) }}</strong></div><div v-if="membership.approved_at"><span>Member since</span><strong>{{ formatDate(membership.approved_at) }}</strong></div><div v-if="membership.expires_at"><span>Valid until</span><strong>{{ formatDate(membership.expires_at) }}</strong></div>
      </div>
    </section>
  </main>
</template>

<style scoped>
.membership-page { width: min(1180px, 88vw); min-height: 80vh; margin: auto; padding: 80px 0 130px; }
.membership-page > header { display: grid; grid-template-columns: .6fr 1.1fr .8fr; gap: 5vw; align-items: end; padding-bottom: 75px; }
.membership-page header h1 { margin: 0; font-size: clamp(3rem, 5.5vw, 5.7rem); font-weight: 560; line-height: .96; }
.membership-page header > p:last-child { margin: 0 0 7px; color: #626a64; line-height: 1.7; }
.membership-layout { display: grid; grid-template-columns: 1.05fr .95fr; gap: 8vw; padding: 90px 7vw; background: #dce8e3; }
.status-icon { display: grid; width: 52px; height: 52px; margin-bottom: 45px; place-items: center; border: 1px solid #9db0a7; border-radius: 50%; }
.status-label { color: #617068; font-size: .72rem; font-weight: 700; text-transform: uppercase; }
.status-panel h2, .membership-error h2 { margin: 12px 0 18px; font-size: clamp(2rem, 3.5vw, 3.7rem); font-weight: 560; line-height: 1.04; }
.status-panel > p:not(.status-label,.inline-error) { max-width: 520px; color: #5f6a64; line-height: 1.7; }
.status-panel > button, .membership-error button { display: inline-flex; align-items: center; gap: 10px; min-height: 48px; margin-top: 28px; padding: 0 19px; border-radius: 4px; background: #173d32; color: white; font-weight: 670; }
.status-panel > button:disabled { opacity: .6; }
.benefits { border-top: 1px solid #9fb2a9; }
.benefits h3 { margin: 0; padding: 24px 0; border-bottom: 1px solid #9fb2a9; font-size: .82rem; text-transform: uppercase; }
.benefits article { display: grid; grid-template-columns: 35px 1fr; gap: 12px; padding: 22px 0; border-bottom: 1px solid #9fb2a9; }
.benefits strong { font-size: .95rem; }.benefits p { margin: 8px 0 0; color: #637068; font-size: .86rem; line-height: 1.55; }
.membership-facts { align-self: end; border-top: 1px solid #9fb2a9; }
.membership-facts > div { display: flex; justify-content: space-between; gap: 25px; padding: 18px 0; border-bottom: 1px solid #9fb2a9; }
.membership-facts span { color: #68766f; font-size: .78rem; }.membership-facts strong { overflow-wrap: anywhere; text-align: right; }
.inline-error { margin-top: 20px; color: #943b31; }.admin-note { font-size: .85rem; }.membership-error { padding: 90px 0; border-block: 1px solid #d3d7d3; }.membership-error p { color: #69706b; }
.membership-skeleton { display: grid; gap: 18px; padding: 80px 7vw; background: #e2e5e1; }.membership-skeleton span { width: 50%; height: 70px; background: #cfd5d0; }.membership-skeleton i { width: 75%; height: 15px; background: #cfd5d0; }
@media (max-width: 800px) { .membership-page { width: calc(100% - 44px); padding-top: 55px; } .membership-page > header { grid-template-columns: 1fr; gap: 22px; } .membership-layout { grid-template-columns: 1fr; padding: 65px 24px; } }
</style>
