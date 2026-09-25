<script setup lang="ts">
import { ref } from "vue";
import { ArrowLeft, BookOpen, LayoutGrid, Menu, Repeat2, Tags, UserRound, UsersRound, X } from "@lucide/vue";
import type { User } from "../api";

defineProps<{ current: string; user: User }>();
const emit = defineEmits<{ navigate: [path: string]; logout: [] }>();
const open = ref(false);
function go(path: string) { open.value = false; emit("navigate", path); }
</script>
<template>
  <div class="admin-shell">
    <button class="drawer-toggle" type="button" aria-label="Toggle admin navigation" :aria-expanded="open" @click="open = !open"><X v-if="open" :size="21" /><Menu v-else :size="21" /></button>
    <aside :class="{ open }">
      <button class="admin-brand" type="button" @click="go('/admin')">Litera<span>.</span><small>Admin</small></button>
      <nav aria-label="Admin navigation">
        <button :class="{ active: current === '/admin' }" type="button" @click="go('/admin')"><LayoutGrid :size="18" />Overview</button>
        <p>Library</p>
        <button :class="{ active: current.startsWith('/admin/books') }" type="button" @click="go('/admin/books')"><BookOpen :size="18" />Books</button>
        <button :class="{ active: current === '/admin/categories' }" type="button" @click="go('/admin/categories')"><Tags :size="18" />Categories</button>
        <button :class="{ active: current === '/admin/authors' }" type="button" @click="go('/admin/authors')"><UserRound :size="18" />Authors</button>
        <p>Membership</p>
        <button :class="{ active: current.startsWith('/admin/members') }" type="button" @click="go('/admin/members')"><UsersRound :size="18" />Members</button>
        <p>Operations</p>
        <button :class="{ active: current.startsWith('/admin/circulation') || current.startsWith('/admin/loans') || current.startsWith('/admin/reservations') }" type="button" @click="go('/admin/circulation')"><Repeat2 :size="18" />Circulation</button>
      </nav>
      <div class="admin-account"><span>{{ user.name }}</span><small>{{ user.email }}</small><button type="button" @click="go('/home')"><ArrowLeft :size="16" />Back to Litera</button><button type="button" @click="$emit('logout')">Sign out</button></div>
    </aside>
    <div v-if="open" class="drawer-shade" @click="open = false"></div>
    <section class="admin-content"><slot /></section>
  </div>
</template>
<style scoped>
.admin-shell { min-height: 100vh; background: #f4f5f2; }.admin-shell > aside { position: fixed; z-index: 35; inset: 0 auto 0 0; display: flex; flex-direction: column; width: 245px; padding: 31px 24px 24px; border-right: 1px solid #d5d9d5; background: #eef1ed; }.admin-brand { display: flex; align-items: baseline; padding: 0 4px 34px; background: transparent; font-size: 1.45rem; font-weight: 760; }.admin-brand span { color: #6f8a78; }.admin-brand small { margin-left: 10px; color: #798079; font-size: .63rem; font-weight: 700; text-transform: uppercase; }.admin-shell nav { display: grid; gap: 3px; }.admin-shell nav p { margin: 26px 9px 8px; color: #929892; font-size: .62rem; font-weight: 700; text-transform: uppercase; }.admin-shell nav button { display: flex; align-items: center; gap: 11px; min-height: 42px; padding: 0 11px; border-radius: 3px; background: transparent; color: #535b55; text-align: left; }.admin-shell nav button.active { background: #173d32; color: white; }.admin-account { display: grid; margin-top: auto; padding-top: 20px; border-top: 1px solid #d0d5d0; }.admin-account > span { font-size: .83rem; font-weight: 700; }.admin-account small { margin: 4px 0 16px; overflow: hidden; color: #7b827c; text-overflow: ellipsis; }.admin-account button { display: flex; align-items: center; gap: 7px; padding: 8px 0; background: transparent; color: #606862; font-size: .78rem; text-align: left; }.admin-content { min-height: 100vh; margin-left: 245px; }.drawer-toggle { display: none; }.drawer-shade { display: none; }
@media (max-width: 760px) { .drawer-toggle { position: fixed; z-index: 50; top: 16px; right: 18px; display: grid; width: 42px; height: 42px; place-items: center; border: 1px solid #d1d6d1; border-radius: 50%; background: #fff; }.admin-shell > aside { transform: translateX(-100%); transition: transform .2s ease; }.admin-shell > aside.open { transform: translateX(0); }.drawer-shade { position: fixed; z-index: 30; inset: 0; display: block; background: rgba(19,25,21,.35); }.admin-content { margin-left: 0; } }
</style>
