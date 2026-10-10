import { useAppStore } from "./store/useAppStore"
import { DocumentUploader } from "./components/DocumentUploader"
import { DocumentResult } from "./components/DocumentResult"

function App() {
  // Читаем текущий шаг из глобального состояния
  const { step } = useAppStore()

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      
      {/* Шапка приложения (всегда видна) */}
      <header className="bg-white border-b border-slate-200 py-4 px-6 shadow-sm sticky top-0 z-50">
        <div className="max-w-5xl mx-auto flex items-center gap-3">
          <div className="bg-[#00A651] text-white p-2.5 rounded-xl shadow-md flex items-center justify-center">
            <span className="font-bold text-xl tracking-tight">Онлайн Деканат</span>
          </div>
          <p className="text-xs text-white-500 font-medium">Цифровой секретарь с ИИ</p>
        </div>
      </header>

      
      <main className="flex-1 p-4 md:p-8 flex flex-col items-center justify-start">
        
        
        {step === "upload" && (
          <div className="w-full max-w-2xl animate-in fade-in slide-in-from-bottom-4 duration-500">
            <DocumentUploader />
          </div>
        )}
        
        
        {step === "processing" && (
          <div className="flex flex-col items-center justify-center h-[60vh] gap-6 animate-in fade-in zoom-in-95 duration-500">
            <div className="relative">
              <div className="absolute inset-0 bg-blue-500 blur-2xl opacity-20 animate-pulse rounded-full"></div>
              
              <div className="relative animate-spin rounded-full h-16 w-16 border-4 border-slate-200 border-t-blue-600"></div>
            </div>
            
            <div className="text-center space-y-2 max-w-md px-4">
              <h2 className="text-xl font-semibold text-slate-800">Цифровой секретарь работает</h2>
              <p className="text-slate-500 leading-relaxed">
                Распознаём текст на документе, извлекаем поля и сверяем их с Положением вуза...
              </p>
            </div>
          </div>
        )}
        
        
        {step === "result" && (
          <div className="w-full max-w-4xl animate-in fade-in slide-in-from-bottom-8 duration-500">
            <DocumentResult />
          </div>
        )}

      </main>
    </div>
  )
}

export default App