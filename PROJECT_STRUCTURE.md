# 长视频拆解系统——工程目录架构与导航说明

本工程为 **教学视频智能分析与拆解系统**（本科毕业设计系统平台）。为了保持工程的可维护性、可扩展性，同时清晰区分“系统源码运行环境”、“算法消融实验”、“毕业设计答辩材料”与“历史工坊/竞赛文档”，特制定本目录规范说明。

---

## 目录全景总览

```text
长视频拆解系统/
│
├── 毕业设计/                              # 【毕业设计工作区】开题、综述、官方模板与导师参考
│   ├── 00_开题与综述初稿(当前撰写)/         # 当前正在编辑修改的开题报告、文献综述初稿
│   ├── 01_毕业设计指导与参考/              # 指导老师（胡曦明老师）提供的全套参考资料与往届校优文档
│   ├── 02_学院官方模板与各项材料提交要求(2023级)/ # 学院/学校官方下发的各项毕设文档模板及存档日期要求
│   ├── 03_学院模板原始压缩包/              # 学院模板原始 zip 包备份
│   └── 毕设工作区导航与开题核心备忘.md      # 开题答辩时间节点、导师红线提醒与自检清单
│
├── 00_工坊项目历史文档(归档备份)/           # 【历史材料安全隔离区】前期竞赛/工坊技术参数、功能实现与预算文档
│                                          # （注：开题与答辩严禁出现竞赛/工坊表述，已作独立归档）
│
├── static/                                # 【前端静态资源】原生轻量级 Web 前端 (HTML5 / CSS3 / ES6 JS)
│   ├── index.html                         # 系统主控制台与任务概览
│   ├── tasks.html                         # 任务列表与视频拆解可视化中心（关键帧/字幕/知识图谱）
│   ├── upload.html                        # 视频上传与拆解流水线参数配置
│   ├── login.html / register.html         # 身份认证（登录与注册）
│   ├── admin.html / profile.html          # 管理员控制台与个人中心
│   ├── common.css / theme.css             # 响应式布局与主题样式
│   └── common.js / keyboard.js            # API 请求、WebSocket 通信与交互控制
│
├── utils/                                 # 【通用工具模块】
│   └── file_packer.py                     # 拆解产物（关键帧/字幕/分析报告）ZIP 打包导出工具
│
├── test_media/                            # 【测试音视频媒体库】存放用于本地算法测试的视频样本
│   └── 1月11日.mov                        # 典型微格教学实录测试样本 (65MB)
│
├── archive_legacy/                        # 【历史版本代码备份】
│   └── largevideo-old.py                  # 早期长视频处理服务端备份
│
├── outputs/                               # 【系统运行产物目录】本地任务执行生成的关键帧、音频、字幕与图谱
├── Reverse-disassembly/                   # 【前期子模块研究】向上溯源反推技术指南与原型探索
│
├── [后端核心服务与算法]
│   ├── large_video.py                     # 【核心服务端入口】FastAPI Web 服务 + 核心 AI 拆解流水线
│   ├── main.py                            # 单视频 CLI 本地快速批处理脚本
│   ├── models.py                          # SQLAlchemy ORM 数据模型定义
│   ├── database.py                        # SQLite 数据库连接引擎与会话工厂
│   ├── crud.py                            # 数据增删改查底层操作
│   ├── auth.py / auth_routes.py           # JWT Token 签发验证与用户鉴权路由
│   ├── admin_routes.py / admin_stats.py   # 管理员路由与全站数据统计分析
│   ├── websocket_manager.py               # WebSocket 实时任务进度广播器
│   ├── share_manager.py                   # 任务外部分享与访问控制
│   ├── subtitle_export.py                 # 多格式字幕导出转换器 (SRT/VTT/TXT)
│   └── report_generator.py                # 教学反思与拆解评估报告生成器
│
├── [学术评测与消融实验]
│   ├── ablation_study.py                  # 关键帧综合特征消融实验脚本（Laplacian+显著性+文本密度）
│   ├── experiment_keyframes.py            # 关键帧抽取准确率/冗余度对比实验脚本
│   └── experiment_subtitles.py            # 课堂语音切分误差/VAD分段对比实验脚本
│
├── teaching_video_system.db               # SQLite 数据库文件
├── requirements.txt                       # Python 第三方依赖包清单
├── README.md                              # 系统技术设计、算法原理与部署指南
└── PROJECT_STRUCTURE.md                   # 本文件（工程架构与目录映射说明）
```

---

## 运行与开发指南

1. **环境准备**：
   ```bash
   pip install -r requirements.txt
   ```
   *需确认系统环境变量 PATH 中已配置 `ffmpeg`、`ffprobe` 及 `tesseract`。*

2. **启动 Web 全栈服务**：
   ```bash
   python large_video.py
   # 或使用 uvicorn 启动
   uvicorn large_video:app --host 0.0.0.0 --port 8000 --reload
   ```
   启动后访问浏览器：`http://localhost:8000/static/index.html`。

3. **运行对比消融实验（用于论文数据支撑）**：
   ```bash
   python experiment_keyframes.py
   python experiment_subtitles.py
   python ablation_study.py
   ```
