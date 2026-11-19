# 教学视频智能分析与拆解系统——开发与部署说明文档

## 1. 项目简介
**教学视频智能分析与拆解系统**（又称长视频拆解系统）是一个专为微格教学、课堂实录、网课视频进行智能化分析、关键帧提取、音频多格式转换、语音转写、知识点图谱构建以及教学评估报告生成的全栈 Web 平台。
系统结合了**计算机视觉 (CV)、数字信号处理 (DSP) 与机器学习 (ML)** 算法，并集成了**大语言模型 (LLM)** 的认知推理能力，实现对长教学视频的多维度拆解与重构，从而辅助教师进行教学反思与教学质量评估。

---

## 2. 技术栈与开发语言

### 2.1 编程语言
*   **后端与算法层**: **Python 3.10.4**
    *   利用 Python 强大的生态整合 OpenCV 图像处理、Pytesseract 字符识别、基于 Web 的多路并发控制以及数据库 ORM 交互。
*   **前端展示层**: **HTML5 / CSS3 / JavaScript (ES6)**
    *   **Vanilla JS (纯原生 JS)**: 轻量级架构，无前端构建步骤，直接通过浏览器原生 Web API 进行 HTTP 请求 (Fetch API) 及全双工实时通信 (WebSocket API)。
    *   **ECharts (可视化)**: 用于渲染知识图谱中复杂的关系实体节点和边。
    *   **Vanilla CSS (CSS3 自定义主题)**: 提供流畅的排版和响应式布局，支持自适应侧边栏及深浅色皮肤。

### 2.2 开发框架与第三方库
*   **Web 框架**: **FastAPI** (基于 Python Asyncio 的高性能异步 Web 框架，自动生成 Swagger UI 交互式 API 文档)。
*   **ASGI 服务器**: **Uvicorn** (极速 ASGI 服务器，用于承载 FastAPI 服务)。
*   **数据库与 ORM**: **SQLAlchemy** (关系型数据库映射组件) + **SQLite** (内嵌轻量级数据库，数据库文件为 `teaching_video_system.db`)。
*   **安全与认证**: **python-jose** (JWT 签名令牌的编解码) + **passlib[bcrypt] / bcrypt** (对用户密码实施安全加盐哈希存储)。
*   **音视频底层处理工具**:
    *   **OpenCV (`opencv-python`)**: 提供关键帧图像解码、视频抽样寻帧、色彩直方图计算、形态学运算、Sobel 梯度计算以及 Laplacian 清晰度量化等功能。
    *   **Pytesseract**: 用于对屏幕画面（如课件 PPT、黑板字等）的 ROI 区域进行光学字符识别 (OCR)。
    *   **FFmpeg / FFprobe**: 核心的多媒体底层引擎，负责高效率的视频静音分离、音频流多格式转码（MP3/M4A/FLAC/OGG）、以及时长探测。

---

## 3. 开发环境与依赖配置

### 3.1 系统环境要求
*   **操作系统**: 兼容 Windows、Linux、macOS。
    *   *注: 本系统已在后端对 Windows 系统下的 GBK 控制台解码、子进程隐藏（`startupinfo`）以及 Tesseract 安装路径自动探测做了深度兼容适配。*
*   **Python 版本**: Python >= 3.8 (推荐使用开发环境版本 **Python 3.10.4**)。

### 3.2 系统级依赖（需手动安装并加入系统环境变量 PATH）
1.  **FFmpeg & FFprobe**:
    *   作用：负责提取视频音频数据（.wav），转换音频格式，读取视频时长和元数据。
    *   安装方法：
        *   Windows: 下载静态构建版（如 [Gyan.dev](https://www.gyan.dev/ffmpeg/builds/)），将 `bin` 目录路径加入系统环境变量 `Path` 中。
        *   Linux (Ubuntu/Debian): `sudo apt update && sudo apt install ffmpeg -y`
    *   验证命令：在终端输入 `ffmpeg -version` 和 `ffprobe -version` 均能正常输出版本信息。
2.  **Tesseract-OCR**:
    *   作用：用于视频关键帧中内嵌字幕的文字识别 (OCR)。
    *   安装方法：
        *   Windows: 从 [UB-Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/wiki) 下载安装包并安装。
        *   Linux: `sudo apt install tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-eng -y`
    *   **关键配置**: 必须确保已下载并安装**中文简体** (`chi_sim`) 和**英文** (`eng`) 语言数据包（放置在 `tessdata` 目录下）。系统启动时将自动搜寻 Tesseract 路径并设置 `TESSDATA_PREFIX` 环境变量。

### 3.3 Python 依赖库
使用 `pip` 安装项目目录下的 `requirements.txt` 依赖：
```bash
pip install -r requirements.txt
```
`requirements.txt` 内容清单：
*   `fastapi` - 异步后端框架
*   `uvicorn` - 运行服务器
*   `python-multipart` - 用于支持多表单文件上传 (上传视频)
*   `opencv-python` - 图像与视频处理
*   `numpy` - 高性能科学计算与矩阵运算
*   `requests`, `aiohttp` - 异步/同步 API 网络请求 (与 LLM 及百度语音识别通信)
*   `sqlalchemy` - ORM 数据库管理
*   `python-jose[cryptography]` - JWT Token 生成与解析
*   `passlib[bcrypt]`, `bcrypt` - 密码加盐加密与校验

---

## 4. 系统架构与核心模块说明

系统的文件组织非常清晰，主要分为后端逻辑、前端静态页面、核心算法、测试/消融实验等模块。

```
长视频拆解系统/
├── static/                     # 前端静态资源目录
│   ├── index.html              # 系统主页（任务仪表盘与统计概览）
│   ├── upload.html             # 视频上传及分析参数设置页面
│   ├── tasks.html              # 我的任务列表与详细拆解结果可视化中心
│   ├── login.html / register.html # 用户登录/注册页面
│   ├── profile.html            # 个人中心（账号及角色管理）
│   ├── welcome.html            # 系统欢迎/过渡页
│   ├── help.html               # 帮助与使用指南说明页
│   ├── common.css / theme.css  # 全局公共样式与主题皮肤 CSS
│   └── common.js / keyboard.js # 核心 API 通信、JWT 处理及快捷键交互 JS
├── utils/
│   └── file_packer.py          # 实用打包工具（将关键帧/字幕打包成 ZIP 下载）
├── ablation_study.py           # 关键帧提取特征的学术消融实验脚本
├── experiment_keyframes.py      # 关键帧提取对比评测实验脚本（基线 vs 本系统算法）
├── experiment_subtitles.py      # 字幕切分对比评测实验脚本（固定分片 vs VAD 分段）
├── main.py                     # 单视频处理的控制台 CLI 工具（用于无 Web 界面下的独立分析）
├── large_video.py              # 系统核心 Web 服务（包含 FastAPI 初始化与核心 AI 算法集）
├── database.py                 # SQLite 连接与 SQLAlchemy Session 管理
├── models.py                   # 数据库模型定义（User, Task, Frame, Subtitle 等关系表）
├── crud.py                     # 数据库增删改查 (CRUD) 底层实现
├── auth.py / auth_routes.py    # 基于 JWT + bcrypt 的安全认证模块及 API 路由
├── admin_routes.py             # 系统管理员路由（包括所有任务状态重载、管理接口）
├── admin_stats.py              # 数据统计分析模块（用于生成仪表盘统计指标）
├── share_manager.py            # 任务外部分享管理（生成临时提取码和分享链接）
├── subtitle_export.py          # 多格式字幕导出工具 (SRT, VTT, TXT)
├── report_generator.py         # 教学分析报告生成器 (Markdown, PDF/Word文本占位)
├── websocket_manager.py        # 实时任务状态追踪的 WebSocket 广播管理器
├── requirements.txt            # 项目运行环境 Python 依赖清单
└── teaching_video_system.db    # SQLite 数据库文件 (系统运行后自动生成)
```

---

## 5. 核心算法设计与学术创新点

本系统在长视频拆解与重构过程中，结合了计算机视觉与信号处理的混合智能策略（Hybrid Intelligence），保障了在软著申请、课题结题或学术汇报中的技术深度与原创性：

### 5.1 图像层算法（Visual Stream）
1.  **镜头边界检测 (Shot Boundary Detection)**:
    *   *原理*: 计算相邻视频帧在 **HSV 色彩空间**下的二维直方图相关性（`cv2.compareHist`）。当相似度低于设定阈值时，判断为镜头场景发生跳变，自动标记关键的时间切片节点。
2.  **图像质量评估 (IQA - Image Quality Assessment)**:
    *   *原理*: 融合了拉普拉斯方差算子（`cv2.Laplacian`，评估图像清晰度）与 Canny 边缘密度算子（评估图像内容的丰富度，剔除纯色、纯黑等无信息量的过渡帧）。
3.  **人工神经网络场景分类 (Neural Scene Classifier)**:
    *   *原理*: 利用 OpenCV 机器学习模块中的多层感知机（**ANN_MLP**），通过 32 维的 HSV 简化直方图特征作为输入，进行二分类（低信息干扰帧 vs 高信息/课件 PPT 帧），在候选关键帧中进行二次筛选过滤。
4.  **视觉显著性检测 (Visual Saliency Detection)**:
    *   *原理*: 基于**频谱残差法 (Spectral Residual, SR)**。在频率域对灰度图进行快速傅里叶变换 (FFT)，计算对数振幅谱的频谱残差，再通过逆傅里叶变换 (IFFT) 还原到空间域，并通过高斯平滑输出显著性热力图，选取热力图均值最高（视觉关注焦点最突出）的时刻作为关键帧。
5.  **文本密度分析 (Text Density Analyzer)**:
    *   *原理*: 采用 Sobel 算子获取垂直边缘，模糊后进行水平矩形结构元素的**形态学闭运算 (Morphological Close)** 将文字笔画聚拢，通过膨胀/腐蚀去除散噪，计算连通文本区域占画面的面积比，以精准判别 PPT/课件画面的切换点。
6.  **相似度去重 (dHash & Hamming Distance)**:
    *   *原理*: 采用**差值哈希 (dHash)** 算法，将帧图像降采样至 9x8 并灰度化，计算相邻像素的明暗差异，生成 64 位二进制哈希序列。通过计算汉明距离（Hamming Distance），当相似度 $\ge 85\%$ 时合并重复帧，保留各场景下质量分数最高（Clarity + Saliency + Density）的唯一帧。

### 5.2 听觉层算法（Audio Stream）
1.  **静音端检测与语音活动检测 (VAD - Voice Activity Detection)**:
    *   *原理*: 提取音频轨的 PCM 数据，利用滑动窗口（20ms）计算信号的**短时能量 (Short-Time Energy, STE)**。当能量高于设定的噪声能量阀值时判定为有效说话段，自动在静音区间进行语义切片。避免了在句子中间暴力切割导致的语音识别上下文割裂。
2.  **多格式音频流转码**:
    *   *原理*: 自动调用底层 FFmpeg，并根据输出规范将音轨分离为高音质 MP3 (192k)、M4A (128k)、FLAC 无损及 OGG (libvorbis) 多格式，满足不同播放终端或复现实验的要求。

### 5.3 认知层算法（Semantic Stream）
1.  **知识图谱实体抽取 (Knowledge Graph Extraction)**:
    *   *原理*: 过滤中文停用词和口语无意义短语，利用正则表达式提取 3-8 字的主题实体。通过统计高频知识点以及跨字幕句子的共现频率（Co-occurrence Frequency），自动关联不同知识点，生成图谱的节点（`nodes`）与边（`links`），支持前端 ECharts 渲染。
2.  **大模型认知推理 (LLM Integration)**:
    *   *原理*: 将语音转写的课堂实录文本投递至集成好的 DeepSeek 接口，生成结构化的教学报告小结和课堂内容大纲。

---

## 6. 学术实验与消融验证 (Ablation & Experiment)

项目代码中包含了一套完整的学术评估体系，用以支撑项目的学术价值或竞赛汇报中的数据展示：

*   **`experiment_keyframes.py`**:
    *   对比算法：**系统关键帧算法 (Ours)** vs **固定时间间隔采样 (Baseline)**。
    *   评测指标：关键帧数量、冗余率（Redundancy Rate）、表征度得分（Representativeness Score）、处理用时。
*   **`experiment_subtitles.py`**:
    *   对比算法：**基于 VAD 静音切分的语音识别 (Ours)** vs **固定时间分片识别 (Baseline)**。
    *   评测指标：分段数量、平均句子长度、分段语义完整性度量（Segment Integrity）、评估字错率（Estimated CER/WER）。
*   **`ablation_study.py` (消融实验)**:
    *   验证在关闭部分模块（如无显著性检测 `-Visual Saliency`、无文本密度分析 `-Text Density`、无去重 `-dHash` 等）时的算法表现，用以证明系统设计中各算法模块的必要性与协同优化效果。实验运行后会自动将汇总矩阵输出至 `results_ablation.json`。

---

## 7. 数据库设计 (SQLite Schema)

数据库底层采用 SQLite，表之间的主要关系定义在 `models.py` 中：

1.  **`users` (用户表)**: 存储账号、加盐密码哈希、角色（`student`, `teacher`, `admin`）。
2.  **`tasks` (任务表)**: 记录视频处理状态（`uploading`, `processing`, `completed`, `failed`）、视频时长、帧统计数、公开/收藏属性，并关联 `users.id`。
3.  **`frames` (关键帧表)**: 存储每一帧的时间戳、物理路径、以及评估算出的显著性得分（`saliency_score`）、文本密度（`text_density`）和图像清晰度质量分数（`quality_score`），并以外键关联 `tasks.id`。
4.  **`subtitles` (字幕表)**: 存储转写文本、时间区间和序号。
5.  **`knowledge_graphs` (知识图谱表)**: 以 JSON 字段存储图谱的节点与关联连接结构数据。
6.  **`share_links` (分享链接表)**: 提供对外分享的加密/公开链接管理。
7.  **`favorites` & `tags` & `task_tags`**: 协同支撑系统的多标签筛选及用户收藏夹功能。

---

## 8. 系统复现与运行部署指南

要想完全复现本系统，可以按照以下几个步骤配置运行环境。

### 第一步：安装外部基础工具
1.  **安装 FFmpeg**:
    *   下载并解压后，将包含 `ffmpeg.exe` 和 `ffprobe.exe` 的 `bin` 文件夹路径添加至系统的环境变量中。
2.  **安装 Tesseract-OCR**:
    *   下载并安装 Tesseract，推荐将其默认安装在 `C:\Program Files\Tesseract-OCR\` 下，本系统会自动检测该默认路径。
    *   下载 `chi_sim.traineddata`（中文简体数据包）和 `eng.traineddata` 并放入安装路径下的 `tessdata` 文件夹内。

### 第二步：安装 Python 依赖包
在系统命令行（PowerShell 或 CMD）中运行：
```powershell
pip install -r requirements.txt
```

### 第三步：初始化数据库并创建管理员
为了确保可以直接使用超级管理员登录系统，请运行初始化脚本：
```powershell
python -c "from database import init_db; init_db()"
python create_admin.py
```
*   该命令将会在项目根目录下自动创建 SQLite 数据库文件 `teaching_video_system.db`。
*   同时在数据库中插入一个初始管理员账户。
    *   **用户名**: `admin`
    *   **密 码**: `admin123`
    *   **角 色**: `admin` (管理员)

### 第四步：运行服务器
直接运行核心 Web 主程序：
```powershell
python large_video.py
```
*   服务将会以开发者模式在本地启动，监听地址为 `http://localhost:8000` 或 `http://127.0.0.1:8000`。

### 第五步：访问与使用
1.  打开浏览器访问：`http://127.0.0.1:8000/login.html`。
2.  输入账号 `admin`，密码 `admin123` 进行登录。
3.  登录成功后进入首页，可点击“视频上传”模块，上传测试视频进行长视频的分析与拆解。

---

## 9. 附录：软著及学术论文汇报参考
若需要将此系统用于软件著作权申请，其核心的代码源清单中突出的算法闭环（包含 `ANN_MLP` 场景分类器、`Spectral Residual` 显著性变换等）均集成在 `large_video.py` 与 `experiment_keyframes.py` 中，无需依赖重型的第三方深度学习框架（如 PyTorch / TensorFlow），仅需配置标准的 CPU 运行环境（如普通笔记本电脑或小型虚拟机）即可流畅运行。这使得系统拥有**极低的部署能耗、极快的启动速度以及高度的自闭环性**，十分适合作为学术成果或校级工坊竞赛的核心展示系统。
