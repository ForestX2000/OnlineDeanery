import { useState, useCallback } from "react"
import { useDropzone } from "react-dropzone"
import imageCompression from "browser-image-compression"
import { DocumentType, useAppStore } from "@/store/useAppStore"

import { analyzeDocument } from "@/services/analyzeDocument"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Upload, FileText, X, Loader2 } from "lucide-react"

const DOC_TYPES = [
  { value: "study_certificate", label: "Справка об обучении" },
  { value: "academic_leave", label: "Заявление на академический отпуск" },
  { value: "internship_certificate", label: "Справка о практике" },
]

export function DocumentUploader() {
  const [file, setFile] = useState<File | null>(null)
  const [docType, setDocType] = useState("")
  const [question, setQuestion] = useState("")
  const [isCompressing, setIsCompressing] = useState(false)
  

  const { setStep, setFormData, setResult  } = useAppStore()

  
  const compressImage = async (fileToCompress: File) => {
    if (!fileToCompress.type.startsWith("image/")) return fileToCompress
    
    setIsCompressing(true)
    const options = {
      maxSizeMB: 0.5, 
      maxWidthOrHeight: 1920,
      useWebWorker: true,
    }
    
    try {
      const compressedFile = await imageCompression(fileToCompress, options)
      return compressedFile
    } catch (error) {
      console.error("Ошибка сжатия:", error)
      return fileToCompress 
    } finally {
      setIsCompressing(false)
    }
  }

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const selectedFile = acceptedFiles[0]
    if (selectedFile) {
      const processedFile = await compressImage(selectedFile)
      setFile(processedFile)
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "image/jpeg": [".jpg", ".jpeg"],
      "image/png": [".png"],
      "application/pdf": [".pdf"],
    },
    maxFiles: 1,
  })


const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault()

  if (!file || !docType || !question.trim()) {
    alert("Заполните все поля")
    return
  }

  setFormData({
    file,
    docType: docType as DocumentType,
    question: question.trim(),
  })

  setStep("processing")

  try {
    const result = await analyzeDocument({
      file,
      docType: docType as DocumentType,
      question: question.trim(),
    })

    setResult(result)
  } catch {
    setStep("upload")
    alert("Не удалось обработать документ. Попробуйте ещё раз.")
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
          Загрузите фото документа, и цифровой секретарь проверит его по правилам вуза за секунды.
        </CardDescription>
      </CardHeader>
      
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          
          
          <div className="space-y-2">
            <Label>1. Загрузите документ</Label>
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
                      {isCompressing && " (Оптимизируем...)"}
                    </p>
                  </div>
                  <Button 
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

          
          <div className="space-y-2">
            <Label htmlFor="docType">2. Тип документа</Label>
            <Select value={docType} onValueChange={(value) => setDocType(value ?? "")}>
              <SelectTrigger id="docType" className="h-11">
                <SelectValue placeholder="Выберите тип документа" />
              </SelectTrigger>
              <SelectContent>
                {DOC_TYPES.map((type) => (
                  <SelectItem key={type.value} value={type.value}>
                    {type.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

         
          <div className="space-y-2">
            <Label htmlFor="question">3. Ваш вопрос</Label>
            <Input
              id="question"
              placeholder="Например: Хватит ли этой справки для перевода на 2 курс?"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              className="h-11"
            />
          </div>

          
          <Button 
            type="submit" 
            className="w-full h-12 text-base font-semibold bg-blue-600 hover:bg-blue-700 transition-colors" 
            disabled={!file || !docType || !question || isCompressing}
          >
            {isCompressing ? (
              <>
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                Оптимизация фото...
              </>
            ) : (
              "Отправить цифровому секретарю"
            )}
          </Button>

        </form>
      </CardContent>
    </Card>
  )
}