# 《基于音画义时关联的教学视频智能解析系统》全功能研发与完善实施路线图 (RTX 5060 适配版)

> **项目名称**：基于音画义时关联的教学视频智能解析技术研究与实现  
> **项目根目录**：`E:\SchoolFiles\competetion\工坊校级项目\视频拆解\长视频拆解系统`  
> **目标运行环境**：Windows 11 / NVIDIA GeForce RTX 5060 (Blackwell 架构 / `sm_120` / 8GB VRAM / 32GB RAM)  
> **文档版本**：v1.0 (开题对齐与工程重构版)

---

## 目录
- [一、 现状审计与开题报告差距分析 (Gap Analysis)](#一-现状审计与开题报告差距分析-gap-analysis)
- [二、 RTX 5060 (sm_120 / 8GB) 软硬件架构与避坑选型](#二-rtx-5060-sm_120--8gb-软硬件架构与避坑选型)
- [三、 目标工程目录架构重构规范](#三-目标工程目录架构重构规范)
- [四、 6 个阶段详细实施推进计划 (Phase 0 ~ Phase 5)](#四-6-个阶段详细实施推进计划-phase-0--phase-5)
  - [阶段 0：工程重构解耦与 sm_120 专属环境基座搭建](#阶段-0工程重构解耦与-sm_120-专属环境基座搭建23-天)
  - [阶段 1：单模态链路升级——本地 GPU ASR 与关键帧课件 OCR 引擎](#阶段-1单模态链路升级本地-gpu-asr-与关键帧课件-ocr-引擎1-周)
  - [阶段 2：攻克核心学术创新——跨模态时序对齐引擎研发](#阶段-2攻克核心学术创新跨模态时序对齐引擎研发115-周)
  - [阶段 3：语义重构升级——加涅事件分期与多层次知识图谱生成](#阶段-3语义重构升级加涅事件分期与多层次知识图谱生成1-周)
  - [阶段 4：系统全链路闭环与前端人机交互界面完善](#阶段-4系统全链路闭环与前端人机交互界面完善1-周)
  - [阶段 5：毕业论文量化评测基准与消融对比实验](#阶段-5毕业论文量化评测基准与消融对比实验115-周)
- [五、 Antigravity 项目工作区关联指引](#五-antigravity-项目工作区关联指引)

---

## 一、 现状审计与开题报告差距分析 (Gap Analysis)

经系统性代码精读，当前项目处于“前端原型界面完备 + 基础音视频处理能跑”，但**开题报告中最具学术价值的跨模态关联与深层语义理解几乎处于空白或玩具代码状态**。具体差距清单如下：

| 功能模块 | 开题报告要求标准 | 当前代码真实状态 | 存在缺陷与风险 | 紧急等级 |
| :--- | :--- | :--- | :--- | :---: |
| **① 音视频解耦** | FFmpeg 提取视频帧流与 16kHz 定点单声道 WAV | 已实现 (`VideoProcessor.extract_audio`) | 状态稳定，可直接复用 | 低 |
| **② 视觉流关键帧抽取** | HSV 镜头检测 + 清晰度/显著性/文本密度加权评分 + dHash 去重 | 基础逻辑已实现 (`calculate_image_quality`, `VisualSaliency`, `TextDensityAnalyzer`) | 1. `large_video.py` 内部类重复定义 (`VideoProcessor` 定义了两次，覆盖了前者)；<br>2. 混入了未生效的假代码 `ModelTrainer`；<br>3. 切点搜索窗固定且缺少自适应调整。 | 中 |
| **② 听觉流语音转写** | 教室低信噪比自适应门限 VAD + 逐句精确 ASR | 短时能量 VAD 已有；但 ASR 调用的为**百度在线免费接口** | 1. 百度免费接口限额且并发仅 2 QPS，40 分钟长课堂处理需要 5~10 分钟且经常超时丢段；<br>2. 实验脚本 `experiment_subtitles.py` 中甚至使用了 `simulate_asr` 模拟文本。 | **高** |
| **③ 课件文本识别 (OCR)** | 对抽出的课件/板书关键帧进行高精 OCR 提取画面文本 | **主分析流水线中完全缺失** | 仅独立脚本 `main.py` 内含有旧版 Tesseract 字幕区域 ROI 识别，关键帧的板书内容没有被识别和存储，导致视觉流没有文本。 | **极高 (P0)** |
| **③ 跨模态时序对齐** | **核心创新**：以课件文本与转写文本的语义相似度矩阵做动态规整 (DTW)，估计并校正音画非刚性漂移 | **完全未实现 (0 行代码)** | `process_video_api` 流程中完全跳过了这一步，视觉关键帧和语音字幕各自独立，无法支撑开题报告的“音画义时四维关联”。 | **极高 (P0)** |
| **④ 语义重构与知识图谱** | 融合加涅教学事件理论（引入/讲解/练习/总结）以及三层拓扑（前置/核心/引申），生成带时间戳绑定的图谱与诊断报告 | 仅写了一段简单的 DeepSeek Prompt 提取通用名词 | 1. `large_video.py:1400` 中竟然将字幕进行了暴力截断：`subtitles[:1500]`，导致 40 分钟的视频仅分析了前 2 分钟！<br>2. 生成的知识图谱没有任何教学事件分期，没有层级关系，节点无法回指到关键帧与视频时间戳。 | **极高 (P0)** |
| **⑤ 系统工程与交互** | 异步任务调度、WebSocket 实时进度推送、分阶段异常隔离 | FastAPI 基础路由具备，WebSocket 类已写 (`websocket_manager.py`) | 1. `process_video_api` 核心长函数堆砌在 `large_video.py` (单文件超 5000 行)；<br>2. WebSocket 实际上未真正在各步骤中向前端广播进度，前端全靠轮询；<br>3. 数据库表缺少 OCR 与对齐偏移量字段。 | 中 |
| **⑥ 论文量化评测** | 建立真值基准集，评测关键帧 F1、音画对齐 MAE 误差、图谱准确度 | `ablation_study.py` 仅为简单玩具脚本 | 缺少系统性的客观指标计算与论文图表生成能力。 | **高** |

---

## 二、 RTX 5060 (sm_120 / 8GB) 软硬件架构与避坑选型

新电脑配备了 **NVIDIA GeForce RTX 5060 (Blackwell 架构, 计算能力 `sm_120`, 8GB VRAM, 32GB RAM)**。此硬件是极具性价比的本地推理工作站，但由于是最新架构，存在以下核心技术选型红线：

### 1. 架构兼容避坑红线 (Crucial)
- **PyTorch 版本红线**：旧版 PyTorch (CUDA 11.8 / 12.1 / 12.4 构建) **不支持 `sm_120`**，运行 CUDA 算子时会触发 `RuntimeError: CUDA error: no kernel image is available for execution on the device`。
  - **解决方案**：必须安装支持 CUDA 12.8 的 PyTorch 官方构建版：
    ```bash
    pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128
    ```
- **PaddleOCR 避坑**：Paddle 原生 whl 对 Blackwell 架构适配周期较长。
  - **解决方案**：采用 **`RapidOCR-ONNX` (结合 onnxruntime-directml 或 onnxruntime-gpu)**。PP-OCRv4 的 ONNX 导出权重在 32GB 内存下单张图推理耗时 <100ms，识别准确率极高且环境依赖极简，完全绕过编译依赖。

### 2. 8GB 显存“流水线串行生命周期管理”
8GB 显存若同时常驻多个大模型会爆显存（OOM）。但本项目为典型**阶段式离线批处理流水线**，因此制定**“显存按需加载、即用即退”**的显存管理原则：

```
[阶段 1: 视觉抽帧 + OCR] 
  -> CPU/DirectML 运行 RapidOCR (占用显存 0 MB)
[阶段 2: 语音转写 ASR] 
  -> 载入 faster-whisper (large-v3-turbo / medium int8) (占用显存 2.5 GB) 
  -> 转写完毕 -> del model; torch.cuda.empty_cache() (释放显存至 0 MB)
[阶段 3: 跨模态向量嵌入与时序对齐] 
  -> 载入 BAAI/bge-small-zh-v1.5 (fp16) (占用显存 0.4 GB) 
  -> 计算相似度矩阵与 DTW 对齐 -> del model (释放显存)
[阶段 4: 语义重构与知识图谱] 
  -> 方案 A (主选): DeepSeek-V3 API (云端推理，上下文达 64k，显存占用 0 MB)
  -> 方案 B (完全离线备选): Ollama 本地运行 Qwen2.5-7B-Instruct-Q4_K_M (占用显存 5.2 GB)
```

---

## 三、 目标工程目录架构重构规范

将当前臃肿且混乱的 5000 行 `large_video.py` 彻底解耦，形成结构清晰的工业级与科研级模块化目录：

```
长视频拆解系统/
├── config/                         # 全局配置 (模型路径、门限参数、API Key)
│   ├── __init__.py
│   └── settings.py
├── core/                           # 核心解析引擎 (音·画·义·时 四维模型)
│   ├── __init__.py
│   ├── audio_engine.py             # ①+② VAD语音活动检测 + faster-whisper 本地 ASR
│   ├── visual_engine.py            # ①+② HSV镜头边界检测 + 多特征(清晰/显著/文本)加权选帧 + dHash去重
│   ├── ocr_engine.py               # ③ 课件与板书高精度 RapidOCR 提取器
│   ├── alignment_engine.py         # ③ 【核心学术创新】跨模态动态时间规整(DTW)与非刚性时序校正
│   └── semantic_engine.py          # ④ 融合加涅九步事件提示工程 + 层次知识图谱重构
├── database/                       # 数据库持久层 (SQLite + SQLAlchemy)
│   ├── __init__.py
│   ├── connection.py               # 数据库引擎与 SessionLocal
│   ├── models.py                   # 实体模型 (Task, Frame, Subtitle, Alignment, KnowledgeGraph)
│   └── crud.py                     # 数据访问对象 (DAO)
├── routers/                        # FastAPI 路由层
│   ├── __init__.py
│   ├── task_routes.py              # 视频上传、流水线触发、任务状态查询
│   ├── result_routes.py            # 关键帧、字幕、图谱、报告查询接口
│   ├── auth_routes.py              # JWT 身份认证与权限管理
│   ├── admin_routes.py             # 管理员与教研统计指标聚合
│   └── websocket_routes.py         # 实时阶段推送 WebSocket 路由
├── services/                       # 业务与调度服务
│   ├── __init__.py
│   ├── task_pipeline.py            # 任务状态机调度器 (异步编排各 core 引擎)
│   ├── report_service.py           # 教学诊断报告 Markdown/HTML/Word 生成导出
│   └── share_service.py            # 一次性分享码与权限校验
├── experiments/                    # 毕业论文实验与指标评测脚本
│   ├── benchmark_data/             # 5~8 门已标注真值的微格/课堂测试视频
│   ├── eval_keyframes.py           # 关键帧消融实验 (清晰度/显著性/文本密度 vs 均匀采样 vs TransNet)
│   ├── eval_alignment.py           # 跨模态时序对齐精度评测 (MAE 误差计算)
│   └── eval_knowledge_graph.py     # 加涅教学事件覆盖度与知识图谱抽取 F1 计算
├── static/                         # 前端单页面交互资源 (HTML/CSS/JS/ECharts)
│   ├── index.html
│   ├── tasks.html
│   ├── common.js
│   └── ...
├── main.py                         # FastAPI 应用程序入口
└── requirements.txt                # 规范依赖库清单
```

---

## 四、 6 个阶段详细实施推进计划 (Phase 0 ~ Phase 5)

### 阶段 0：工程重构解耦与 sm_120 专属环境基座搭建（2~3 天）

- [ ] **任务 0.1：RTX 5060 专用 Python 虚拟环境配置**
  - 在新电脑上安装 Anaconda/Miniconda，创建 Python 3.10/3.11 环境：
    ```bash
    conda create -n video_rag python=3.10 -y
    conda activate video_rag
    # 核心：安装 cu128 PyTorch
    pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128
    # 核心：安装高性能推理与多模态依赖
    pip install faster-whisper rapidocr-onnxruntime sentence-transformers fastapi uvicorn websockets sqlalchemy python-multipart opencv-python pydantic requests aiohttp
    ```
  - 编写一段自检脚本，验证 `torch.cuda.is_available()`，打印显卡名称为 `RTX 5060`，验证张量能在 GPU 上正常分配计算。
- [ ] **任务 0.2：架构目录初始化与代码迁移拆解**
  - 按上述架构创建 `core/`、`routers/`、`services/` 目录；
  - 将 `large_video.py` 中的重复定义类、无效类（如 `ModelTrainer`）彻底清理；
  - 将通用的音视频解耦、基础工具函数归档到对应模块。
- [ ] **任务 0.3：数据库表结构 (Schema) 升级扩展**
  - 升级 `models.py` 中的数据表定义：
    - `Frame` 表增添：`ocr_text` (课件文字), `aligned_time` (对齐后时间戳), `drift_offset` (漂移量), `scene_category` (板书/人像/混合)；
    - `Task` 表完善状态机枚举：`QUEUED`, `EXTRACTING_MEDIA`, `ANALYZING_VISUAL`, `TRANSCRIBING_AUDIO`, `ALIGNING_MULTIMODAL`, `RESTRUCTURING_SEMANTICS`, `COMPLETED`, `FAILED`；
    - 新增 `AlignmentLog` 表：记录每一对视频帧与语音段的对齐明细与相似度评分。

---

### 阶段 1：单模态链路升级——本地 GPU ASR 与关键帧课件 OCR 引擎（1 周）

- [ ] **任务 1.1：集成 `faster-whisper` 本地高性能语音识别 (`core/audio_engine.py`)**
  - 彻底废除百度在线 API；
  - 采用 `faster-whisper` 加载 `large-v3-turbo`（或 `medium`）模型，设置计算精度为 `compute_type="int8_float16"`；
  - 接入原有的短时能量 VAD（20ms 窗、自适应静音阈值），对非静音段切片后送入 Whisper，产出包含 `start`、`end`、`text`、`confidence` 的高精度时间戳字幕列表；
  - 记录单段识别耗时，输出完整 SRT 文件并自动写入 `subtitles` 数据库表。
- [ ] **任务 1.2：构建课件关键帧结构化 OCR 引擎 (`core/ocr_engine.py`)**
  - 基于 `rapidocr_onnxruntime` 封装 `SlideOCREngine`；
  - 对视觉流筛出的每一个代表性关键帧进行文字检测与识别；
  - 过滤规则：剔除置信度低于 0.6 的字符，合并同一行文本，去除教师衣服或背景中的偶发噪点文字；
  - 将识别出的文本内容、版面区域分布（用于判定是否为 PPT 课件帧）存入 `Frame.ocr_text`。
- [ ] **任务 1.3：优化内容感知多特征关键帧筛选机制 (`core/visual_engine.py`)**
  - 镜头边界检测：基于 HSV 色彩直方图巴氏距离检测切换点；
  - 切点邻域寻优：在检测到的切点后 2.0 秒内（采样 10~15 帧），综合计算：
    $$\text{Score} = w_1 \cdot \text{LaplacianVar} + w_2 \cdot \text{SpectralResidual} + w_3 \cdot \text{TextDensity}$$
  - 选出综合得分最高者作为代表帧，使用 dHash (汉明距离 $\le 5$) 进行跨镜头同质课件去重。

---

### 阶段 2：攻克核心学术创新——跨模态时序对齐引擎研发（1~1.5 周）

> **这是本课题最核心的学术创新点，也是开题答辩和毕业论文的亮点所在。**

- [ ] **任务 2.1：构建跨模态语义向量表征与相似度矩阵 (`core/alignment_engine.py`)**
  - 加载轻量级嵌入模型 `BAAI/bge-small-zh-v1.5`（显存开销仅 400MB）；
  - 将所有关键帧提取的 `ocr_text` 编码为向量矩阵 $V \in \mathbb{R}^{M \times D}$；
  - 将所有语音转写的 `subtitles` 文本句段编码为向量矩阵 $A \in \mathbb{R}^{N \times D}$；
  - 计算课件-语音语义余弦相似度矩阵 $S = V \cdot A^T \in [-1, 1]^{M \times N}$。
- [ ] **任务 2.2：实现带局部时间窗约束的动态时间规整算法 (Windowed DTW)**
  - 传统真实课堂中，教师讲解与课件翻页的超前/滞后通常在一定合理范围（例如 $\pm 15$ 秒至 $\pm 30$ 秒内），不可能出现第 1 分钟课件与第 30 分钟语音对齐的情况；
  - 设计带时间窗惩罚的动态时间规整：
    $$D(i, j) = (1 - S_{i, j}) + \min \begin{cases} D(i-1, j) + \text{gap} \\ D(i, j-1) + \text{gap} \\ D(i-1, j-1) \end{cases} + \lambda \cdot |t_{\text{frame}}(i) - t_{\text{audio}}(j)|$$
  - 回溯寻优路径，找到每个课件帧与语音段落的最优匹配，解出时间对齐映射 $\hat{t} = f(t_{\text{frame}})$，计算非刚性漂移量 $\Delta t = \hat{t} - t_{\text{frame}}$。
- [ ] **任务 2.3：设计置信度门限与纯板书/图表退化机制 (Robust Fallback)**
  - 真实场景中，存在部分课件仅有纯示意图、数学几何图形，或教师板书字迹潦草导致 OCR 提取文本为空或置信度极低；
  - 设立置信度检验阈值 $\theta_{\text{sim}}$：
    - 若最优匹配的相似度低于阈值，则判定当前帧不存在语义对齐线索，系统**自动退化回原始物理时间戳**（即 $\Delta t = 0$）；
    - 记录对齐状态标志位（`EXACT_ALIGNED` vs `FALLBACK_RAW`），彻底避免“无文字课件强行匹配语音”造成的灾难性语义错位。
- [ ] **任务 2.4：对齐结果持久化与可解释性数据产出**
  - 将每个关键帧的校正后时间戳 `aligned_time` 和漂移偏移量 `drift_offset` 写入数据库；
  - 输出包含对齐前后时间戳对比的对齐日志 JSON，供前端交互渲染音画漂移分析曲线。

---

### 阶段 3：语义重构升级——加涅事件分期与多层次知识图谱生成（1 周）

- [ ] **任务 3.1：彻底修复 1500 字暴力截断 Bug，设计多模态上下文装配器 (`core/semantic_engine.py`)**
  - 废除原代码 `subtitles[:1500]` 的做法；
  - 利用对齐后的结果，将课堂全过程按照“时间跨度 + 课件切换”划分为若干个**多模态教学微单元 (Micro Teaching Units, MTU)**；
  - 每个 MTU 包含：`[时间区间]`、`[课件核心文字]`、`[教师对齐讲解语句]`；
  - 采用分块滑动窗口（Map-Reduce 式上下文聚合）或长文本大模型（DeepSeek 64k 上下文）一次性喂入完整的结构化多模态数据。
- [ ] **任务 3.2：融合加涅九步教学事件理论的结构化提示工程**
  - 编写专业的教学分析 System Prompt，要求大模型输出遵循严格的教学法分期：
    - **环节一：引起注意与温故知新**（引入阶段）；
    - **环节二：呈现教学刺激与引导学习**（核心概念讲授阶段）；
    - **环节三：引出表现与提供反馈**（课堂提问、例题推导与练习阶段）；
    - **环节四：总结强化与拓展迁移**（课堂总结与作业布置阶段）。
  - 输出结构化教学事件时间轴列表。
- [ ] **任务 3.3：加涅分期与三层知识图谱重构 (Pydantic 严格约束 JSON)**
  - 采用结构化 JSON Schema 输出，规定节点和边必须包含：
    - 节点分类：`prerequisite`（前置基础知识）、`core`（课堂核心讲授知识）、`extension`（课外引申拓展）；
    - 节点绑定：每一个知识点**必须绑定发生的时间戳区间 `timestamp` 及对应的代表关键帧编号 `frame_id`**（实现回指）；
    - 关系类型：`leads_to`（推导递进）、`contains`（包含组成）、`contrasts`（对比分析）、`explains`（实例说明）。
- [ ] **任务 3.4：自动化教学诊断报告生成升级 (`services/report_service.py`)**
  - 汇总输出专业教学反思与诊断报告：
    - 课堂基本信息与时长分布统计；
    - 教学事件各阶段耗时比例分析（例如：讲授占比 70%，练习占比 10%，诊断是否超时或比例失衡）；
    - 核心概念拓扑一览；
    - 课件板书质量与音画同步性诊断建议；
  - 支持渲染为 Markdown，并导出为 HTML / Word 文档。

---

### 阶段 4：系统全链路闭环与前端人机交互界面完善（1 周）

- [ ] **任务 4.1：异步流水线状态机编排与 WebSocket 实时广播**
  - 在 `services/task_pipeline.py` 中规范整个长视频处理的串行调度状态；
  - 在每个主要阶段（切音频、抽帧、OCR、ASR、时序对齐、LLM 推理、报告落盘）开始与结束时，调用 `websocket_routes.broadcast_to_task(task_id, {...})`；
  - 前端 `tasks.html` / `common.js` 监听 WebSocket，动态更新带有当前正在执行模块的高级进度条与执行日志。
- [ ] **任务 4.2：前端关键帧与字幕时间轴“音画双向联动”交互**
  - 点击任何一张关键帧缩略图，右侧音视频播放器跳转到对应时间，且字幕滚动到对应对齐语句；
  - 点击任何一句字幕，高亮显示该时刻对应的课件关键帧；
  - 关键帧卡片上直观显示标注：`原始捕获时间 12:35` / `校正对齐时间 12:42`（标记漂移 +7s）。
- [ ] **任务 4.3：ECharts 知识图谱深度交互升级**
  - 引入力导向图 (Force Graph) 动态物理引擎；
  - 节点按加涅阶段与前置/核心/引申类型分别以学术深蓝、松石绿、琥珀金分类着色；
  - 点击知识点节点，弹窗显示该概念在课堂上的讲解内容摘要，并提供“一键定位到视频”按钮。

---

### 阶段 5：毕业论文量化评测基准与消融对比实验（1~1.5 周）

> **用于为开题报告验收、中期检查及毕业论文第 4、5 章提供扎实的实验图表和数据支撑。**

- [ ] **任务 5.1：基准数据集收集与真值标注 (`experiments/benchmark_data/`)**
  - 收集 5~8 门不同学科（计算机算法课、师范生微格教学实训、数学例题课、人文讲座）时长 20~45 分钟的真实教学视频；
  - 人工标定部分真值 (Ground Truth)：
    - 真实课件翻页时间戳与真实关键代表帧；
    - 随机抽样 50 处课件内容与教师口头讲解的真实对应时间戳（用于评测对齐误差）；
    - 教学专家标注的核心知识点拓扑结构。
- [ ] **任务 5.2：实验一 —— 关键帧抽取与去重消融对比实验 (`eval_keyframes.py`)**
  - 对比方案：
    - Baseline 1：均匀固定间隔采样 (每 10s 一帧)；
    - Baseline 2：纯 HSV 色彩直方图切点帧；
    - Baseline 3：开源深度模型 TransNet V2 转场关键帧；
    - Ours：HSV + 邻域清晰度/显著性/文本密度加权 + dHash 去重。
  - 评测指标：有效知识画面召回率 (Recall)、冗余帧压缩比 (Compression Ratio)、单视频处理耗时 (s)。
- [ ] **任务 5.3：实验二 —— 跨模态时序对齐精度对比实验 (`eval_alignment.py`)**
  - 对比方案：
    - 未对齐基线：原始物理切片时间戳；
    - 简单固定时间偏移校正 (全局平移 $\Delta t = \text{const}$)；
    - Ours：基于 BGE 相似度矩阵的局部窗口动态时间规整 (Windowed DTW)。
  - 评测指标：平均绝对时间偏移误差 (Mean Absolute Error, $\text{MAE} = \frac{1}{K}\sum |\hat{t}_k - t^*_k|$)、音画语义匹配命中率 (Hit Rate @ 5s)。
- [ ] **任务 5.4：实验三 —— 知识图谱结构与教学事件抽取质量评测 (`eval_knowledge_graph.py`)**
  - 对比方案：
    - Baseline：传统纯文本无提示 LLM 摘要抽词；
    - Ours：结合对齐多模态单元 + 加涅教学事件理论约束抽取；
  - 评测指标：专业知识点抽取 F1-Score、专家盲评打分（知识点完整度、层级合理性、反思可用性，1~5 分量表）。

---

## 五、 Antigravity 项目工作区关联指引

由于你提到“当前这是在一个 conversation 里面，想把这个变成一个 project”，在 Antigravity 架构中：

1. **当前文件的物理存储位置**：
   本项目全部代码与开题文档都直接存放在本地真实磁盘：
   `E:\SchoolFiles\competetion\工坊校级项目\视频拆解\长视频拆解系统`

2. **在 Antigravity IDE 中激活为正规 Project / Workspace 的操作方法**：
   - 点击 Antigravity IDE 顶部主菜单：**`File` (文件) $\rightarrow$ `Open Folder...` (打开文件夹)**；
   - 浏览并选择定位到：`E:\SchoolFiles\competetion\工坊校级项目\视频拆解\长视频拆解系统`，点击“选择文件夹”；
   - 此时，左侧的文件资源管理器（File Explorer）将完整加载整个工程目录树，Antigravity 的代码智能索引、全局检索、Git 版本管理和终端调试将全部绑定到此项目上下文；
   - 在左侧侧边栏中随时打开本指南文档：`SYSTEM_IMPROVEMENT_ROADMAP.md`，即可作为后期的开发对照清单（Checklist）逐项打勾推进。
