import { useState } from "react"
import type { DocumentImage, JsonValue } from "../../api"
import { matchesImageDimensions } from "../../api/highlights"
import type { HighlightBox } from "../../api/highlights"

interface Props {
  imageUrl: string
  name: string
  image?: DocumentImage | null
  fields: Record<string, JsonValue>
  highlights: HighlightBox[]
  activeField: string | null
  selectedField: string | null
  onHoverField: (field: string | null) => void
  onSelectField: (field: string) => void
  fieldLabel: (field: string) => string
}

function displayFieldValue(value: JsonValue | undefined): string {
  if (value === undefined || value === null || value === "") return "не найдено"
  if (typeof value === "boolean") return value ? "Да" : "Нет"
  if (typeof value === "object") return JSON.stringify(value) ?? String(value)
  return String(value)
}

export function ImageHighlight({ imageUrl, name, image, fields, highlights, activeField, selectedField,
  onHoverField, onSelectField, fieldLabel }: Props) {
  const [loaded, setLoaded] = useState<{ url: string; width: number; height: number } | null>(null)
  const [failedUrl, setFailedUrl] = useState<string | null>(null)
  const [activeBox, setActiveBox] = useState<number | null>(null)
  const ready = loaded?.url === imageUrl && failedUrl !== imageUrl
  const aligned = ready && matchesImageDimensions(image, loaded.width, loaded.height)
  const visible = aligned ? highlights : []

  return (
    <figure id="document-preview" className="mb-6 space-y-2">
      <div className="neon-document-frame overflow-hidden rounded-2xl bg-[#04130a]">
        <div className="relative">
          <img src={imageUrl} alt={`Загруженный документ: ${name}`} className="block h-auto w-full"
            style={{ imageOrientation: "from-image" }}
            onLoad={(event) => setLoaded({ url: imageUrl, width: event.currentTarget.naturalWidth, height: event.currentTarget.naturalHeight })}
            onError={() => setFailedUrl(imageUrl)} />
          {visible.map((box, index) => {
            const isActive = activeBox === index || (box.field !== null && activeField === box.field)
            const label = box.field ? fieldLabel(box.field) : box.text || "Область текста"
            const value = box.field ? displayFieldValue(fields[box.field]) : box.text
            const description = `${label}: ${value}${box.confidence === null ? "" : `, уверенность ${Math.round(box.confidence * 100)}%`}`
            const activate = () => { setActiveBox(index); onHoverField(box.field) }
            const deactivate = () => { setActiveBox(null); onHoverField(null) }
            return (
              <button key={index} type="button" aria-label={description} title={description}
                aria-pressed={box.field ? selectedField === box.field : undefined}
                onMouseEnter={activate} onMouseLeave={deactivate} onFocus={activate} onBlur={deactivate}
                onClick={() => { if (box.field) onSelectField(box.field) }}
                className={`absolute border-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#159957] ${isActive
                  ? "neon-field-box-active z-10" : "neon-field-box"}`}
                style={{ left: `${box.left}%`, top: `${box.top}%`, width: `${box.width}%`, height: `${box.height}%` }}>
                <span className="pointer-events-none absolute bottom-full left-[-2px] whitespace-nowrap rounded-t bg-[#087b45] px-1.5 py-1 text-[10px] font-semibold text-white shadow-[0_0_8px_rgba(8,123,69,0.8)]">
                  {box.field ? `${label}: ${value}` : box.text}
                </span>
              </button>
            )
          })}
        </div>
        {Object.keys(fields).length > 0 && (
          <div className="border-t border-[#159957]/60 bg-[#052111] px-3 py-3 sm:px-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-[#8fe0b2]">Текст и значения, извлечённые моделью</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {Object.entries(fields).map(([field, value]) => (
                <span key={field} className="rounded-md border border-[#159957]/70 bg-[#087b45]/35 px-2 py-1 text-sm text-white shadow-[0_0_8px_rgba(8,123,69,0.38)]">
                  <span className="font-semibold text-[#9de6bb]">{fieldLabel(field)}:</span> {displayFieldValue(value)}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
      <figcaption className="text-sm text-slate-600">
        {failedUrl === imageUrl ? "Не удалось показать фото. Загрузите документ заново." :
          ready && image && !aligned ? "Подсветка недоступна: размеры фото не совпали с координатами распознавания." :
          visible.length ? "Рамки показывают найденные области. Текст и значения модели приведены под изображением." :
          "Координаты текстовых областей не получены. Распознанные поля приведены под изображением."}
      </figcaption>
      {activeField && visible.some((box) => box.field === activeField) &&
        <p className="text-sm font-medium text-[#087b45]" aria-live="polite">На фото: {fieldLabel(activeField)}</p>}
    </figure>
  )
}
