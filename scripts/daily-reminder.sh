#!/bin/bash

# 每日工作日志提醒脚本
# 用途：每天工作结束时提醒更新 daily-log.md

echo "📝 每日工作日志提醒"
echo "===================="
echo ""
echo "请花 5 分钟更新今天的工作记录："
echo ""
echo "1️⃣  打开文件：docs/progress/daily-log.md"
echo "2️⃣  填写今天的内容："
echo "   - 今日目标（完成情况）"
echo "   - 完成的任务"
echo "   - 遇到的问题"
echo "   - 明天的计划"
echo "   - 实际用时"
echo ""
echo "3️⃣  保存并提交 Git"
echo ""
echo "💡 提示：记录越及时，信息越准确！"
echo ""

# 自动打开编辑器（可选）
read -p "是否现在打开 daily-log.md？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    # 使用系统默认编辑器打开
    ${EDITOR:-code} docs/progress/daily-log.md
fi
