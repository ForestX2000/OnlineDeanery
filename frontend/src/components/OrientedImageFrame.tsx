import type { ReactNode } from "react"
import type { DocumentImage } from "../../api"

interface Props {
  image?: DocumentImage | null
  className?: string
  children: ReactNode
}

/** Rotates the image and its coordinate overlays together using the backend angle. */
export function OrientedImageFrame({ image, className = "relative", children }: Props) {
  const rotation = image?.rotation ?? 0
  const isSideways = rotation === 90 || rotation === 270

  const frameStyle = isSideways && image
    ? { aspectRatio: `${image.height} / ${image.width}` }
    : undefined
  const contentStyle = isSideways && image
    ? {
      position: "absolute" as const,
      left: "50%",
      top: "50%",
      width: `${image.width / image.height * 100}%`,
      transform: `translate(-50%, -50%) rotate(${-rotation}deg)`,
      transformOrigin: "center",
    }
    : rotation === 180 ? { transform: "rotate(180deg)" } : undefined

  return (
    <div className={className} style={frameStyle}>
      <div className="relative w-full" style={contentStyle}>{children}</div>
    </div>
  )
}
