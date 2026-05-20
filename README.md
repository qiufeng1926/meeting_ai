# 会议 AI 系统

一个智能的语音识别和会议纪要生成系统，支持实时语音转写、批量音频文件处理和历史会议管理。

## 📋 目录

- [功能特性](#-功能特性)
- [快速开始](#-快速开始)
- [使用说明](#-使用说明)
- [API 接口](#-api-接口)
- [项目结构](#-项目结构)
- [技术栈](#-技术栈)
- [配置说明](#-配置说明)
- [日志系统](#-日志系统)
- [故障排查](#-故障排查)
- [开发指南](#-开发指南)

---

## ✨ 功能特性

### 1. 实时语音转写 🎙️
- 通过麦克风实时采集音频
- 边说话边显示识别结果
- 自动累积完整文本
- WebSocket 低延迟通信
- **停止录音后自动生成 AI 会议纪要**
- 支持自定义会议名称

### 2. 批量音频处理 📁
- 上传音频文件（WAV、MP3、M4A等）
- 拖拽或点击选择文件
- 自动语音识别
- AI 自动生成会议纪要
- 结果自动保存到本地
- 支持自定义会议名称

### 3. 历史会议管理 📋
- 独立标签页查看所有会议记录
- 显示会议时间、文件大小、是否有总结
- 智能提取并显示会议名称
- 点击查看完整转写文本和 AI 总结
- 支持返回列表继续浏览

---

## 🚀 快速开始

### 1. 环境准备

确保已安装以下依赖：
```bash
pip install fastapi uvicorn funasr zhipuai python-dotenv numpy
```

### 2. 配置环境变量

编辑 `.env` 文件，配置必要的参数：
```env
# GLM API 配置
GLM_API_KEY=your_api_key_here
GLM_MODEL=glm-4-flash
GLM_TEMPERATURE=0.3

# ASR 配置
ASR_MODEL_NAME=paraformer-zh
ASR_DEVICE=cpu
FFMPEG_PATH=D:\AI\ffmpeg-8.1.1-essentials_build\bin

# 文件路径配置
UPLOAD_DIR=upload
OUTPUT_DIR=output
```

### 3. 启动服务

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. 访问系统

打开浏览器访问：
```
http://localhost:8000
```

---

## 📖 使用说明

### 界面布局

系统采用三标签页设计：
```
[🎙️ 实时转写] [📁 批量处理] [📋 历史会议]
```

### 实时转写模式

1. 点击顶部的 "🎙️ 实时转写" 标签
2. **（可选）**在"📝 会议名称"输入框中输入会议名称
   - 例如："项目周会"、"客户沟通会议"
3. 点击 "开始录音" 按钮
4. 允许浏览器访问麦克风权限
5. 开始说话，文本会实时显示
6. 点击 "停止录音" 结束
7. **系统自动生成 AI 会议纪要**
8. 在页面下方查看 AI 总结

**文件保存位置：**
- 有名称：`output/transcripts/项目周会_uuid_时间戳_realtime.txt`
- 无名称：`output/transcripts/uuid_时间戳_realtime.txt`

### 批量处理模式

1. 点击顶部的 "📁 批量处理" 标签
2. **（可选）**在"📝 会议名称"输入框中输入会议名称
3. 拖拽音频文件到上传区域，或点击选择文件
4. 点击 "开始处理" 按钮
5. 等待处理完成（显示进度条）
6. 查看转写文本和 AI 生成的会议纪要

**文件保存位置：**
- 有名称：`output/transcripts/客户沟通_uuid_时间戳.txt`
- 无名称：`output/transcripts/uuid_时间戳.txt`

### 历史会议模式

1. 点击顶部的 "📋 历史会议" 标签
2. 自动加载所有会议记录
3. 每条记录显示：
   - 会议名称（从文件名智能提取）
   - 创建时间
   - 文件大小
   - 是否有 AI 总结（✅/❌）
   - 内容预览（前150字符）
4. 点击任意会议卡片查看详情
5. 详情页显示：
   - 完整转写文本
   - AI 会议纪要（如果有）
6. 点击 "← 返回列表" 回到列表页

---

## 🔧 API 接口

### REST API

#### 1. 批量上传音频
**URL**: `POST /api/meeting/upload`

**请求**:
- Content-Type: `multipart/form-data`
- 参数: 
  - `file`: 音频文件
  - `meeting_name`: 会议名称（可选）

**响应**: 
```json
{
  "success": true,
  "filename": "meeting.wav",
  "file_id": "uuid",
  "transcript": "识别文本",
  "summary": "AI 会议纪要",
  "transcript_file": "output/transcripts/xxx.txt",
  "summary_file": "output/summaries/xxx.md"
}
```

#### 2. 获取会议列表
**URL**: `GET /api/meetings/list`

**响应**:
```json
{
  "success": true,
  "total": 5,
  "meetings": [
    {
      "file_id": "uuid",
      "filename": "项目周会_xxx_realtime.txt",
      "created_at": "2026-05-20T14:30:25",
      "size": 12345,
      "has_summary": true,
      "preview": "前200字符预览...",
      "transcript_file": "output/transcripts/xxx.txt",
      "summary_file": "output/summaries/xxx.md"
    }
  ]
}
```

#### 3. 获取会议详情
**URL**: `GET /api/meetings/{file_id}`

**响应**:
```json
{
  "success": true,
  "file_id": "uuid",
  "transcript": "完整转写文本",
  "summary": "AI 会议纪要",
  "transcript_file": "路径",
  "summary_file": "路径"
}
```

#### 4. WebSocket 连接状态
**URL**: `GET /api/ws/status`

**响应**:
```json
{
  "active_connections": 2,
  "connections": ["uuid1", "uuid2"]
}
```

### WebSocket API

#### 实时语音转写
**URL**: `ws://localhost:8000/api/ws/transcribe`

**消息格式**:

1. **初始化消息**（可选，发送会议名称）:
```json
{
  "type": "init",
  "meeting_name": "项目周会"
}
```

2. **客户端发送音频数据**:
```json
{
  "type": "audio",
  "data": [音频字节数组],
  "sample_rate": 16000
}
```

3. **服务端返回识别结果**:
```json
{
  "type": "result",
  "text": "当前识别的文本片段",
  "total_text": "累计的全部文本",
  "timestamp": "2026-05-20T14:30:25.123"
}
```

4. **生成总结提示**:
```json
{
  "type": "generating_summary",
  "message": "正在生成 AI 会议纪要..."
}
```

5. **会话结束**:
```json
{
  "type": "session_end",
  "total_text": "完整文本",
  "summary": "AI 会议纪要",
  "file_id": "uuid",
  "transcript_file": "路径",
  "summary_file": "路径",
  "duration": "持续时间"
}
```

6. **错误消息**:
```json
{
  "type": "error",
  "message": "错误描述信息"
}
```

---

## 📂 项目结构

```
meeting_ai/
├── api/                    # API 接口
│   ├── main.py            # FastAPI 主应用
│   └── routes/            # 路由模块
│       ├── meeting.py     # 批量处理接口
│       └── websocket.py   # WebSocket 实时转写 + 历史会议
├── asr/                   # 语音识别引擎
│   └── engine.py          # FunASR 封装（批量+流式）
├── config/                # 配置管理
│   └── config.py          # 环境变量配置
├── llm/                   # 大语言模型
│   ├── glm_chat.py        # GLM 客户端
│   └── prompt.py          # 提示词模板
├── utils/                 # 工具模块
│   └── logger.py          # JSON 日志系统
├── static/                # 静态文件
│   └── transcribe.html    # Web 界面（三标签页）
├── upload/                # 上传文件目录
├── output/                # 输出目录
│   ├── transcripts/       # 转写文本（.txt）
│   └── summaries/         # 会议纪要（.md）
├── logs/                  # 日志文件（JSON Lines）
├── .env                   # 环境变量配置
├── test_system.py         # 系统测试脚本
└── README.md              # 项目说明
```

---

## 🎯 技术栈

- **后端**: FastAPI + Python 3.11+
- **语音识别**: FunASR (Paraformer-zh)
- **大语言模型**: GLM-4 Flash (智谱 AI)
- **前端**: HTML5 + CSS3 + JavaScript (原生)
- **通信**: WebSocket + REST API
- **音频处理**: NumPy + FFmpeg

---

## ⚙️ 配置说明

### 环境变量 (.env)

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `GLM_API_KEY` | 智谱 AI API Key | 必填 |
| `GLM_MODEL` | GLM 模型名称 | `glm-4-flash` |
| `GLM_TEMPERATURE` | 温度参数（0-1） | `0.3` |
| `ASR_MODEL_NAME` | ASR 模型名称 | `paraformer-zh` |
| `ASR_DEVICE` | 运行设备 | `cpu` |
| `FFMPEG_PATH` | FFmpeg 路径 | 需配置 |
| `UPLOAD_DIR` | 上传目录 | `upload` |
| `OUTPUT_DIR` | 输出目录 | `output` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `LOG_DIR` | 日志目录 | `logs` |

### 会议名称配置

**命名规则**:
- 自动清理非法字符（只保留字母、数字、空格、下划线、连字符）
- 空格转换为下划线
- 建议长度不超过 50 个字符

**示例**:
- "项目周会 2026" → "项目周会_2026"
- "Customer Meeting #1" → "Customer_Meeting_1"
- "测试@会议!" → "测试会议"

---

## 📝 日志系统

### 日志格式

日志文件保存在 `logs/` 目录下，采用 JSON Lines 格式：

```json
{"time": "2026-05-20T14:30:25.123", "level": "INFO", "logger": "meeting_ai", "message": "Meeting AI 服务启动", "module": "main", "filename": "main.py", "lineno": 15, ...}
```

### 日志特性

- ✅ 单文件最大 15MB，自动轮转
- ✅ 保留最近 15 天的日志
- ✅ 同时输出到控制台和文件
- ✅ 捕获未处理的异常和警告
- ✅ 包含完整的堆栈跟踪信息

### 日志级别

可通过环境变量 `LOG_LEVEL` 设置：
- `DEBUG`: 调试信息
- `INFO`: 一般信息（默认）
- `WARNING`: 警告信息
- `ERROR`: 错误信息
- `CRITICAL`: 严重错误

---

## 🐛 故障排查

### 问题 1：无法连接 WebSocket

**症状**: 实时转写无法使用

**解决**:
1. 检查服务是否正常运行
2. 确认防火墙未阻止 WebSocket 连接
3. 查看浏览器控制台错误信息
4. 检查 WebSocket URL 是否正确

### 问题 2：识别结果为空

**症状**: 录音后没有文本输出

**解决**:
1. 检查麦克风是否正常工作
2. 确认浏览器已授予麦克风权限
3. 确认音频格式正确（16kHz, 16-bit PCM）
4. 查看服务器日志 (`logs/` 目录)
5. 尝试在安静环境中录音

### 问题 3：AI 总结失败

**症状**: 转写成功但无会议纪要

**解决**:
1. 检查 GLM API Key 是否正确配置
2. 确认网络连接正常
3. 查看日志中的详细错误信息
4. 检查 API 配额是否充足

### 问题 4：服务启动失败

**症状**: uvicorn 启动报错

**解决**:
1. 检查 Python 版本（需要 3.11+）
2. 确认所有依赖已安装
3. 检查端口 8000 是否被占用
4. 查看 `.env` 文件格式是否正确

### 问题 5：文件保存失败

**症状**: 转写结果未保存

**解决**:
1. 检查 `output/` 目录是否存在
2. 确认有写入权限
3. 检查磁盘空间是否充足
4. 查看日志中的错误信息

---

## 💡 开发指南

### 代码规范

1. **Python 代码**:
   - 遵循 PEP 8 规范
   - 使用类型注解
   - 添加必要的注释和文档字符串

2. **前端代码**:
   - 使用语义化 HTML
   - CSS 采用 BEM 命名规范
   - JavaScript 使用 ES6+ 语法

3. **日志记录**:
   ```python
   from utils.logger import get_logger
   logger = get_logger("module_name")
   logger.info("这是一条信息日志")
   logger.error("这是一条错误日志", exc_info=True)
   ```

### 测试

运行系统测试脚本：
```bash
python test_system.py
```

测试内容包括：
- ✅ 配置加载
- ✅ 日志系统
- ✅ ASR 引擎
- ✅ LLM 客户端
- ✅ FastAPI 应用

---

## 📊 性能优化建议

### 实时转写
1. **音频块大小**: 建议每块 2000-4000 个采样点（约 125-250ms）
2. **网络延迟**: 确保稳定的网络连接
3. **降噪处理**: 建议在客户端进行降噪和回声消除
4. **GPU 加速**: 如需更快的识别速度，配置 `ASR_DEVICE=gpu`

### 批量处理
1. **并发处理**: 可考虑添加队列机制处理多个文件
2. **缓存机制**: 对常用模型进行预热
3. **异步处理**: 使用后台任务处理大文件

---


