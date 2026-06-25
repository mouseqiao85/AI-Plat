@echo off
chcp 65001 >nul 2>nul
REM fin-assistant 一键启动脚本 (Windows)
REM 同时启动后端 (uvicorn :8000) 和前端 (vite :5173)

setlocal enabledelayedexpansion
set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%backend"
set "FRONTEND_DIR=%ROOT_DIR%frontend"

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo   fin-assistant 启动中...
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

REM ── Step 1: 检查 .env ──────────────────────────────────────────────────
if not exist "%BACKEND_DIR%\.env" (
    echo [!] 未检测到 backend\.env 文件
    if exist "%ROOT_DIR%.env.example" (
        copy "%ROOT_DIR%.env.example" "%BACKEND_DIR%\.env" >nul
        echo [+] 已从 .env.example 创建 backend\.env
        echo     请编辑 backend\.env 填入实际密钥后重新启动
        echo.
        start notepad "%BACKEND_DIR%\.env"
        pause
        exit /b 1
    ) else (
        echo [X] 未找到 .env.example 模板，请手动创建 backend\.env
        pause
        exit /b 1
    )
)

REM 快速检查 LLM_API_KEY
findstr /c:"LLM_API_KEY=your-api-key-here" "%BACKEND_DIR%\.env" >nul 2>nul
if !errorlevel! == 0 (
    echo [!] 警告: LLM_API_KEY 未配置，聊天功能将不可用
    echo.
)

REM ── Step 2: 检查依赖 ──────────────────────────────────────────────────
echo [1/4] 检查 Python 依赖...
cd /d "%BACKEND_DIR%"
pip install -q -r requirements.txt 2>nul

echo [2/4] 检查 Node 依赖...
cd /d "%FRONTEND_DIR%"
if not exist "node_modules" (
    call npm install
)

REM ── Step 3: 启动服务 ──────────────────────────────────────────────────
echo [3/4] 启动后端 uvicorn :8000 ...
start "fin-backend" /D "%BACKEND_DIR%" cmd /c "python -m uvicorn app.main:app --reload --port 8000 --host 0.0.0.0"

timeout /t 3 /nobreak >nul

echo [4/4] 启动前端 vite :5173 ...
start "fin-frontend" /D "%FRONTEND_DIR%" cmd /c "npm run dev"

timeout /t 2 /nobreak >nul

echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo   后端:    http://localhost:8000
echo   前端:    http://localhost:5173
echo   API文档: http://localhost:8000/docs
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo   关闭弹出的终端窗口即可停止对应服务
echo.
pause
