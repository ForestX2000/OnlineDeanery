import { useState } from "react"
import type { DocumentImage } from "../../api"
import { matchesImageDimensions } from "../../api/highlights"
import type { HighlightBox } from "../../api/highlights"

interface Props {
  imageUrl: string
  name: string
  image?: DocumentImage | null
  highlights: HighlightBox[]
  activeField: string | null
  selectedField: string | null
  onHoverField: (field: string | null) => void
  onSelectField: (field: string) => void
  fieldLabel: (field: string) => string
}

export function ImageHighlight({ imageUrl, name, image, highlights, activeField, selectedField,
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
            const description = `${label}${box.confidence === null ? "" : `, уверенность ${Math.round(box.confidence * 100)}%`}`
            const activate = () => { setActiveBox(index); onHoverField(box.field) }
            const deactivate = () => { setActiveBox(null); onHoverField(null) }
            return <button key={index} type="button" aria-label={description} title={description}
              aria-pressed={box.field ? selectedField === box.field : undefined}
              onMouseEnter={activate} onMouseLeave={deactivate} onFocus={activate} onBlur={deactivate}
              onClick={() => { if (box.field) onSelectField(box.field) }}
              className={`absolute border-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lime-200 ${isActive
                ? "neon-field-box-active z-10" : "neon-field-box"}`}
              style={{ left: `${box.left}%`, top: `${box.top}%`, width: `${box.width}%`, height: `${box.height}%` }} />
          })}
        </div>
      </div>
      <figcaption className="text-sm text-slate-600">
        {failedUrl === imageUrl ? "Не удалось показать фото. Загрузите документ заново." :
          ready && image && !aligned ? "Подсветка недоступна: размеры фото не совпали с координатами распознавания." :
          visible.length ? "Выберите поле в таблице или область на фото. Жёлтым выделены связанные области." :
          "Для этого фото координаты областей не получены. Распознанные поля приведены ниже."}
      </figcaption>
      {activeField && visible.some((box) => box.field === activeField) &&
        <p className="text-sm font-medium text-[#087b45]" aria-live="polite">На фото: {fieldLabel(activeField)}</p>}
    </figure>
  )
}
