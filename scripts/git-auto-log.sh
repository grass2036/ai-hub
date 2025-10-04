#!/bin/bash

# Git 提交时自动更新工作日志
# 用途：在 Git 提交后钩子中调用，自动追踪进度

PROJECT_DIR="/Users/chiyingjie/code/git/ai-hub"
LOG_FILE="$PROJECT_DIR/docs/progress/daily-log.md"
TODAY=$(date +%Y-%m-%d)

# 获取最新的提交信息
LAST_COMMIT_MSG=$(git log -1 --pretty=format:"%s")
LAST_COMMIT_FILES=$(git log -1 --name-only --pretty=format:"")

# 分析提交类型
commit_type="其他"
if echo "$LAST_COMMIT_MSG" | grep -iq "^feat"; then
    commit_type="新功能开发"
elif echo "$LAST_COMMIT_MSG" | grep -iq "^fix"; then
    commit_type="Bug修复"
elif echo "$LAST_COMMIT_MSG" | grep -iq "^docs"; then
    commit_type="文档更新"
elif echo "$LAST_COMMIT_MSG" | grep -iq "^refactor"; then
    commit_type="代码重构"
elif echo "$LAST_COMMIT_MSG" | grep -iq "^test"; then
    commit_type="测试相关"
fi

# 输出到日志文件（追加模式）
PROGRESS_LOG="$PROJECT_DIR/.daily-progress-cache.log"

echo "$TODAY|$commit_type|$LAST_COMMIT_MSG" >> "$PROGRESS_LOG"

# 显示提示
echo ""
echo "📝 工作进度已自动记录"
echo "   类型: $commit_type"
echo "   提交: $LAST_COMMIT_MSG"
echo ""
