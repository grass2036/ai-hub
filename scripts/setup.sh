#!/bin/bash

# AI Hub Platform - 项目初始化脚本
# 
# 该脚本将帮助你快速设置开发环境

set -e

echo "🚀 AI Hub Platform - 项目初始化"
echo "================================"

# 检查当前目录
if [ ! -f "README.md" ] || [ ! -d "backend" ]; then
    echo "❌ 错误: 请在项目根目录执行此脚本"
    exit 1
fi

# 检查Python版本
python_version=$(python3 --version 2>/dev/null || echo "Not found")
if [[ ! $python_version == *"Python 3."* ]]; then
    echo "❌ 错误: 需要Python 3.9或更高版本"
    echo "当前版本: $python_version"
    exit 1
fi

echo "✅ Python版本检查通过: $python_version"

# 创建数据目录
echo "📁 创建数据目录..."
mkdir -p data/{uploads,documents,vectors,logs,backups}
touch data/uploads/.gitkeep
touch data/documents/.gitkeep
touch data/vectors/.gitkeep
touch data/logs/.gitkeep
touch data/backups/.gitkeep

# 创建Python虚拟环境
echo "🐍 创建Python虚拟环境..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ 虚拟环境创建成功"
else
    echo "ℹ️  虚拟环境已存在，跳过创建"
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 检查AgentFlow子模块
echo "📦 检查AgentFlow子模块..."
if [ ! -d "agentflow/.git" ]; then
    echo "⚠️  AgentFlow子模块未初始化，正在初始化..."
    git submodule update --init --recursive
fi

# 安装AgentFlow框架
echo "🔧 安装AgentFlow框架..."
if [ -d "agentflow" ]; then
    pip install -e ./agentflow
    echo "✅ AgentFlow安装成功"
else
    echo "⚠️  AgentFlow目录不存在，请检查子模块配置"
fi

# 升级pip并安装依赖
echo "📦 安装项目依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 检查环境变量配置
echo "🔐 检查环境配置..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ 已创建 .env 文件，请编辑填入你的API密钥"
        echo ""
        echo "📝 需要配置的API密钥:"
        echo "   - OPENROUTER_API_KEY (必需)"
        echo "   - GEMINI_API_KEY (必需)"
        echo "   - OPENAI_API_KEY (可选)"
        echo "   - SUPABASE_URL 和 SUPABASE_ANON_KEY (第2个月需要)"
        echo ""
    else
        echo "❌ .env.example 文件不存在"
        exit 1
    fi
else
    echo "ℹ️  .env 文件已存在"
fi

# 测试基础功能
echo "🧪 测试基础功能..."
if python -c "import sys, os; sys.path.insert(0, '.'); from backend.config.settings import get_settings; settings = get_settings(); print('✅ 配置加载成功')"; then
    echo "✅ 基础配置测试通过"
else
    echo "❌ 基础配置测试失败，请检查依赖安装"
    exit 1
fi

# 创建开发脚本
echo "📝 创建开发脚本..."

# 创建启动脚本
cat > scripts/run_dev.sh << 'EOF'
#!/bin/bash
# 启动开发服务器

echo "🚀 启动AI Hub开发服务器..."

# 激活虚拟环境
source venv/bin/activate

# 启动后端
echo "📡 启动FastAPI后端服务器..."
python backend/main.py
EOF

# 创建测试脚本  
cat > scripts/run_tests.sh << 'EOF'
#!/bin/bash
# 运行测试

echo "🧪 运行项目测试..."

# 激活虚拟环境
source venv/bin/activate

# 运行后端测试
echo "🔍 运行后端测试..."
pytest backend/tests/ -v

# 运行代码质量检查
echo "📋 运行代码质量检查..."
black --check backend/
isort --check-only backend/
mypy backend/ || echo "⚠️  类型检查有警告，但不影响运行"
EOF

# 使脚本可执行
chmod +x scripts/run_dev.sh
chmod +x scripts/run_tests.sh

echo ""
echo "🎉 项目初始化完成!"
echo ""
echo "📋 下一步操作:"
echo "1. 编辑 .env 文件，填入你的API密钥"
echo "2. 运行 'scripts/run_dev.sh' 启动开发服务器"
echo "3. 访问 http://localhost:8000/api/docs 查看API文档"
echo ""
echo "🔧 常用命令:"
echo "   source venv/bin/activate        # 激活虚拟环境"
echo "   python backend/main.py          # 启动后端服务"
echo "   scripts/run_tests.sh            # 运行测试"
echo ""
echo "📚 项目文档: docs/development/setup.md"
echo "🐛 如有问题，请查看项目README.md"
echo ""
echo "🌟 准备开始你的AI开发之旅！"