import assert from "node:assert/strict"
import { test } from "node:test"
import { canPreviewImage, documentHighlights, isDocumentImage, matchesImageDimensions } from "../api/highlights.ts"

const image = { width: 1600, height: 900, rotation: 90 }
const box = { field: "stamp", text: "", bbox: [800, 450, 1200, 675], confidence: 0.87, source: "yolo", page: 1 }

test("pixel boxes scale to percentages in the original preview plane without a second rotation", () => {
  assert.deepEqual(documentHighlights([box], image), [{ ...box, left: 50, top: 50, width: 25, height: 25 }])
  assert.equal(matchesImageDimensions(image, 1600, 900), true)
  assert.equal(matchesImageDimensions(image, 900, 1600), false)
})

test("spotting text can have no field or calibrated confidence", () => {
  const rawText = { ...box, field: null, text: "Документ", source: "spotting", confidence: null }
  assert.equal(documentHighlights([rawText], image)[0].confidence, null)
  assert.equal(documentHighlights([rawText], image)[0].field, null)
})

test("legacy coordinates and missing image dimensions produce no invented overlays", () => {
  assert.deepEqual(documentHighlights([{ x: 10, y: 20 }], image), [])
  for (const metadata of [undefined, null, {}, { width: 1600, height: 900 }]) {
    assert.deepEqual(documentHighlights([box], metadata), [])
  }
})

test("invalid dimensions, rotations and non-finite geometry are rejected", () => {
  for (const metadata of [{ ...image, width: 0 }, { ...image, height: -1 }, { ...image, width: 1.5 },
    { ...image, width: Infinity }, { ...image, width: "1600" }, { ...image, rotation: 45 }]) {
    assert.equal(isDocumentImage(metadata), false)
    assert.deepEqual(documentHighlights([box], metadata), [])
  }
  for (const bbox of [[-1, 0, 10, 10], [0, -1, 10, 10], [0, 0, 1601, 900], [0, 0, 1600, 901],
    [10, 0, 10, 10], [10, 0, 5, 10], [0, 10, 10, 5], [0, 0, NaN, 10], [0, 0, Infinity, 10],
    ["0", 0, 10, 10], [0, 0, 10]]) {
    assert.deepEqual(documentHighlights([{ ...box, bbox }], image), [])
  }
})

test("invalid sources, confidence, fields and pages are ignored without hiding valid boxes", () => {
  const invalid = [{ ...box, page: 2 }, { ...box, source: "ocr" }, { ...box, confidence: null },
    { ...box, confidence: 1.1 }, { ...box, confidence: -0.1 }, { ...box, confidence: NaN },
    { ...box, confidence: "0.9" }, { ...box, field: 5 }, { ...box, field: " " }, { ...box, text: null }]
  assert.equal(documentHighlights([...invalid, box], image).length, 1)
})

test("PDFs never become image previews, even if supplied with an image filename", () => {
  assert.equal(canPreviewImage({ name: "scan.pdf", type: "application/pdf" }), false)
  assert.equal(canPreviewImage({ name: "scan.png", type: "application/pdf" }), false)
  assert.equal(canPreviewImage({ name: "scan.pdf", type: "image/png" }), false)
  assert.equal(canPreviewImage({ name: "scan.PNG", type: "" }), true)
  assert.equal(canPreviewImage({ name: "scan.jpeg", type: "image/jpeg" }), true)
})
