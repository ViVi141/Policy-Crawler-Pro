# ==============================================================================
# MNR Law Crawler Online - 快速启动脚本 (Windows PowerShell)
# ==============================================================================
#
# 项目名称: MNR Law Crawler Online (自然资源部法规爬虫系统 - Web版)
# 项目地址: https://github.com/ViVi141/MNR-Law-Crawler-Online
# 作者: ViVi141
# 许可证: MIT License
#
# 描述: 该脚本用于Windows环境下快速启动完整的应用栈
#       包括后端服务、前端服务和自动打开浏览器访问应用
#
# 使用方法: .\快速启动.ps1
#
# ==============================================================================

# MNR Law Crawler - 快速启动脚本

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "MNR Law Crawler - 快速启动" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查后端是否已运行
$backendPort = 8000
$backendRunning = Get-NetTCPConnection -LocalPort $backendPort -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Listen" }

if ($backendRunning) {
    Write-Host "✓ 后端服务已在运行 (端口 $backendPort)" -ForegroundColor Green
} else {
    Write-Host "正在启动后端服务..." -ForegroundColor Yellow
    
    # 启动后端
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD\backend'; .\启动后端.ps1" -WindowStyle Normal
    Write-Host "后端服务启动中，请等待 5-10 秒..." -ForegroundColor Yellow
    Start-Sleep -Seconds 8
    
    # 再次检查
    $backendRunning = Get-NetTCPConnection -LocalPort $backendPort -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Listen" }
    if ($backendRunning) {
        Write-Host "✓ 后端服务启动成功" -ForegroundColor Green
    } else {
        Write-Host "⚠ 后端服务可能启动失败，请检查后端窗口的错误信息" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "正在启动前端服务..." -ForegroundColor Yellow

# 启动前端
Set-Location frontend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; npm run dev" -WindowStyle Normal

Set-Location ..

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "服务启动完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "访问地址：" -ForegroundColor Yellow
Write-Host "  前端: http://localhost:3000" -ForegroundColor White
Write-Host "  后端API: http://localhost:8000" -ForegroundColor White
Write-Host "  API文档: http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "默认账号：" -ForegroundColor Yellow
Write-Host "  用户名: admin" -ForegroundColor White
Write-Host "  密码: admin123" -ForegroundColor White
Write-Host ""
Write-Host "提示：如果前端无法连接后端，请确认后端服务已正常启动" -ForegroundColor Cyan
Write-Host ""

