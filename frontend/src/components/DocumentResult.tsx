import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Separator } from "@/components/ui/separator"
import { FileText, AlertTriangle, CheckCircle2 } from "lucide-react"


import { useAppStore } from "@/store/useAppStore"
import { Button } from "@base-ui/react"

export function DocumentResult() {
  const {result, reset}= useAppStore()
  const data = result

  if(!data) return null

  return (
    <div className="max-w-4xl mx-auto space-y-6 p-4">
      
      <Card className="border-green-200 bg-green-50/30 relative overflow-hidden">
      <div className="absolute top-0 left-0 right-0 h-1.5 bg-[#00A651]"></div>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <FileText className="h-5 w-5 text-blue-600" />
            Распознанные данные: Справка об обучении
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-1/3">Поле документа</TableHead>
                <TableHead>Значение</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {Object.entries(data.extracted_fields).map(([key, value]) => (
                <TableRow key={key}>
                  <TableCell className="font-medium capitalize">
                    {key.replace(/_/g, " ")}
                  </TableCell>
                  <TableCell>
                    {value === "не найдено" ? (
                      <Badge variant="destructive" className="flex items-center gap-1 w-fit">
                        <AlertTriangle className="h-3 w-3" /> не найдено
                      </Badge>
                    ) : (
                      <span className="text-green-700 flex items-center gap-1">
                        <CheckCircle2 className="h-4 w-4" /> {value}
                      </span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      
      <Card className="border-blue-200 bg-blue-50/50">
        <CardHeader>
          <CardTitle className="text-lg text-blue-900">Ответ цифрового секретаря</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-slate-800 leading-relaxed text-lg">
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
                    <Badge key={idx} variant="outline" className="bg-white text-blue-700 border-blue-300 cursor-pointer hover:bg-blue-100 transition-colors">
                      {source.type === "положение" ? "📜 " : "📄 "}
                      {source.reference}
                    </Badge>
                  ))}
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
      <Button onClick={reset} className="mt-2 text-red-600 hover:text-red-700 hover:bg-red-50" >Проверить другой документ</Button>

    </div>
  )
}