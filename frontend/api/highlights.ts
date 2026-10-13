import type { DocumentCoordinate, DocumentImage } from "./types.ts"

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

export function isDocumentImage(value: unknown): value is DocumentImage {
  return isRecord(value) && Number.isSafeInteger(value.width) && Number(value.width) > 0 &&
    Number.isSafeInteger(value.height) && Number(value.height) > 0 &&
    [0, 90, 180, 270].includes(value.rotation as number)
}

export interface HighlightBox extends DocumentCoordinate {
  left: number
  top: number
  width: number
  height: number
}

/** Coordinates are already in the EXIF-oriented original image plane. Do not rotate again. */
export function documentHighlights(coordinates: unknown, image: unknown): HighlightBox[] {
  if (!isDocumentImage(image) || !Array.isArray(coordinates)) return []
  return coordinates.flatMap((value: unknown) => {
    if (!isRecord(value) || (value.field !== null && (typeof value.field !== "string" || !value.field.trim())) ||
        typeof value.text !== "string" || !["yolo", "spotting", "tesseract", "tesseract_supplement", "color"].includes(value.source as string) ||
        value.page !== 1 || !Array.isArray(value.bbox) || value.bbox.length !== 4 ||
        !value.bbox.every((n: unknown) => typeof n === "number" && Number.isFinite(n)) ||
        !(value.confidence === null || (typeof value.confidence === "number" &&
          Number.isFinite(value.confidence) && value.confidence >= 0 && value.confidence <= 1)) ||
        (value.source === "yolo" && value.confidence === null)) return []

    const [x1, y1, x2, y2] = value.bbox as [number, number, number, number]
    if (x1 < 0 || y1 < 0 || x2 > image.width || y2 > image.height || x2 <= x1 || y2 <= y1) return []
    return [{
      field: value.field as string | null, text: value.text,
      bbox: [x1, y1, x2, y2] as [number, number, number, number],
      confidence: value.confidence as number | null, source: value.source as DocumentCoordinate["source"], page: 1 as const,
      left: x1 / image.width * 100, top: y1 / image.height * 100,
      width: (x2 - x1) / image.width * 100, height: (y2 - y1) / image.height * 100,
    }]
  })
}

export function canPreviewImage(file: Pick<File, "name" | "type">): boolean {
  return /\.(jpe?g|png)$/i.test(file.name) && ["", "image/png", "image/jpeg"].includes(file.type)
}

export function matchesImageDimensions(image: unknown, width: number, height: number): boolean {
  return isDocumentImage(image) && image.width === width && image.height === height
}
