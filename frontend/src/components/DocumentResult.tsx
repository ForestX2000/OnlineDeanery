import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Separator } from "@/components/ui/separator"
import { FileText, AlertTriangle, CheckCircle2 } from "lucide-react"

import { useAppStore } from "@/store/useAppStore"
import { Button } from "@base-ui/react"

export function DocumentResult() {
  const { result, reset } = useAppStore()
  const data = result

  if (!data) return null

  return (
    <div className="max-w-4xl mx-auto space-y-6 p-4">

      <Card className="border-[#087b45]/20 bg-[#087b45]/5 relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-1.5 bg-[#087b45]"></div>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg text-[#1e293b]">
            <FileText className="h-5 w-5 text-[#087b45]" />
            Распознанные данные: Справка об обучении
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow className="border-[#1e293b]/10 hover:bg-transparent">
                <TableHead className="w-1/3 text-[#1e293b]/70">Поле документа</TableHead>
                <TableHead className="text-[#1e293b]/70">Значение</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {Object.entries(data.extracted_fields).map(([key, value]) => (
                <TableRow key={key} className="border-[#1e293b]/10 hover:bg-[#087b45]/5">
                  <TableCell className="font-medium capitalize text-[#1e293b]">
                    {key.replace(/_/g, " ")}
                  </TableCell>
                  <TableCell>
                    {value === "не найдено" ? (
                      <Badge className="flex items-center gap-1 w-fit bg-amber-100 text-amber-800 border border-amber-200 hover:bg-amber-100">
                        <AlertTriangle className="h-3 w-3" /> не найдено
                      </Badge>
                    ) : (
                      <span className="text-[#087b45] flex items-center gap-1 font-medium">
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

      <Card className="border-[#1e293b]/10 bg-white">
        <CardHeader>
          <CardTitle className="text-lg text-[#1e293b]">Ответ цифрового секретаря</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-[#1e293b] leading-relaxed text-lg">
            {data.answer}
          </p>

          {data.sources.length > 0 && (
            <>
              <Separator className="my-4 bg-[#1e293b]/10" />
              <div className="space-y-2">
                <p className="text-sm font-semibold text-[#1e293b]/70 uppercase tracking-wide">
                  Источники информации:
                </p>
                <div className="flex flex-wrap gap-2">
                  {data.sources.map((source, idx) => (
                    <Badge
                      key={idx}
                      variant="outline"
                      className="bg-white text-[#087b45] border-[#087b45]/30 cursor-pointer hover:bg-[#087b45]/10 transition-colors"
                    >
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

      <Button
        onClick={reset}
        className="mt-2 text-[#1e293b]/70 hover:text-[#1e293b] hover:bg-[#1e293b]/5 transition-colors"
      >
        Проверить другой документ
      </Button>
    </div>
  )
}
