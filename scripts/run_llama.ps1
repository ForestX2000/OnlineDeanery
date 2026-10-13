$srv = Get-ChildItem C:\llama -Recurse -Filter llama-server.exe -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
if (!$srv) { Write-Error "llama-server.exe not found. Run scripts/install_llama.ps1 first."; exit 1 }
foreach ($f in @("C:\models\PaddleOCR-VL-1.5.gguf", "C:\models\PaddleOCR-VL-1.5-mmproj.gguf")) {
  if (!(Test-Path $f)) { Write-Error "Missing $f. Run scripts/install_llama.ps1 first."; exit 1 }
}
& $srv -m C:\models\PaddleOCR-VL-1.5.gguf --mmproj C:\models\PaddleOCR-VL-1.5-mmproj.gguf --host 127.0.0.1 --port 8080 --temp 0
