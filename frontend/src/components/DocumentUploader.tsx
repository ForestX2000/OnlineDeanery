import { useState, useRef } from "react"
import { useDropzone } from "react-dropzone"
import { useAppStore } from "@/store/useAppStore"
import { analyzeDocument, sendMessage, validateFile, DOCUMENT_LABELS, MAX_FILE_SIZE, MAX_QUESTION_LENGTH } from "../../api"
import type { DocumentType } from "../../api"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Upload, FileText, X } from "lucide-react"

const DOC_TYPES = Object.entries(DOCUMENT_LABELS).map(([value, label]) => ({ value, label }))

export function DocumentUploader() {
  const store = useAppStore()
  const { setStep, setFormData, setResult, error, setError } = store
  const [file, setFile] = useState<File | null>(store.file)
  const [docType, setDocType] = useState<DocumentType | "">(store.docType)
  const [question, setQuestion] = useState(store.question)
  const submitting = useRef(false)

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: (acceptedFiles, rejections) => {
      if (rejections.length) {
        setError("Выберите один файл JPG, PNG или PDF размером до 10 МБ")
        return
      }
      const selectedFile = acceptedFiles[0]
      if (!selectedFile) return
      try {
        validateFile(selectedFile)
        setFile(selectedFile)
        setError(null)
      } catch (error) {
        setError(error instanceof Error ? error.message : "Не удалось выбрать файл")
      }
    },
    accept: {
      "image/jpeg": [".jpg", ".jpeg"],
      "image/png": [".png"],
      "application/pdf": [".pdf"],
    },
    maxFiles: 1,
    maxSize: MAX_FILE_SIZE,
    multiple: false,
  })


  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (submitting.current) return
    if (!question.trim()) {
      setError("Введите вопрос")
      return
    }

    setFormData({
      file,
      docType,
      question: question.trim(),
    })

    submitting.current = true
    setError(null)
    setStep("processing")

    try {
      const result = file
        ? await analyzeDocument({ file, docType, question })
        : await sendMessage(question)

      setResult(result)
    } catch (error) {
      setError(error instanceof Error ? error.message : "Не удалось получить ответ")
      setStep("upload")
    } finally {
      submitting.current = false
    }
  }

  return (
    <Card className="w-full max-w-2xl mx-auto shadow-xl border-slate-200">
      <CardHeader className="space-y-1">
        <CardTitle className="text-2xl font-bold flex items-center gap-2 text-slate-900">
          <FileText className="h-7 w-7 text-blue-600" />
          Онлайн-деканат
        </CardTitle>
        <CardDescription className="text-slate-600">
          Задайте вопрос по правилам вуза. При необходимости приложите документ для проверки его полей.
        </CardDescription>
      </CardHeader>
      
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          
          
          <div className="space-y-2">
            <Label>1. Загрузите документ (необязательно)</Label>
            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200
                ${isDragActive ? "border-blue-500 bg-blue-50/50" : "border-slate-300 hover:border-blue-400 hover:bg-slate-50"}
                ${file ? "bg-green-50/50 border-green-500" : ""}
              `}
            >
              <input {...getInputProps()} />
              {file ? (
                <div className="flex flex-col items-center gap-3 text-green-700">
                  <div className="bg-green-100 p-3 rounded-full">
                    <FileText className="h-8 w-8" />
                  </div>
                  <div className="space-y-1">
                    <p className="font-semibold text-base">{file.name}</p>
                    <p className="text-sm text-green-600">
                      {(file.size / 1024 / 1024).toFixed(2)} МБ 
                    </p>
                  </div>
                  <Button 
                    type="button"
                    variant="ghost" 
                    size="sm" 
                    className="mt-2 text-red-600 hover:text-red-700 hover:bg-red-50" 
                    onClick={(e) => { 
                      e.stopPropagation()
                      setFile(null)
                    }}
                  >
                    <X className="h-4 w-4 mr-1" /> Удалить
                  </Button>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-3 text-slate-500">
                  <div className="bg-slate-100 p-4 rounded-full">
                    <Upload className="h-8 w-8 text-slate-400" />
                  </div>
                  <div className="space-y-1">
                    <p className="font-medium text-slate-700">Перетащите файл сюда или нажмите для выбора</p>
                    <p className="text-xs text-slate-400">Поддерживаются JPG, PNG, PDF (до 10 МБ)</p>
                  </div>
                </div>
              )}
            </div>
          </div>

          
          {file && <div className="space-y-2">
            <Label htmlFor="docType">2. Тип документа (необязательно)</Label>
            <Select value={docType || "auto"} onValueChange={(value) => {
              if (value === null || value === "auto") {
                setDocType("")
              } else if (typeof value === "string" && Object.prototype.hasOwnProperty.call(DOCUMENT_LABELS, value)) {
                setDocType(value as DocumentType)
              }
            }}>
              <SelectTrigger id="docType" className="h-11">
                <SelectValue placeholder="Определить автоматически" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="auto">Определить автоматически</SelectItem>
                {DOC_TYPES.map((type) => (
                  <SelectItem key={type.value} value={type.value}>
                    {type.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>}

         
          <div className="space-y-2">
            <Label htmlFor="question">Ваш вопрос</Label>
            <Input
              id="question"
              required
              maxLength={MAX_QUESTION_LENGTH}
              placeholder="Например: Хватит ли этой справки для перевода на 2 курс?"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              className="h-11"
            />
          </div>

          
          {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
          <Button 
            type="submit" 
            className="w-full h-12 text-base font-semibold bg-blue-600 hover:bg-blue-700 transition-colors" 
            disabled={!question.trim()}
          >
            Отправить цифровому секретарю
          </Button>

        </form>
      </CardContent>
    </Card>
  )
}
