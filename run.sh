#!/bin/bash
#
# 语音输入管理器 - 启动脚本
#

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查虚拟环境
if [ -d "$SCRIPT_DIR/venv" ]; then
    PYTHON="$SCRIPT_DIR/venv/bin/python"
    echo "✅ 使用虚拟环境"
else
    # 检查系统 Python
    if command -v python3 &> /dev/null; then
        PYTHON="python3"
    elif command -v python &> /dev/null; then
        PYTHON="python"
    else
        echo "❌ 错误: 未找到 Python，请先运行 ./install.sh"
        exit 1
    fi
fi

# 解析参数
MODE="gui"
if [ "$1" = "--cli" ] || [ "$1" = "-c" ]; then
    MODE="cli"
fi

if [ "$MODE" = "gui" ]; then
    # 优先通过 /Applications 下的 .app 包启动（权限持久化）
    APP_BUNDLE="/Applications/Voice-Aura.app"
    if [ -d "$APP_BUNDLE" ]; then
        echo "🚀 通过应用包启动 Voice Aura..."
        open "$APP_BUNDLE"
    else
        echo "🚀 启动语音输入管理器..."
        "$PYTHON" "$SCRIPT_DIR/src/voice_gui.py"
    fi
else
    echo "🚀 启动语音输入服务（命令行模式）..."
    "$PYTHON" "$SCRIPT_DIR/src/voice_input_qwen.py"
fi
