#!/bin/bash

# 自动工作进度追踪脚本
# 功能：自动收集今天的开发活动并更新 daily-log.md

PROJECT_DIR="/Users/chiyingjie/code/git/ai-hub"
LOG_FILE="$PROJECT_DIR/docs/progress/daily-log.md"
TODAY=$(date +%Y-%m-%d)
DAY_NUM=""

cd "$PROJECT_DIR" || exit 1

echo "🔍 正在分析今天的工作进度..."
echo ""

# ==================== 1. 收集Git提交记录 ====================
echo "📊 收集数据中..."

# 获取今天的Git提交
git_commits=$(git log --since="$TODAY 00:00" --until="$TODAY 23:59" --pretty=format:"- %s" 2>/dev/null)

# 获取今天修改的文件
modified_files=$(git log --since="$TODAY 00:00" --until="$TODAY 23:59" --name-only --pretty=format:"" 2>/dev/null | sort -u | grep -v '^$')

# 统计修改的文件数量
file_count=$(echo "$modified_files" | grep -v '^$' | wc -l | tr -d ' ')

# 统计代码变化
if [ -n "$(git log --since="$TODAY 00:00" --oneline 2>/dev/null)" ]; then
    code_stats=$(git log --since="$TODAY 00:00" --until="$TODAY 23:59" --shortstat 2>/dev/null | \
        awk '{inserted+=$4; deleted+=$6} END {print inserted " insertions, " deleted " deletions"}')
else
    code_stats="0 insertions, 0 deletions"
fi

# ==================== 2. 分析修改的文件类别 ====================
backend_files=$(echo "$modified_files" | grep "backend/" | wc -l | tr -d ' ')
frontend_files=$(echo "$modified_files" | grep "frontend/" | wc -l | tr -d ' ')
docs_files=$(echo "$modified_files" | grep "docs/" | wc -l | tr -d ' ')
config_files=$(echo "$modified_files" | grep -E "\.(json|yaml|yml|toml|env|sh)$" | wc -l | tr -d ' ')

# ==================== 3. 推断完成的任务 ====================
completed_tasks=""

if [ "$backend_files" -gt 0 ]; then
    backend_changes=$(echo "$modified_files" | grep "backend/" | head -5)
    completed_tasks="${completed_tasks}\n- ✅ 后端开发 ($backend_files 个文件)"
    for file in $backend_changes; do
        completed_tasks="${completed_tasks}\n  - \`$file\`"
    done
fi

if [ "$frontend_files" -gt 0 ]; then
    frontend_changes=$(echo "$modified_files" | grep "frontend/" | head -5)
    completed_tasks="${completed_tasks}\n- ✅ 前端开发 ($frontend_files 个文件)"
    for file in $frontend_changes; do
        completed_tasks="${completed_tasks}\n  - \`$file\`"
    done
fi

if [ "$docs_files" -gt 0 ]; then
    completed_tasks="${completed_tasks}\n- ✅ 文档更新 ($docs_files 个文件)"
fi

if [ "$config_files" -gt 0 ]; then
    completed_tasks="${completed_tasks}\n- ✅ 配置文件修改 ($config_files 个文件)"
fi

# ==================== 4. 检查是否已有今天的记录 ====================
if grep -q "## $TODAY" "$LOG_FILE"; then
    echo "⚠️  今天的记录已存在，将更新内容"
    update_mode=true
else
    echo "📝 创建今天的新记录"
    update_mode=false
fi

# ==================== 5. 生成日志内容 ====================
log_entry="## $TODAY (Day $DAY_NUM)

**今日目标**:
- [x] 开发功能
- [ ] 待补充

**完成**:
$(echo -e "$completed_tasks")

**代码统计**:
- 修改文件: $file_count 个
- 代码变化: $code_stats
- 后端文件: $backend_files 个
- 前端文件: $frontend_files 个
- 文档文件: $docs_files 个

**Git提交记录**:
$(if [ -n "$git_commits" ]; then echo "$git_commits"; else echo "- 暂无提交"; fi)

**问题**:
- 待补充

**明天计划**:
- [ ] 待补充

**实际用时**: 待补充

---
"

# ==================== 6. 更新日志文件 ====================
if [ "$update_mode" = true ]; then
    # 更新已存在的记录（暂时跳过，避免覆盖手动内容）
    echo "⚠️  已有记录，请手动更新"
    echo ""
    echo "建议内容："
    echo "$log_entry"
else
    # 在模板之前插入新记录
    if grep -q "## 模板（复制使用）" "$LOG_FILE"; then
        # 在模板前插入
        awk -v entry="$log_entry" '
            /## 模板（复制使用）/ {print entry}
            {print}
        ' "$LOG_FILE" > "${LOG_FILE}.tmp"
        mv "${LOG_FILE}.tmp" "$LOG_FILE"
        echo "✅ 已自动添加今天的工作记录"
    else
        # 追加到文件末尾
        echo "$log_entry" >> "$LOG_FILE"
        echo "✅ 已自动添加今天的工作记录"
    fi
fi

echo ""
echo "📊 今日工作总结："
echo "   - 修改文件: $file_count 个"
echo "   - 代码变化: $code_stats"
echo "   - 后端: $backend_files 个 | 前端: $frontend_files 个 | 文档: $docs_files 个"
echo ""
echo "📝 查看完整记录: code $LOG_FILE"
echo ""
