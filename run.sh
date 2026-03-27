#!/bin/bash
#
# 语音输入管理器 - 启动脚本
#

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查 Python
if command -v python3 &> /dev/null; then
    PYTHON="python3"
elif command -v python &> /dev/null; then
    PYTHON="python"
else
    echo "❌ 错误: 未找到 Python，请先运行 ./install.sh"
    exit 1
fi

# 解析参数
MODE="gui"
if [ "$1" = "--cli" ] || [ "$1" = "-c" ]; then
    MODE="cli"
fi

if [ "$MODE" = "gui" ]; then
    echo "🚀 启动语音输入管理器..."
    $PYTHON "$SCRIPT_DIR/src/voice_gui.py"
else
    echo "🚀 启动语音输入服务（命令行模式）..."
    $PYTHON "$SCRIPT_DIR/src/voice_input.py"
fi
