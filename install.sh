#!/bin/bash
#
# 语音输入管理器 - 安装脚本
#

set -e

echo "========================================"
echo "  语音输入管理器 - 安装脚本"
echo "========================================"
echo ""

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查 Python 版本
echo ">>> 检查 Python 环境..."
if command -v python3 &> /dev/null; then
    PYTHON="python3"
elif command -v python &> /dev/null; then
    PYTHON="python"
else
    echo "❌ 错误: 未找到 Python，请先安装 Python 3.9+"
    echo "   推荐使用 Homebrew: brew install python"
    exit 1
fi

PYTHON_VERSION=$($PYTHON --version 2>&1 | awk '{print $2}')
echo "✅ 找到 Python $PYTHON_VERSION"

# 检查版本是否 >= 3.9
MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 9 ]); then
    echo "❌ 错误: 需要 Python 3.9 或更高版本"
    exit 1
fi

# 检查 pip
echo ""
echo ">>> 检查 pip..."
if ! $PYTHON -m pip --version &> /dev/null; then
    echo "❌ 错误: 未找到 pip"
    exit 1
fi
echo "✅ pip 可用"

# 安装依赖
echo ""
echo ">>> 安装依赖包..."
echo "   (这可能需要几分钟，请耐心等待)"
echo ""

# 使用国内镜像加速
$PYTHON -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple 2>&1 || \
$PYTHON -m pip install -r requirements.txt

# 创建虚拟环境（如果不存在）
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo ""
    echo ">>> 创建虚拟环境..."
    $PYTHON -m venv "$SCRIPT_DIR/venv"
    VENV_PYTHON="$SCRIPT_DIR/venv/bin/python"
    echo ">>> 在虚拟环境中安装依赖..."
    $VENV_PYTHON -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple 2>&1 || \
    $VENV_PYTHON -m pip install -r requirements.txt
fi

echo ""
echo "✅ 依赖安装完成"
echo ""

# 更新 /Applications 下的 .app 应用程序包
APP_BUNDLE="/Applications/Voice-Aura.app"
if [ -d "$APP_BUNDLE" ]; then
    echo ">>> 更新应用程序包: $APP_BUNDLE"
    VENV_PYTHON="$SCRIPT_DIR/venv/bin/python"
    if [ ! -f "$VENV_PYTHON" ]; then
        VENV_PYTHON="$(which python3 || which python)"
    fi
    cat > "$APP_BUNDLE/Contents/MacOS/launch" << LAUNCHER_EOF
#!/bin/bash
cd "$SCRIPT_DIR"
export PYTHONUNBUFFERED=1
exec "$VENV_PYTHON" "$SCRIPT_DIR/src/voice_gui.py"
LAUNCHER_EOF
    chmod +x "$APP_BUNDLE/Contents/MacOS/launch"
    codesign --force --deep --sign - "$APP_BUNDLE" 2>/dev/null || true
    echo "✅ 应用程序包已更新"
else
    echo "ℹ️  未找到 /Applications/Voice-Aura.app，跳过更新"
fi

# 创建默认配置文件
CONFIG_FILE="$HOME/.voice_config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    echo ">>> 创建默认配置文件..."
    cp "$SCRIPT_DIR/config/default_config.json" "$CONFIG_FILE"
    echo "✅ 配置文件已创建: $CONFIG_FILE"
else
    echo "ℹ️  配置文件已存在: $CONFIG_FILE"
fi

# 创建默认热词文件
HOTWORDS_FILE="$HOME/hotwords.txt"
if [ ! -f "$HOTWORDS_FILE" ]; then
    echo ">>> 创建默认热词文件..."
    touch "$HOTWORDS_FILE"
    echo "✅ 热词文件已创建: $HOTWORDS_FILE"
else
    echo "ℹ️  热词文件已存在: $HOTWORDS_FILE"
fi

echo ""
echo "========================================"
echo "  安装完成！"
echo "========================================"
echo ""
echo "⚠️  首次运行前，请确保已授权："
echo ""
echo "   1. 麦克风权限："
echo "      系统设置 → 隐私与安全性 → 麦克风 → 添加终端"
echo ""
echo "   2. 辅助功能权限："
echo "      系统设置 → 隐私与安全性 → 辅助功能 → 添加终端"
echo ""
echo "📌 首次运行会自动下载语音模型（0.6B 约 1.5GB，1.7B 约 3.5GB）"
echo ""
echo "🚀 运行方式："
echo "   ./run.sh          # 通过 .app 包启动（推荐，权限持久化）"
echo "   ./run.sh --cli    # 直接启动服务（无 GUI）"
echo ""
