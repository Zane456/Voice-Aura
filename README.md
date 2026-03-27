# 语音输入管理器

基于 FunASR 的 macOS 按键语音输入工具。按住指定键说话，松开后自动识别并输入到光标位置。

## 功能特性

- **按键触发录音** - 按住右 Command（可自定义）开始录音，松开自动识别
- **高精度中文识别** - 使用阿里 FunASR 模型，识别准确率高
- **热词支持** - 自定义热词提升特定词汇识别率
- **替换规则** - 自动修正常见误识别
- **GUI 管理** - 图形界面管理服务、按键和规则

## 系统要求

- macOS 10.15+
- Python 3.9+
- 约 5GB 磁盘空间（首次运行需下载模型）

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/你的用户名/voice-input.git
cd voice-input
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

### 热词

热词可以提升特定词汇的识别准确率。编辑 `~/hotwords.txt`，每行一个词：

```
Claude Code 100
OpenRouter 50
n8n 50
```

数字表示热词权重（可选，默认 50）。

### 替换规则

在 GUI 中配置替换规则，自动修正常见误识别：

```
cloud code → Claude Code
克劳德 → Claude
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `~/.voice_config.json` | 配置文件（触发键、替换规则） |
| `~/hotwords.txt` | 热词列表 |
| `~/.cache/modelscope/` | 模型缓存目录 |

## 常见问题

### 麦克风没声音 / 无法录音

检查麦克风权限：系统设置 → 隐私与安全性 → 麦克风

### 识别后没有输入文字

检查辅助功能权限：系统设置 → 隐私与安全性 → 辅助功能

### 首次启动很慢

首次运行需要下载约 1-2GB 的模型文件，请耐心等待。

### 如何更新替换规则后生效

在 GUI 中修改替换规则后，需要重启服务才能生效。

## 依赖

- [FunASR](https://github.com/alibaba-damo-academy/FunASR) - 阿里开源语音识别框架
- [sounddevice](https://python-sounddevice.readthedocs.io/) - 音频录制
- [pynput](https://pynput.readthedocs.io/) - 键盘监听

## License

MIT
