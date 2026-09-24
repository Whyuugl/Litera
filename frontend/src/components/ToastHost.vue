<script setup lang="ts">
import { CheckCircle2, CircleAlert, X } from "@lucide/vue";
import { dismissToast, toasts } from "../toast";
</script>
<template><div class="toast-host" aria-live="polite"><div v-for="toast in toasts" :key="toast.id" class="toast" :class="toast.tone"><CheckCircle2 v-if="toast.tone === 'success'" :size="18" /><CircleAlert v-else :size="18" /><span>{{ toast.message }}</span><button type="button" aria-label="Dismiss notification" @click="dismissToast(toast.id)"><X :size="16" /></button></div></div></template>
<style scoped>
.toast-host { position: fixed; z-index: 100; right: 24px; bottom: 24px; display: grid; gap: 9px; width: min(360px, calc(100vw - 40px)); }
.toast { display: grid; grid-template-columns: auto 1fr auto; gap: 11px; align-items: center; padding: 15px; border: 1px solid #cad0cb; background: white; box-shadow: 0 15px 35px rgba(26,34,29,.14); font-size: .85rem; }.toast.success > svg { color: #3c6954; }.toast.error > svg { color: #a5483c; }.toast button { display: grid; padding: 3px; place-items: center; background: transparent; }
@media (max-width: 500px) { .toast-host { right: 20px; bottom: 20px; } }
</style>
