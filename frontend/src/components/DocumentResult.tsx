import { useRef, useState } from "react"
import { ApiError, DOCUMENT_LABELS, MAX_QUESTION_LENGTH, sendMessage } from "../../api"
import type { DocumentType, JsonValue } from "../../api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Separator } from "@/components/ui/separator"
import { FileText, AlertTriangle } from "lucide-react"


import { useAppStore } from "@/store/useAppStore"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ImageHighlight } from "@/components/ImageHighlight"
import { documentHighlights } from "../../api/highlights"

const FIELD_LABELS = new Map<string, string>([
  ["student_name", "ФИО студента"],
  ["name", "ФИО студента"],
  ["university", "Учебное заведение"],
  ["program", "Образовательная программа"],
  ["study_form", "Форма обучения"],
  ["study_period", "Период обучения"],
  ["number", "Номер документа"],
  ["document_number", "Номер документа"],
  ["internship_period", "Сроки практики"],
  ["issue_date", "Дата выдачи"],
  ["signature", "Подпись"],
  ["stamp", "Печать"],
  ["group", "Группа"],
  ["course", "Курс"],
  ["reason", "Основание"],
  ["start_date", "Дата начала"],
  ["end_date", "Дата окончания"],
  ["application_date", "Дата заявления"],
  ["organization", "Организация"],
  ["supervisor", "Руководитель"],
  ["grade", "Оценка"],
])

const VERIFICATION_LABELS = new Map<string, string>([
  ["complete", "Обязательные поля заполнены"],
  ["incomplete", "Обнаружены замечания"],
  ["unknown", "Недостаточно данных для проверки"],
])

function fieldLabel(field: string): string {
  return FIELD_LABELS.get(field) ?? field.replace(/_/g, " ")
}

function formatValue(value: JsonValue, field: string): string {
  if (["signature", "stamp"].includes(field)) {
    if (value === null) return "Не проверено"
    if (value === false) return "Не обнаружено"
  }
  if (value === null || value === "") return "не найдено"
  if (typeof value === "boolean") return value ? "Да" : "Нет"
  if (typeof value === "object") return JSON.stringify(value)
  return String(value)
}

function sourceUrl(url?: string | null): string | undefined {
  if (!url) return
  try {
    const parsed = new URL(url)
    if (["https:", "http:"].includes(parsed.protocol)) return parsed.href
  } catch { /* Ссылка необязательна: оставляем текст источника. */ }
}

export function DocumentResult() {
  const { result, reset, setResult, preview } = useAppStore()
  const [selectedField, setSelectedField] = useState<string | null>(null)
  const [hoveredField, setHoveredField] = useState<string | null>(null)
  const [question, setQuestion] = useState("")
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expired, setExpired] = useState(false)
  const submitting = useRef(false)
  const data = result

  if(!data) return null

  const document = data.document
  const photo = preview?.conversationId === data.conversation_id ? preview : null
  const highlights = documentHighlights(document?.coordinates, document?.image)
  const highlightedFields = new Set(photo ? highlights.map((box) => box.field).filter(Boolean) : [])
  const activeField = hoveredField ?? selectedField
  const selectField = (field: string) => setSelectedField((current) => current === field ? null : field)
  const verification = data.verification
  const documentLabel = document?.type
    ? DOCUMENT_LABELS[document.type as DocumentType] ?? document.type
    : "Тип не определён"

  const handleFollowUp = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!question.trim() || submitting.current || expired) return
    submitting.current = true
    setPending(true)
    setError(null)
    try {
      setResult(await sendMessage(question, data.conversation_id))
      setQuestion("")
    } catch (error) {
      setExpired(error instanceof ApiError && error.status === 404)
      setError(error instanceof Error ? error.message : "Не удалось получить ответ")
    } finally {
      submitting.current = false
      setPending(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 p-4">

      {document && <Card className="border-[#087b45]/20 bg-[#087b45]/5 relative overflow-hidden">
      <div className="absolute top-0 left-0 right-0 h-1.5 bg-[#087b45]"></div>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <FileText className="h-5 w-5 text-[#087b45]" />
            Распознанные данные: {documentLabel}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {photo && <ImageHighlight key={photo.url} imageUrl={photo.url} name={photo.name}
            image={document.image} highlights={highlights} activeField={activeField} selectedField={selectedField}
            onHoverField={setHoveredField} onSelectField={selectField} fieldLabel={fieldLabel} />}
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-1/3">Поле документа</TableHead>
                <TableHead>Значение</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {Object.entries(document.fields).map(([key, value]) => (
                <TableRow key={key} className={activeField === key && highlightedFields.has(key) ? "bg-amber-100/70" : undefined}
                  onMouseEnter={() => { if (highlightedFields.has(key)) setHoveredField(key) }}
                  onMouseLeave={() => setHoveredField(null)}>
                  <TableCell className="font-medium">
                    {highlightedFields.has(key) ? <button type="button" className="text-left text-[#087b45] underline decoration-dotted underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2"
                      aria-label={`Показать на фото: ${fieldLabel(key)}`} aria-controls="document-preview"
                      aria-pressed={selectedField === key} onClick={() => selectField(key)}
                      onFocus={() => setHoveredField(key)} onBlur={() => setHoveredField(null)}>
                      {fieldLabel(key)}
                    </button> : fieldLabel(key)}
                  </TableCell>
                  <TableCell>
                    {formatValue(value, key) === "не найдено" ? (
                      <Badge variant="destructive" className="flex items-center gap-1 w-fit">
                        <AlertTriangle className="h-3 w-3" /> не найдено
                      </Badge>
                    ) : (
                      <span className="text-slate-800">
                        {formatValue(value, key)}
                      </span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {Object.keys(document.fields).length === 0 && <p className="text-slate-600">Поля документа не найдены.</p>}
          {document.visual_features?.status === "disabled" && <p className="mt-4 text-sm text-slate-600">
            Проверка подписи и печати не выполнена: модель детекции не подключена.
          </p>}
          {document.visual_features?.status === "error" && <p className="mt-4 text-sm text-slate-600">
            Проверка подписи и печати не выполнена: модель детекции недоступна.
          </p>}
          {verification && <div className="mt-4 space-y-2">
            <p>Статус проверки: {VERIFICATION_LABELS.get(verification.status) ?? verification.status}</p>
            {verification.missing_fields.length > 0 && <p className="text-red-700">Не найдены обязательные поля: {verification.missing_fields.map(fieldLabel).join(", ")}</p>}
            {verification.issues.map((issue, index) => <p key={index} className="text-red-700">{issue}</p>)}
          </div>}
          <p className="mt-4 text-sm text-slate-500">Проверка комплектности не означает принятие документа. Окончательное решение принимает деканат.</p>
        </CardContent>
      </Card>}


      <Card className="border-[#1e293b]/10 bg-white">
        <CardHeader>
          <CardTitle className="text-lg text-[#1e293b]">Ответ цифрового секретаря</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-slate-800 leading-relaxed text-lg whitespace-pre-wrap">
            {data.answer}
          </p>


          {data.sources.length > 0 && (
            <>
              <Separator className="my-4" />
              <div className="space-y-2">
                <p className="text-sm font-semibold text-slate-600 uppercase tracking-wide">
                  Источники информации:
                </p>
                <div className="flex flex-wrap gap-2">
                  {data.sources.map((source, idx) => (
                    <Badge key={idx} variant="outline" className="bg-white text-[#087b45] border-[#087b45]/30">
                      {source.type === "положение" ? "📜 " : "📄 "}
                      {sourceUrl(source.url)
                        ? <a href={sourceUrl(source.url)} target="_blank" rel="noopener noreferrer" className="underline">{source.reference}</a>
                        : source.reference}
                    </Badge>
                  ))}
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
      <form onSubmit={handleFollowUp} className="space-y-3" aria-busy={pending}>
        <Label htmlFor="follow-up">Уточняющий вопрос</Label>
        <Input id="follow-up" value={question} onChange={(event) => setQuestion(event.target.value)}
          required maxLength={MAX_QUESTION_LENGTH} disabled={pending || expired} placeholder="Спросите подробнее по этому обращению" />
        {error && <p role="alert" className="text-red-700">{error}{expired && " Начните новое обращение и приложите документ заново."}</p>}
        <Button type="submit" disabled={pending || expired || !question.trim()}>{pending ? "Получаем ответ..." : "Задать вопрос"}</Button>
      </form>
      <Button type="button" onClick={reset} disabled={pending} variant="outline">Новое обращение</Button>

    </div>
  )
}
