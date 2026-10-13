$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
New-Item -ItemType Directory -Force -Path "$root\models", "C:\llama", "C:\models" | Out-Null
$zip = "C:\llama\llama.zip"
$zipUrl = "https://github.com/ggml-org/llama.cpp/releases/download/b11429/llama-b11429-bin-win-cpu-x64.zip"
if (!(Test-Path $zip)) {
  Invoke-WebRequest -Uri $zipUrl -OutFile $zip
}
Expand-Archive $zip C:\llama -Force
Get-ChildItem C:\llama -Recurse -Filter llama-server.exe | Select-Object FullName
$files = @{
  "$root\models\PaddleOCR-VL-1.6-GGUF.gguf" = "https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6-GGUF/resolve/main/PaddleOCR-VL-1.6-GGUF.gguf"
  "$root\models\PaddleOCR-VL-1.6-GGUF-mmproj.gguf" = "https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6-GGUF/resolve/main/PaddleOCR-VL-1.6-GGUF-mmproj.gguf"
}
foreach ($path in $files.Keys) {
  if (!(Test-Path $path)) {
    Invoke-WebRequest -Uri $files[$path] -OutFile $path
  }
  Get-Item $path | Select-Object FullName, Length
}
