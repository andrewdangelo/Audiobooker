// Custom hook for toast notifications

import { toast as showToast } from '../components/ui/toast'

export function useToast() {
  const toast = (options: { title: string; description?: string }) => {
    showToast(options)
  }

  return { toast }
}
