import { ref } from "vue";

export type Toast = { id: number; message: string; tone: "success" | "error" };
export const toasts = ref<Toast[]>([]);
let nextId = 1;

export function notify(message: string, tone: Toast["tone"] = "success") {
  const id = nextId++;
  toasts.value.push({ id, message, tone });
  window.setTimeout(() => { toasts.value = toasts.value.filter((toast) => toast.id !== id); }, 3500);
}

export function dismissToast(id: number) {
  toasts.value = toasts.value.filter((toast) => toast.id !== id);
}
