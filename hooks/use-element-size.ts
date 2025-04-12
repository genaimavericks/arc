import { useState, useEffect, RefObject } from "react"

export function useElementSize<T extends HTMLElement = HTMLDivElement>(
  ref: RefObject<T | null>
) {
  const [size, setSize] = useState<{ width: number; height: number }>({
    width: 0,
    height: 0,
  })

  useEffect(() => {
    if (!ref.current) return

    const observer = new ResizeObserver(entries => {
      if (entries[0]) {
        const { width, height } = entries[0].contentRect
        setSize({ width, height })
      }
    })

    observer.observe(ref.current)

    return () => {
      observer.disconnect()
    }
  }, [ref])

  return size
}
