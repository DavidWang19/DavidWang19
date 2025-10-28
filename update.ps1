#!/usr/bin/env pwsh
# Profile Statistics Update Script
# 运行此脚本以更新统计数据并推送到 GitHub

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  GitHub Profile Stats Updater" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Python 是否安装
Write-Host "🔍 检查环境..." -ForegroundColor Yellow
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "❌ 错误: 未找到 Python，请先安装 Python 3.8+" -ForegroundColor Red
    exit 1
}

$pythonVersion = python --version
Write-Host "✅ 找到 $pythonVersion" -ForegroundColor Green

# 检查是否安装了依赖
Write-Host ""
Write-Host "🔍 检查依赖..." -ForegroundColor Yellow

# 从 requirements.txt 读取依赖包列表
$requiredPackages = @()
if (Test-Path "requirements.txt") {
    Get-Content "requirements.txt" | ForEach-Object {
        $line = $_.Trim()
        # 跳过空行和注释
        if ($line -and -not $line.StartsWith("#")) {
            # 提取包名（移除版本号）
            if ($line -match '^([a-zA-Z0-9_-]+)') {
                $requiredPackages += $matches[1]
            }
        }
    }
} else {
    Write-Host "❌ 错误: 未找到 requirements.txt" -ForegroundColor Red
    exit 1
}

$pipList = pip list 2>&1 | Out-String
$missingDeps = @()
foreach ($package in $requiredPackages) {
    # 使用更精确的匹配：包名后面跟着空格或行尾
    if ($pipList -notmatch "(?m)^$package\s+") {
        $missingDeps += $package
    }
}

if ($missingDeps.Count -gt 0) {
    Write-Host "⚠️  发现缺失的依赖: $($missingDeps -join ', ')" -ForegroundColor Yellow
    Write-Host "📦 正在安装依赖..." -ForegroundColor Yellow
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ 依赖安装失败" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ 依赖安装完成" -ForegroundColor Green
} else {
    Write-Host "✅ 所有依赖已安装" -ForegroundColor Green
}

# 检查 .env 文件
Write-Host ""
Write-Host "🔍 检查配置文件..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Write-Host "⚠️  未找到 .env 文件" -ForegroundColor Yellow
    Write-Host "📝 正在创建 .env 文件模板..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "❌ 请先编辑 .env 文件，填入您的 API 密钥，然后重新运行此脚本" -ForegroundColor Red
    exit 1
}
Write-Host "✅ 配置文件存在" -ForegroundColor Green

# 运行统计脚本
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "📊 开始生成统计数据..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Push-Location scripts
python main.py
$exitCode = $LASTEXITCODE
Pop-Location

if ($exitCode -ne 0) {
    Write-Host ""
    Write-Host "❌ 统计数据生成失败" -ForegroundColor Red
    exit 1
}

# 检查是否有更改
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🔍 检查文件更改..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

git add figures/
$status = git status --porcelain

if ([string]::IsNullOrWhiteSpace($status)) {
    Write-Host "ℹ️  没有检测到更改，无需提交" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "可能的原因：" -ForegroundColor Yellow
    Write-Host "  - 图表数据没有变化" -ForegroundColor Gray
    Write-Host "  - figures 目录中的文件已经是最新的" -ForegroundColor Gray
    exit 0
}

Write-Host "📝 检测到以下更改：" -ForegroundColor Yellow
git status --short

# 提交更改
Write-Host ""
Write-Host "💾 提交更改..." -ForegroundColor Yellow
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
git commit -m "🤖 Update profile statistics - $timestamp"

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 提交失败" -ForegroundColor Red
    exit 1
}

Write-Host "✅ 提交成功" -ForegroundColor Green

# 推送到远程仓库
Write-Host ""
Write-Host "🚀 推送到 GitHub..." -ForegroundColor Yellow
git push

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 推送失败，请检查网络连接或远程仓库权限" -ForegroundColor Red
    Write-Host "💡 提示: 您可以稍后手动运行 'git push' 来推送更改" -ForegroundColor Cyan
    exit 1
}

Write-Host "✅ 推送成功！" -ForegroundColor Green

# 完成
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ✨ 更新完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "您的 GitHub Profile 统计数据已更新并推送到远程仓库" -ForegroundColor Cyan
Write-Host "访问 https://github.com/DavidWang19 查看您的 Profile" -ForegroundColor Cyan
Write-Host ""
