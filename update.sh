#!/bin/bash
# Profile Statistics Update Script
# 运行此脚本以更新统计数据并推送到 GitHub

echo "========================================"
echo "  GitHub Profile Stats Updater"
echo "========================================"
echo ""

# 检查 Python 是否安装
echo "🔍 检查环境..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python，请先安装 Python 3.8+"
    exit 1
fi

python_version=$(python3 --version)
echo "✅ 找到 $python_version"

# 检查是否安装了依赖
echo ""
echo "🔍 检查依赖..."

# 从 requirements.txt 读取依赖包列表
required_packages=()
if [ -f "requirements.txt" ]; then
    while IFS= read -r line; do
        # 跳过空行和注释
        line=$(echo "$line" | xargs)  # 去除首尾空格
        if [[ -n "$line" && ! "$line" =~ ^# ]]; then
            # 提取包名（移除版本号）
            package=$(echo "$line" | sed 's/[><=!].*//' | xargs)
            if [ -n "$package" ]; then
                required_packages+=("$package")
            fi
        fi
    done < requirements.txt
else
    echo "❌ 错误: 未找到 requirements.txt"
    exit 1
fi

missing_deps=()
for package in "${required_packages[@]}"; do
    # 使用更精确的匹配：包名后面跟着空格
    if ! pip3 list 2>/dev/null | grep -q "^$package "; then
        missing_deps+=("$package")
    fi
done

if [ ${#missing_deps[@]} -gt 0 ]; then
    echo "⚠️  发现缺失的依赖: ${missing_deps[*]}"
    echo "📦 正在安装依赖..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ 依赖安装失败"
        exit 1
    fi
    echo "✅ 依赖安装完成"
else
    echo "✅ 所有依赖已安装"
fi

# 检查 .env 文件
echo ""
echo "🔍 检查配置文件..."
if [ ! -f ".env" ]; then
    echo "⚠️  未找到 .env 文件"
    echo "📝 正在创建 .env 文件模板..."
    cp .env.example .env
    echo "❌ 请先编辑 .env 文件，填入您的 API 密钥，然后重新运行此脚本"
    exit 1
fi
echo "✅ 配置文件存在"

# 运行统计脚本
echo ""
echo "========================================"
echo "📊 开始生成统计数据..."
echo "========================================"
echo ""

cd scripts
python3 main.py
exit_code=$?
cd ..

if [ $exit_code -ne 0 ]; then
    echo ""
    echo "❌ 统计数据生成失败"
    exit 1
fi

# 检查是否有更改
echo ""
echo "========================================"
echo "🔍 检查文件更改..."
echo "========================================"
echo ""

git add figures/
status=$(git status --porcelain)

if [ -z "$status" ]; then
    echo "ℹ️  没有检测到更改，无需提交"
    echo ""
    echo "可能的原因："
    echo "  - 图表数据没有变化"
    echo "  - figures 目录中的文件已经是最新的"
    exit 0
fi

echo "📝 检测到以下更改："
git status --short

# 提交更改
echo ""
echo "💾 提交更改..."
timestamp=$(date '+%Y-%m-%d %H:%M:%S')
git commit -m "🤖 Update profile statistics - $timestamp"

if [ $? -ne 0 ]; then
    echo "❌ 提交失败"
    exit 1
fi

echo "✅ 提交成功"

# 推送到远程仓库
echo ""
echo "🚀 推送到 GitHub..."
git push

if [ $? -ne 0 ]; then
    echo "❌ 推送失败，请检查网络连接或远程仓库权限"
    echo "💡 提示: 您可以稍后手动运行 'git push' 来推送更改"
    exit 1
fi

echo "✅ 推送成功！"

# 完成
echo ""
echo "========================================"
echo "  ✨ 更新完成！"
echo "========================================"
echo ""
echo "您的 GitHub Profile 统计数据已更新并推送到远程仓库"
echo "访问 https://github.com/DavidWang19 查看您的 Profile"
echo ""
