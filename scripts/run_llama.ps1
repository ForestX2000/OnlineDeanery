$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
# Host-режим (без Docker): сервер рядом, модели из ./models.
$candidates = @(
  "$root\models\PaddleOCR-VL-1.6-GGUF.gguf",
  "C:\models\PaddleOCR-VL-1.6-GGUF.gguf"
) | Where-Object { Test-Path $_ }
$mmprojCandidates = @(
  "$root\models\PaddleOCR-VL-1.6-GGUF-mmproj.gguf",
  "C:\models\PaddleOCR-VL-1.6-GGUF-mmproj.gguf"
) | Where-Object { Test-Path $_ }
if (!$candidates -or !$mmprojCandidates) { Write-Error "GGUF/mmproj not found. Run scripts/install_llama.ps1 first (./models)."; exit 1 }
$model = $candidates | Select-Object -First 1
$mmproj = $mmprojCandidates | Select-Object -First 1
$srv = Get-ChildItem C:\llama -Recurse -Filter llama-server.exe -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
if (!$srv) { Write-Error "llama-server.exe not found. Run scripts/install_llama.ps1 first."; exit 1 }
$threadCount = if ([string]::IsNullOrWhiteSpace($env:LLAMA_THREADS)) { "-1" } else { $env:LLAMA_THREADS }
if ($threadCount -notmatch '^(?:-1|[1-9]\d*)$') { Write-Error "LLAMA_THREADS должен быть -1 (авто) или положительным числом."; exit 1 }
& $srv -m $model --mmproj $mmproj --threads $threadCount --threads-batch $threadCount --host 127.0.0.1 --port 8080 --temp 0
