# Voice Aura

macOS 按键语音输入工具。按住指定键说话，松开后自动识别并输入到光标位置。

使用 Qwen3-ASR 模型，支持 Apple Silicon (MPS) 加速。

## 功能特性

- **按键触发录音** - 按住右 Command（可自定义）开始录音，松开自动识别
- **高精度中文识别** - 使用 Qwen3-ASR 模型，业界领先中文识别准确率
- **替换规则** - 自动修正常见误识别，GUI 中可自定义
- **GUI 管理** - 图形界面管理服务、模型选择和规则
- **模型切换** - 支持 1.7B（精确）和 0.6B（极速）两种模型

## 系统要求

- macOS 12+ (Apple Silicon 或 Intel)
- Python 3.9+
- 约 5GB 磁盘空间（首次运行需下载模型）

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/Zane456/Voice-Aura.git
cd Voice-Aura
```

### 2. 安装依赖

```bash
chmod +x install.sh run.sh
./install.sh
```

### 3. 授权权限

首次使用需要授权：

1. **麦克风权限**：系统设置 → 隐私与安全性 → 麦克风 → 添加终端
2. **辅助功能权限**：系统设置 → 隐私与安全性 → 辅助功能 → 添加终端

### 4. 启动

```bash
./run.sh          # 启动 GUI 管理器
./run.sh --cli    # 直接启动服务（命令行模式）
```

## 使用方法

1. 启动服务后，按住 **右 Command 键** 开始录音
2. 对着麦克风说话
3. 松开按键，自动识别并输入到当前光标位置

## 配置

### 触发按键

在 GUI 中可选择的触发按键：
- 右 Command（默认）
- 左 Command
- 右 Option
- 左 Option
- Control
- Shift

### 识别模型

在 GUI 中可切换模型：
- **Qwen3-ASR-1.7B (精确)** - 默认，识别准确率更高
- **Qwen3-ASR-0.6B (极速)** - 速度更快，适合实时场景

### 替换规则

在 GUI 中配置替换规则，自动修正常见误识别：

```
cloud code → Claude Code
克劳德 → Claude
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `~/.voice_config.json` | 配置文件（触发键、模型、替换规则） |
| `/tmp/voice_input.log` | 服务运行日志 |
| `~/.cache/huggingface/` | 模型缓存目录 |

## 常见问题

### 麦克风没声音 / 无法录音

检查麦克风权限：系统设置 → 隐私与安全性 → 麦克风

### 识别后没有输入文字

检查辅助功能权限：系统设置 → 隐私与安全性 → 辅助功能

### 首次启动很慢

首次运行需要下载模型（1.7B 约 3.5GB，0.6B 约 1.5GB），请耐心等待。后续启动只需加载模型（约 10-30 秒）。

### 模型下载失败

使用国内镜像：
```bash
HF_ENDPOINT=https://hf-mirror.com ./run.sh --cli
```

## 依赖

- [Qwen3-ASR](https://huggingface.co/Qwen) - 语音识别模型
- [sounddevice](https://python-sounddevice.readthedocs.io/) - 音频录制
- [pynput](https://pynput.readthedocs.io/) - 键盘监听

## License

MIT
