import { useCallback, useEffect, useRef, useState } from "react"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "./ui/tooltip"
import { cn } from "../lib/utils"

/**
 * 文本溢出才提示的 Tooltip。
 *
 * 用法：把原来「可能被截断」的文本节点直接换成它，保留原 className：
 *   <p className="truncate text-sm">{name}</p>
 *   <OverflowTooltip as="p" className="truncate text-sm" text={name} />
 *
 * 判定方式：scrollWidth > clientWidth（单行 truncate）或
 *          scrollHeight > clientHeight（line-clamp 多行）。没溢出时完全不弹层。
 */
export function OverflowTooltip({
  text,
  children,
  as: Tag = "span",
  className,
  contentClassName,
  side = "top",
  delayDuration = 150,
  ...rest
}) {
  const ref = useRef(null)
  const [overflow, setOverflow] = useState(false)
  const [open, setOpen] = useState(false)

  const measure = useCallback(() => {
    const el = ref.current
    if (!el) return
    const over =
      el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 1
    setOverflow(over)
  }, [])

  useEffect(() => {
    measure()
    const el = ref.current
    if (!el || typeof ResizeObserver === "undefined") return
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    if (el.parentElement) ro.observe(el.parentElement)
    return () => ro.disconnect()
  }, [measure, text, children])

  // 内容变了再量一次（等字体加载完宽度也会变）
  useEffect(() => {
    const timer = setTimeout(measure, 60)
    return () => clearTimeout(timer)
  }, [measure, text, children])

  // children 用于「带图标等子节点」的展示，text 只作为 tooltip 文案
  const body = children ?? text
  const label = text ?? children

  return (
    <TooltipProvider delayDuration={delayDuration}>
      <Tooltip
        open={overflow && open}
        onOpenChange={(next) => setOpen(next && overflow)}
        disableHoverableContent
      >
        <TooltipTrigger asChild>
          <Tag ref={ref} className={className} {...rest}>
            {body}
          </Tag>
        </TooltipTrigger>
        <TooltipContent
          side={side}
          className={cn("max-w-sm break-words text-xs leading-relaxed", contentClassName)}
        >
          {label}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

export default OverflowTooltip
