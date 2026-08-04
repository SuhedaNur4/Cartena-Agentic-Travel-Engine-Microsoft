#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Cartena başlatma scripti — Docker (Ollama) entegreli.
.USAGE
    .\start.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot

Write-Host ""
Write-Host "  Cartena AI - Baslatiliyor..." -ForegroundColor Cyan
Write-Host ""

Write-Host "  [1/2] Yapay Zeka (Ollama) baglantisi hazirlaniyor..." -ForegroundColor Yellow
$ollamaUrl = "http://localhost:11434/v1"
$envPath = Join-Path $ProjectRoot ".env"
Write-Host "         .env dosyasi korundu. Eger model hatasi alirsaniz Ollama veya Foundry'nin calistigindan emin olun." -ForegroundColor Green

Write-Host "  [2/2] Backend baslatiliyor (http://localhost:8000)..." -ForegroundColor Yellow
Write-Host ""
Set-Location $ProjectRoot
& ".\.venv\Scripts\python.exe" -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
