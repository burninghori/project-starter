import { X } from "lucide-react"

import { IconButton } from "@/components/ui/Button"
import { cn } from "@/lib/cn"
import { useToastStore } from "@/lib/toast-store"

export function Toaster() {
  const toasts = useToastStore((state) => state.toasts)
  const dismiss = useToastStore((state) => state.dismiss)

  return (
    <div className="app-toaster" role="status" aria-live="polite">
      {toasts.map((item) => (
        <div key={item.id} className={cn("app-toast", `app-toast--${item.tone}`)}>
          <div className="app-toast__text">
            <strong>{item.title}</strong>
            {item.reason && <p>{item.reason}</p>}
            {item.requestId && <p className="app-mono">요청 ID {item.requestId}</p>}
          </div>
          <IconButton label="알림 닫기" icon={<X size={16} aria-hidden />} onClick={() => dismiss(item.id)} />
        </div>
      ))}
    </div>
  )
}
