const listeners = new Set()
let idSeq = 0

export function toast(message, kind = 'ok') {
  const id = ++idSeq
  listeners.forEach((fn) => fn({ id, message, kind }))
  window.setTimeout(() => dismiss(id), 4200)
}

export function dismiss(id) {
  listeners.forEach((fn) => fn({ id, dismiss: true }))
}

export function onToast(fn) {
  listeners.add(fn)
  return () => listeners.delete(fn)
}
