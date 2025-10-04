#!/bin/bash

# 自动化每日工作日志提醒脚本
# 用途：每天23点自动弹出提醒通知

PROJECT_DIR="/Users/chiyingjie/code/git/ai-hub"
LOG_FILE="$PROJECT_DIR/docs/progress/daily-log.md"

# 发送 macOS 通知
osascript -e 'display notification "📝 该更新今天的工作日志了！" with title "AI Hub 开发提醒" sound name "Glass"'

# 等待5秒后再次提醒
sleep 5

# 弹出对话框
response=$(osascript -e 'display dialog "📝 今天的工作日志还没更新！\n\n是否现在打开 daily-log.md？" buttons {"稍后提醒", "取消", "立即打开"} default button "立即打开" with title "工作日志提醒"')

# 检查用户选择
if echo "$response" | grep -q "立即打开"; then
    # 打开文件
    open -a "Visual Studio Code" "$LOG_FILE"

    # 等待VS Code打开
    sleep 2

    # 再次提醒具体步骤
    osascript -e 'display notification "1. 使用代码片段: dailylog + Tab\n2. 填写今天的工作内容\n3. 保存文件" with title "记录步骤" sound name "Ping"'

elif echo "$response" | grep -q "稍后提醒"; then
    # 30分钟后再次提醒
    (sleep 1800 && osascript -e 'display notification "📝 还记得更新工作日志吗？" with title "AI Hub 提醒" sound name "Glass"') &
fi

exit 0
