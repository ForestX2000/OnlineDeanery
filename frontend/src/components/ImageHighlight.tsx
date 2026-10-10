import { useState } from "react"

interface HighlightBox {
  field: string
  x: number // в процентах
  y: number // в процентах
  w: number // в процентах
  h: number // в процентах
}

interface Props {
  imageUrl: string
  highlights: HighlightBox[]
}

export function ImageHighlight({ imageUrl, highlights }: Props) {
  const [activeField, setActiveField] = useState<string | null>(null)

  return (
    <div className="relative inline-block rounded-lg overflow-hidden border-2 border-slate-200 shadow-md">
      <img src={imageUrl} alt="Документ" className="max-w-full h-auto block" />
      
      {/* Слой подсветки */}
      {highlights.map((box, idx) => {
        const isActive = activeField === box.field
        return (
          <div
            key={idx}
            onMouseEnter={() => setActiveField(box.field)}
            onMouseLeave={() => setActiveField(null)}
            className={`absolute border-2 transition-all duration-300 cursor-pointer
              ${isActive 
                ? "border-yellow-400 bg-yellow-400/20 shadow-[0_0_15px_rgba(250,204,21,0.5)] z-10" 
                : "border-green-500/50 bg-green-500/10 hover:bg-green-500/20"
              }
            `}
            style={{
              left: `${box.x}%`,
              top: `${box.y}%`,
              width: `${box.w}%`,
              height: `${box.h}%`,
            }}
          >
            {isActive && (
              <div className="absolute -top-8 left-0 bg-slate-900 text-white text-xs px-2 py-1 rounded whitespace-nowrap z-20">
                Найдено: {box.field.replace(/_/g, " ")}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}