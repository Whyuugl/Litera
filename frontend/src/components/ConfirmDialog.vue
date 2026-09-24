<script setup lang="ts">
defineProps<{ open: boolean; title: string; message: string; confirmLabel?: string; destructive?: boolean; busy?: boolean }>();
defineEmits<{ confirm: []; cancel: [] }>();
</script>
<template><Teleport to="body"><div v-if="open" class="dialog-backdrop" @click.self="$emit('cancel')"><section class="confirm-dialog" role="alertdialog" aria-modal="true" :aria-labelledby="'confirm-title'"><h2 id="confirm-title">{{ title }}</h2><p>{{ message }}</p><div><button type="button" :disabled="busy" @click="$emit('cancel')">Cancel</button><button type="button" :class="{ danger: destructive }" :disabled="busy" @click="$emit('confirm')">{{ busy ? 'Working...' : confirmLabel || 'Confirm' }}</button></div></section></div></Teleport></template>
<style scoped>
.dialog-backdrop { position: fixed; z-index: 90; inset: 0; display: grid; padding: 20px; place-items: center; background: rgba(20,26,22,.48); }.confirm-dialog { width: min(470px, 100%); padding: 34px; background: #f7f8f5; }.confirm-dialog h2 { margin: 0 0 13px; font-size: 1.65rem; }.confirm-dialog p { margin: 0; color: #666e68; line-height: 1.65; }.confirm-dialog > div { display: flex; justify-content: flex-end; gap: 10px; margin-top: 30px; }.confirm-dialog button { min-height: 42px; padding: 0 16px; border: 1px solid #b9bfba; border-radius: 3px; background: transparent; }.confirm-dialog button:last-child { border-color: #173d32; background: #173d32; color: white; }.confirm-dialog button.danger { border-color: #a5483c; background: #a5483c; }
</style>
