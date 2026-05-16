# Agent Platform - 快速启动脚本 (Windows PowerShell)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Agent Platform - 快速启动" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查配置文件
Write-Host "[1/4] 检查配置文件..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Write-Host "  [!] .env 文件不存在" -ForegroundColor Red
    Write-Host "  [i] 正在从模板创建 .env 文件..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "  [OK] .env 文件已创建，请编辑配置后重新运行" -ForegroundColor Green
    Write-Host ""
    Write-Host "  编辑命令: notepad .env" -ForegroundColor Cyan
    exit 1
} else {
    Write-Host "  [OK] .env 文件已存在" -ForegroundColor Green
}

# 检查Go环境
Write-Host ""
Write-Host "[2/4] 检查Go环境..." -ForegroundColor Yellow
try {
    $goVersion = go version
    Write-Host "  [OK] $goVersion" -ForegroundColor Green
} catch {
    Write-Host "  [!] Go 未安装，请先安装 Go >= 1.23" -ForegroundColor Red
    Write-Host "  下载地址: https://golang.org/dl/" -ForegroundColor Cyan
    exit 1
}

# 检查Python环境
Write-Host ""
Write-Host "[3/4] 检查Python环境..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version
    Write-Host "  [OK] $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  [!] Python 未安装，请先安装 Python >= 3.11" -ForegroundColor Red
    Write-Host "  下载地址: https://www.python.org/downloads/" -ForegroundColor Cyan
    exit 1
}

# 检查依赖
Write-Host ""
Write-Host "[4/4] 检查项目依赖..." -ForegroundColor Yellow

# Go依赖
if (-not (Test-Path "go.sum")) {
    Write-Host "  [i] 正在下载Go依赖..." -ForegroundColor Yellow
    go mod download
}

# Python依赖
Write-Host "  [i] 检查Python依赖..." -ForegroundColor Yellow
Set-Location "agent"
if (Test-Path "requirements.txt") {
    python -m pip install -r requirements.txt --quiet
}
Set-Location ".."

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  环境检查完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 启动选项
Write-Host "请选择启动模式:" -ForegroundColor Cyan
Write-Host "  1. 启动所有服务 (Go Gateway + Python Agent)" -ForegroundColor White
Write-Host "  2. 仅启动 Go Gateway" -ForegroundColor White
Write-Host "  3. 仅启动 Python Agent" -ForegroundColor White
Write-Host "  4. 退出" -ForegroundColor White
Write-Host ""

$choice = Read-Host "请输入选项 (1-4)"

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "启动所有服务..." -ForegroundColor Green
        
        # 启动Python Agent
        Write-Host ""
        Write-Host "[启动 Python Agent (端口8001)]" -ForegroundColor Cyan
        Start-Process -FilePath "python" -ArgumentList "main.py" -WorkingDirectory "agent" -NoNewWindow
        
        Start-Sleep -Seconds 2
        
        # 启动Go Gateway
        Write-Host ""
        Write-Host "[启动 Go Gateway (端口8080)]" -ForegroundColor Cyan
        Set-Location "cmd/gateway"
        go run main.go
    }
    "2" {
        Write-Host ""
        Write-Host "启动 Go Gateway..." -ForegroundColor Green
        Set-Location "cmd/gateway"
        go run main.go
    }
    "3" {
        Write-Host ""
        Write-Host "启动 Python Agent..." -ForegroundColor Green
        Set-Location "agent"
        python main.py
    }
    "4" {
        Write-Host "退出" -ForegroundColor Yellow
        exit 0
    }
    default {
        Write-Host "无效选项" -ForegroundColor Red
        exit 1
    }
}
