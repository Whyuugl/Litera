<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { CheckCircle2, UserRound } from "@lucide/vue";
import { api, formatEnum, type Membership, type User } from "../api";

const props = defineProps<{ user: User }>();
const membership = ref<Membership | null>(null);
const initials = computed(() => props.user.name.split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase());
onMounted(async () => { try { membership.value = (await api<{ membership: Membership | null }>("/api/v1/memberships/me")).membership; } catch { membership.value = null; } });
</script>

<template>
  <main class="profile-page">
    <header><p class="eyebrow">Your account</p><h1>A simple place<br />to be known.</h1></header>
    <section class="identity-section">
      <div class="avatar"><img v-if="user.avatar_url" :src="user.avatar_url" alt="" /><span v-else>{{ initials }}</span></div>
      <div class="identity"><h2>{{ user.name }}</h2><p>{{ user.email }}</p><span><CheckCircle2 v-if="user.is_active" :size="15" />{{ user.is_active ? 'Active account' : 'Inactive account' }}</span></div>
    </section>
    <section class="account-details">
      <div><p class="eyebrow">Account details</p><h2>What Litera knows<br />about you.</h2></div>
      <dl><div><dt>Name</dt><dd>{{ user.name }}</dd></div><div><dt>Email</dt><dd>{{ user.email }}</dd></div><div><dt>Account type</dt><dd>{{ formatEnum(user.role) }}</dd></div><div><dt>Account status</dt><dd>{{ user.is_active ? 'Active' : 'Inactive' }}</dd></div><div><dt>Membership</dt><dd>{{ membership ? formatEnum(membership.status) : 'Not applied' }}</dd></div></dl>
    </section>
    <p class="profile-note"><UserRound :size="17" /> Profile editing is not available yet. Your account information is managed by Litera.</p>
  </main>
</template>

<style scoped>
.profile-page { width: min(1120px, 88vw); min-height: 80vh; margin: auto; padding: 80px 0 120px; }
.profile-page header h1 { margin: 0; font-size: clamp(3.2rem, 6vw, 6rem); font-weight: 560; line-height: .96; }
.identity-section { display: flex; align-items: center; gap: 35px; margin: 75px 0 100px; padding: 45px; background: #dce8e3; }
.avatar { display: grid; width: 110px; height: 110px; flex: none; overflow: hidden; place-items: center; border-radius: 50%; background: #173d32; color: white; font-size: 2rem; font-weight: 700; }.avatar img { width: 100%; height: 100%; object-fit: cover; }
.identity h2 { margin: 0 0 9px; font-size: 2rem; }.identity p { margin: 0; color: #5c6861; }.identity span { display: flex; align-items: center; gap: 7px; margin-top: 18px; color: #53655c; font-size: .78rem; }
.account-details { display: grid; grid-template-columns: .8fr 1.2fr; gap: 9vw; padding-top: 90px; border-top: 1px solid #d3d7d3; }.account-details h2 { margin: 0; font-size: clamp(2rem, 3.5vw, 3.5rem); font-weight: 560; line-height: 1.05; }.account-details dl { margin: 0; border-top: 1px solid #c9ceca; }.account-details dl div { display: flex; justify-content: space-between; gap: 25px; padding: 19px 0; border-bottom: 1px solid #c9ceca; }.account-details dt { color: #737a75; font-size: .8rem; }.account-details dd { margin: 0; overflow-wrap: anywhere; text-align: right; }
.profile-note { display: flex; align-items: center; gap: 9px; margin: 70px 0 0; color: #7a817c; font-size: .8rem; }
@media (max-width: 650px) { .profile-page { width: calc(100% - 44px); padding-top: 55px; }.identity-section { align-items: flex-start; padding: 30px 22px; }.avatar { width: 76px; height: 76px; }.account-details { grid-template-columns: 1fr; gap: 40px; }.account-details dd { max-width: 60%; }.profile-note { align-items: flex-start; } }
</style>
