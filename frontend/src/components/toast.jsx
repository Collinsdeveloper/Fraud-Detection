import { useEffect, useState } from 'react'
import { onToast } from './toast'

export function ToastHost() {
  const [items, setItems] = useState([])
  useEffect(() => onToast((event) => {
    setItems((previous) => event.dismiss
      ? previous.filter((item) => item.id !== event.id)
      : [...previous, event])
  }), [])
  return <div className="toast-wrap">
    {items.map((item) => <div key={item.id} className={`toast ${item.kind === 'err' ? 'err' : item.kind === 'warn' ? 'warn' : 'ok'}`}>{item.message}</div>)}
  </div>
}
