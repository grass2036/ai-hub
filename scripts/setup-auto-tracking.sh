#!/bin/bash

# 一键设置自动进度追踪系统

echo "🚀 设置自动工作进度追踪系统"
echo "================================"
echo ""

PROJECT_DIR="/Users/chiyingjie/code/git/ai-hub"
cd "$PROJECT_DIR" || exit 1

# 1. 设置 Git hooks
echo "📌 步骤 1/3: 设置 Git Hooks"
if [ -f ".git/hooks/post-commit" ]; then
    echo "   ✅ Git post-commit hook 已存在"
else
    cp scripts/git-auto-log.sh .git/hooks/post-commit
    chmod +x .git/hooks/post-commit
    echo "   ✅ Git post-commit hook 已创建"
fi
echo ""

# 2. 设置每日自动汇总
echo "📌 步骤 2/3: 设置每日自动汇总"

PLIST_FILE="$HOME/Library/LaunchAgents/com.aihub.autotrack.plist"

cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.aihub.autotrack</string>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$PROJECT_DIR/scripts/auto-track-progress.sh</string>
    </array>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>23</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>RunAtLoad</key>
    <false/>

    <key>StandardOutPath</key>
    <string>/tmp/aihub-autotrack.log</string>

    <key>StandardErrorPath</key>
    <string>/tmp/aihub-autotrack-error.log</string>
</dict>
</plist>
EOF

launchctl unload "$PLIST_FILE" 2>/dev/null
launchctl load "$PLIST_FILE"

echo "   ✅ 每日23:00自动汇总任务已设置"
echo ""

# 3. 创建进度缓存文件
echo "📌 步骤 3/3: 初始化缓存"
touch .daily-progress-cache.log
echo "   ✅ 进度缓存文件已创建"
echo ""

echo "🎉 自动追踪系统设置完成！"
echo ""
echo "📋 工作原理："
echo "   1️⃣  每次 git commit 后 → 自动记录提交信息到缓存"
echo "   2️⃣  每天 23:00 → 自动分析今日代码变化"
echo "   3️⃣  自动生成工作日志 → 更新到 daily-log.md"
echo ""
echo "🧪 测试命令："
echo "   手动运行分析: bash scripts/auto-track-progress.sh"
echo "   测试 Git hook: git commit --allow-empty -m 'test: 测试自动追踪'"
echo ""
echo "📊 查看缓存: cat .daily-progress-cache.log"
echo "📝 查看日志: code docs/progress/daily-log.md"
echo ""
