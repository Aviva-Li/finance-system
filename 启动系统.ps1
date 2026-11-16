# ============================================================
#  个人理财系统 · 一键启动脚本（Windows PowerShell）
#  功能：自动初始化 Python 后端依赖 + 前端 npm 依赖，
#        同时启动后端(0.0.0.0:8000)与前端 dev(0.0.0.0:5173)，
#        并打印本机 / 局域网访问地址。
#  用法：右键「使用 PowerShell 运行」，或在终端执行：
#        powershell -ExecutionPolicy Bypass -File 启动系统.ps1
# ============================================================
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $root 'backend'
$frontendDir = Join-Path $root 'frontend'

Write-Host ""
Write-Host "=== 个人理财系统 启动中 ===" -ForegroundColor Cyan

# ---------- 1. 后端依赖 ----------
Write-Host "[1/4] 检查后端依赖 (Python venv + pip) ..." -ForegroundColor Yellow
$venvDir = Join-Path $backendDir '.venv'
$venvPy = Join-Path $venvDir 'Scripts\python.exe'
if (!(Test-Path $venvPy)) {
    if (Get-Command py -ErrorAction SilentlyContinue) { & py -m venv $venvDir }
    else { & python -m venv $venvDir }
    & $venvPy -m pip install --quiet --upgrade pip
}
# 优先使用清华 PyPI 镜像，国内网络安装更快更稳（仅对该 venv 生效）
& $venvPy -m pip config --site set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple | Out-Null
& $venvPy -m pip install --quiet --disable-pip-version-check -r (Join-Path $backendDir 'requirements.txt')

# ---------- 2. 前端依赖 ----------
Write-Host "[2/4] 检查前端依赖 (npm install) ..." -ForegroundColor Yellow
if (!(Test-Path (Join-Path $frontendDir 'node_modules'))) {
    Push-Location $frontendDir
    npm install --no-fund --no-audit
    Pop-Location
}

# ---------- 3. 释放端口 ----------
Write-Host "[3/4] 释放端口 8000 / 5173 (清理旧进程) ..." -ForegroundColor Yellow
Get-NetTCPConnection -LocalPort 8000, 5173 -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 1

# ---------- 4. 启动后端 ----------
Write-Host "[4/4] 启动后端 (0.0.0.0:8000) ..." -ForegroundColor Yellow
$logFile = Join-Path $backendDir 'uvicorn.log'
$errFile = Join-Path $backendDir 'uvicorn.err.log'
Start-Process -FilePath $venvPy `
    -ArgumentList '-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8000' `
    -WorkingDirectory $backendDir -WindowStyle Minimized `
    -RedirectStandardOutput $logFile -RedirectStandardError $errFile

# 等待后端真正就绪（最多 20 秒）
$backendReady = $false
for ($i = 0; $i -lt 40; $i++) {
    try {
        Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 2 | Out-Null
        $backendReady = $true
        break
    } catch { Start-Sleep -Milliseconds 500 }
}
if (!$backendReady) {
    Write-Host "后端启动失败，请查看日志：$errFile" -ForegroundColor Red
    Read-Host "按回车退出"
    exit 1
}

# 探测本机局域网 IP（UDP 连接只取本机出口地址，不会真正发包）
$lanIp = '127.0.0.1'
try {
    $udp = New-Object System.Net.Sockets.UdpClient
    $udp.Connect('223.5.5.5', 53)
    $lanIp = $udp.Client.LocalEndPoint.Address.ToString()
    $udp.Close()
} catch {
    try {
        $lanIp = (Get-NetIPAddress -AddressFamily IPv4 |
            Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } |
            Sort-Object InterfaceMetric | Select-Object -First 1).IPAddress
    } catch {}
}

Write-Host ""
Write-Host "=== 后端已启动，启动前端后访问地址如下 ===" -ForegroundColor Green
Write-Host "  本机访问:     http://localhost:5173" -ForegroundColor White
Write-Host "  局域网访问:   http://${lanIp}:5173" -ForegroundColor Cyan
Write-Host "  （同一 WiFi 下，手机 / 其他电脑直接打开局域网地址）" -ForegroundColor Gray
Write-Host "  后端 API:     http://localhost:8000   (接口文档 /docs)" -ForegroundColor Gray
Write-Host "  默认访问密码: 123456（登录后可在「系统设置」修改）" -ForegroundColor Gray
Write-Host ""
Write-Host "  外网访问: 后续可把前后端部署到云服务器，或用 frp / ngrok 内网穿透。" -ForegroundColor Gray
Write-Host "  打不开时: 请在 Windows 防火墙中放行 5173 与 8000 端口。" -ForegroundColor Gray
Write-Host "  关闭系统: 在本窗口按 Ctrl+C 结束前端，再结束已最小化的后端窗口（或直接关电脑）。" -ForegroundColor Gray
Write-Host "  后端日志: $logFile" -ForegroundColor Gray
Write-Host ""
Write-Host "=== 启动前端 dev server (0.0.0.0:5173)，以下为 vite 输出 ===" -ForegroundColor Cyan
Write-Host ""

Push-Location $frontendDir
npm run dev
Pop-Location
