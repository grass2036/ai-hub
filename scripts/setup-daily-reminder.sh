#!/bin/bash

# 设置每日23点自动提醒
# 使用 launchd (macOS 推荐方式)

echo "🔧 正在设置每日23点自动提醒..."
echo ""

# 创建 launchd plist 文件
PLIST_FILE="$HOME/Library/LaunchAgents/com.aihub.dailyreminder.plist"
SCRIPT_PATH="/Users/chiyingjie/code/git/ai-hub/scripts/auto-daily-reminder.sh"

# 检查脚本是否存在
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "❌ 错误: 找不到提醒脚本"
    echo "   路径: $SCRIPT_PATH"
    exit 1
fi

# 创建 plist 配置
cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.aihub.dailyreminder</string>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$SCRIPT_PATH</string>
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
    <string>/tmp/aihub-daily-reminder.log</string>

    <key>StandardErrorPath</key>
    <string>/tmp/aihub-daily-reminder-error.log</string>
</dict>
</plist>
EOF

echo "✅ 已创建 launchd 配置文件"
echo "   位置: $PLIST_FILE"
echo ""

# 加载配置
launchctl unload "$PLIST_FILE" 2>/dev/null  # 先卸载（如果存在）
launchctl load "$PLIST_FILE"

if [ $? -eq 0 ]; then
    echo "✅ 自动提醒已启用！"
    echo ""
    echo "⏰ 提醒时间: 每天 23:00"
    echo "📝 功能: 弹出通知提醒你更新工作日志"
    echo ""
    echo "📋 管理命令:"
    echo "   查看状态: launchctl list | grep dailyreminder"
    echo "   停止提醒: launchctl unload $PLIST_FILE"
    echo "   启动提醒: launchctl load $PLIST_FILE"
    echo "   查看日志: tail -f /tmp/aihub-daily-reminder.log"
    echo ""
    echo "🧪 测试提醒: bash $SCRIPT_PATH"
    echo ""
else
    echo "❌ 启用失败，请检查权限"
    exit 1
fi
