# Python睡眠质量分析预测 睡眠质量可视化


## Env build

### Conda
```bash
conda env create -f environment.yml
conda activate sleepQualityVisualization
```

### update after git pull
```bash
conda env update -f environment.yml --prune
```


## Parts

### 数据格式
(Example source using data from my wristband.

 Format:XiaoMi Mi band 7nfc ver exported from zepp app)
Data format：

```
DATA/
├── SLEEP/
│   └── SLEEP_*.csv
│       date, deepSleepTime, shallowSleepTime, wakeTime,
│       start, stop, REMTime, naps
│
├── SLEEP_MINUTE/
│   └── SLEEP_MINUTE_*.csv
│       date, time, stage, hr, respiratory_rate
│
├── ACTIVITY/
│   └── ACTIVITY_*.csv
│       date, steps, distance, runDistance, calories
│
├── ACTIVITY_MINUTE/
│   └── ACTIVITY_MINUTE_*.csv
│       date, time, steps
│
├── ACTIVITY_STAGE/
│   └── ACTIVITY_STAGE_*.csv
│       date, start, stop, distance, calories, steps
│
├── HEARTRATE/
│   └── HEARTRATE_*.csv
│       time, heartRate
│
└── HEARTRATE_AUTO/
    └── HEARTRATE_AUTO_*.csv
        date, time, heartRate
```


## Git 版本管理

项目使用 `.gitignore` 忽略以下内容（详见根目录 `.gitignore` 文件）：
- `__pycache__/`、`*.pyc` 等 Python 编译文件
- `OUTPUT/`、`DATA/` 运行时生成数据
- `backend/uploads/` 上传临时目录
- `frontend/node_modules/`、`frontend/dist/` 前端依赖与构建产物
- `config.local.txt` 本地敏感配置覆盖
- `.vscode/`、`.idea/` IDE 配置
- `*.log` 日志文件


## 项目结构

```
SleepQualityVisualization/
├── .gitignore                   # Git 忽略规则
├── environment.yml              # Conda 环境配置（含 Python + Node.js）
├── README.md
│
├── DATA/                        # 原始 CSV 数据目录（不纳入版本控制）
│   ├── SLEEP/
│   ├── SLEEP_MINUTE/
│   ├── ACTIVITY/
│   ├── ACTIVITY_MINUTE/
│   ├── ACTIVITY_STAGE/
│   ├── HEARTRATE/
│   └── HEARTRATE_AUTO/
│
├── OUTPUT/                      # 预处理输出目录（不纳入版本控制）
│   ├── sleep_daily_preview.csv
│   ├── sleep_daily.parquet
│   ├── secondary_processed.csv
│   └── fine/
│       └── sleep_fine_*.parquet
│
├── backend/                     # Python 后端（一个功能一个 py 文件）
│   ├── config.txt               # 全量配置文件（数据库/端口/模型参数）
│   ├── app.py                   # 主入口：Flask 应用工厂、数据库初始化
│   ├── models.py                # 数据库模型：User / SleepRecord / AnalysisReport
│   ├── auth.py                  # 用户认证：注册/登录/登出/权限装饰器
│   ├── data_manage.py           # 数据管理：CSV上传/预览/一键预处理/删除
│   ├── visualize.py             # 可视化数据：散点图/直方图/热力图/阶段占比/趋势
│   ├── predict.py               # 预测分析：线性回归/特征重要性/个性化建议
│   ├── admin.py                 # 管理员：全局统计/用户管理/群体数据聚合
│   ├── preprocess.py            # 数据预处理引擎（可独立运行）
│   ├── postprocess.py           # 二次处理引擎（可独立运行）
│   └── import_to_sql.py         # 手动 SQL 导入脚本（可独立运行）
│
└── frontend/                    # Vue 3 + Element Plus + ECharts 前端
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.js              # 路由配置 + 导航守卫
        ├── App.vue              # 主布局（角色感知导航栏）
        ├── api/
        │   └── sleep.js         # 全部 API 请求封装
        └── components/
            ├── LoginPage.vue        # 登录页
            ├── RegisterPage.vue     # 注册页
            ├── UserHome.vue         # 普通用户首页
            ├── UserCenter.vue       # 个人中心（历史报告）
            ├── DataManage.vue       # 数据管理（上传/预览/预处理）
            ├── VisualizePage.vue    # 可视化分析（5类图表）
            ├── PredictPage.vue      # 睡眠质量预测
            ├── AdminHome.vue        # 管理员首页
            ├── AdminUsers.vue       # 用户管理 + 全局数据
            └── AdminVis.vue         # 群体可视化分析
```


## 配置说明

配置文件 `backend/config.txt` 采用 Key=Value 格式，所有可修改参数集中管理：

```ini
# ---------- MySQL 数据库连接 ----------
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=root
MYSQL_DATABASE=sleep_quality_db
MYSQL_CHARSET=utf8mb4
MYSQL_CONNECT_TIMEOUT=10

# ---------- Flask 后端服务 ----------
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=true
SECRET_KEY=sleep-quality-secret-key-change-in-production

# ---------- 前端开发服务 ----------
FRONTEND_PORT=3000
FRONTEND_API_TARGET=http://127.0.0.1:5000

# ---------- 文件上传 ----------
UPLOAD_FOLDER=backend/uploads
MAX_UPLOAD_SIZE_MB=50
ALLOWED_EXTENSIONS=csv

# ---------- 预测模型参数 ----------
MODEL_RANDOM_SEED=42
MODEL_TEST_SIZE=0.2
MODEL_CV_FOLDS=5

# ---------- 管理员默认账号（首次启动自动创建） ----------
ADMIN_DEFAULT_USERNAME=admin
ADMIN_DEFAULT_PASSWORD=admin123
```


## 系统架构概览

```
┌─────────────────────────────────────────────────────┐
│                    前端 (Vue 3)                      │
│  localhost:FRONTEND_PORT  (默认 3000)               │
│  Login → Register → UserHome → DataManage           │
│  → Visualize → Predict → UserCenter                 │
│  Admin: AdminHome → AdminUsers → AdminVis           │
└────────────┬────────────────────────────────────────┘
             │  /api/*  (Vite Proxy)
┌────────────▼────────────────────────────────────────┐
│               后端 Flask API (Python)                │
│  0.0.0.0:FLASK_PORT  (默认 5000)                    │
│  ┌──────────┬──────────┬──────────┬──────────┐     │
│  │  auth.py │  data_   │ visualize│ predict  │     │
│  │  注册登录│  manage  │  .py     │  .py     │     │
│  │  权限校验│  上传处理│  图表数据│  ML预测  │     │
│  ├──────────┴──────────┴──────────┴──────────┤     │
│  │              admin.py  全局管理             │     │
│  └────────────────────────────────────────────┘     │
└────────────┬────────────────────────────────────────┘
             │  SQLAlchemy + PyMySQL
┌────────────▼────────────────────────────────────────┐
│              MySQL 数据库 (sleep_quality_db)          │
│  ┌─────────────┬──────────────┬─────────────────┐  │
│  │   users     │sleep_records │analysis_reports │  │
│  │  用户表      │  睡眠数据表   │   分析报告表     │  │
│  └─────────────┴──────────────┴─────────────────┘  │
└─────────────────────────────────────────────────────┘
```


## 快速启动

### 1. 环境准备
```bash
# 创建 Conda 环境（含 Python 3.12 + Node.js）
conda env create -f environment.yml
conda activate sleepQualityVisualization

# 安装前端依赖
cd frontend && npm install && cd ..
```

### 2. 启动 MySQL
确保 MySQL 服务已启动，数据库 `sleep_quality_db` 将在首次启动后端时自动创建。

### 3. 启动后端
```bash
cd backend && python app.py
```
首次启动自动完成：
- 创建数据库 `sleep_quality_db`
- 创建三张核心表（users / sleep_records / analysis_reports）
- 创建默认管理员账号（admin / admin123）

### 4. 启动前端
```bash
cd frontend && npm run dev
```
浏览器访问 `http://localhost:3000`


## 功能模块（全部通过前端操作）

### 模块一：用户权限管理
| 功能 | 前端页面 | 后端接口 |
|------|---------|---------|
| 用户注册 | `/register` | `POST /api/auth/register` |
| 用户登录 | `/login` | `POST /api/auth/login` |
| 角色识别 | 导航栏自动区分 | `GET /api/auth/me` |
| 权限拦截 | 路由守卫自动跳转 | 装饰器 `@login_required` / `@admin_required` |
| 退出登录 | 导航栏退出按钮 | `POST /api/auth/logout` |

- 普通用户：默认角色，注册后即可使用全部个人功能
- 管理员：使用预设账号登录（admin/admin123），可访问全局管理功能
- 管理员本身也拥有普通用户的全部功能权限

### 模块二：数据管理（普通用户）
| 功能 | 前端页面 | 后端接口 |
|------|---------|---------|
| CSV 上传 | `/user/data` 拖拽上传 | `POST /api/data/upload` |
| 数据预览 | `/user/data` 表格展示 | `GET /api/data/records` |
| 一键预处理 | `/user/data` 按钮触发 | `POST /api/data/preprocess` |
| 数据删除 | `/user/data` 逐条删除 | `DELETE /api/data/records/<id>` |
| 个人统计 | `/user/home` 首页卡片 | `GET /api/data/stats` |

上传流程：选择 CSV → 系统自动解析列名 → 计算睡眠衍生指标（效率/比例/质量分）→ 存入数据库。

### 模块三：可视化分析（普通用户）
| 功能 | 前端页面 | 后端接口 |
|------|---------|---------|
| 多日趋势图 | `/user/vis` 趋势Tab | `GET /api/vis/trend` |
| 散点图（心率/步数 vs 质量） | `/user/vis` 散点Tab | `GET /api/vis/scatter` |
| 直方图（步数/时长分布） | `/user/vis` 直方图Tab | `GET /api/vis/histogram` |
| 相关性热力图 | `/user/vis` 热力图Tab | `GET /api/vis/correlation` |
| 睡眠阶段占比饼图 | `/user/vis` 阶段Tab | `GET /api/vis/stage_pie` |

所有图表基于 ECharts 渲染，支持悬浮查看数值、图片导出。

### 模块四：预测与分析（普通用户）
| 功能 | 前端页面 | 后端接口 |
|------|---------|---------|
| 睡眠质量预测 | `/user/predict` 输入参数 | `POST /api/predict/score` |
| 特征重要性分析 | 预测结果面板 | 模型 LinearRegression.coef_ |
| 个性化建议 | 预测结果面板 | 规则引擎自动生成 |
| 历史报告 | `/user/center` 个人中心 | `GET /api/predict/reports` |

预测流程：用户输入生理参数（或留空使用历史均值）→ 线性回归模型推理 → 输出 0-100 质量分 + 各特征影响权重 + 中文改善建议。

### 模块五：管理员全局管理
| 功能 | 前端页面 | 后端接口 |
|------|---------|---------|
| 全局统计面板 | `/admin/home` | `GET /api/admin/dashboard` |
| 用户管理 | `/admin/users` | `GET/DELETE /api/admin/users` |
| 全局数据管理 | `/admin/users` 下半区 | `GET /api/admin/all_records` |
| 群体质量分布 | `/admin/home` 图表 | `GET /api/admin/group_quality_distribution` |
| 群体睡眠结构 | `/admin/home` 饼图 | `GET /api/admin/group_sleep_structure` |
| 影响因素排行 | `/admin/home` 条形图 | `GET /api/admin/group_influence_ranking` |
| 全局相关性热力图 | `/admin/vis` | `GET /api/vis/admin/global_correlation` |
| 群体分布与趋势 | `/admin/vis` | `GET /api/vis/admin/global_distribution` |

### 模块六：系统首页
- 未登录：显示登录页 `/login`
- 普通用户登录：自动跳转个人首页 `/user/home`，显示统计卡片 + 最近记录
- 管理员登录：自动跳转管理首页 `/admin/home`，显示全站统计 + 群体图表
- 导航栏根据角色动态显示菜单项


## 数据库设计

三张核心表，实现多用户数据隔离：

| 表名 | 说明 | 关键字段 |
|------|------|---------|
| `users` | 用户信息表 | id, username, password_hash, role(user/admin), created_at |
| `sleep_records` | 睡眠数据表 | id, user_id(FK), record_date, deepSleepTime, shallowSleepTime, REMTime, wakeTime, sleepQualityScore, daySteps, avgHeartRate, ... |
| `analysis_reports` | 分析报告表 | id, user_id(FK), predicted_score, input_params(JSON), shap_values(JSON), suggestions, feature_importance(JSON), created_at |

- 所有睡眠数据通过 `user_id` 外键绑定到用户，实现数据隔离
- 报告表记录每次预测的输入参数、输出结果和建议，支持历史回溯


## 后端模块清单（一个功能一个 py 文件）

| 文件 | 职责 | 行数 |
|------|------|------|
| `app.py` | Flask 主入口、数据库初始化、蓝图注册 | ~110 |
| `models.py` | SQLAlchemy 三表模型定义 | ~130 |
| `auth.py` | 注册/登录/登出 + 登录/管理员装饰器 | ~110 |
| `data_manage.py` | CSV 上传解析、CRUD、一键预处理 | ~230 |
| `visualize.py` | 6 类可视化数据端点 + 管理员全局端点 | ~210 |
| `predict.py` | 线性回归训练/预测、特征分析、建议生成 | ~200 |
| `admin.py` | 全局仪表盘、用户管理、群体聚合分析 | ~170 |
| `preprocess.py` | 原始 CSV → 每日/精细 Parquet（可独立运行） | ~300 |
| `postprocess.py` | 精细数据 → 生理信号整合 CSV（可独立运行） | ~180 |
| `import_to_sql.py` | Parquet → MySQL 手动导入（可独立运行） | ~180 |


## 前端页面清单

| 页面 | 路由 | 权限 | 说明 |
|------|------|------|------|
| 登录 | `/login` | 公开 | 用户名+密码登录 |
| 注册 | `/register` | 公开 | 新用户自主注册 |
| 个人首页 | `/user/home` | 登录 | 统计卡片 + 最近记录 |
| 个人中心 | `/user/center` | 登录 | 历史预测报告查看 |
| 数据管理 | `/user/data` | 登录 | 上传/预览/预处理/删除 |
| 可视化分析 | `/user/vis` | 登录 | 趋势/散点/直方图/热力图/阶段饼图 |
| 睡眠预测 | `/user/predict` | 登录 | 输入参数 → 预测分数+建议 |
| 管理首页 | `/admin/home` | 管理员 | 全站统计 + 群体图表 |
| 用户管理 | `/admin/users` | 管理员 | 用户列表 + 全局数据管理 |
| 群体分析 | `/admin/vis` | 管理员 | 全局热力图/分布/趋势 |


### 2.数据分析

基于个人历史数据，系统自动计算各指标间的皮尔逊相关系数，生成相关性热力图。通过线性回归模型分析各特征对睡眠质量的影响权重，区分正向/负向影响因素。

### 3.机器学习建模

使用 Scikit-learn LinearRegression 线性回归模型：
- 输入特征：总睡眠时长、深睡/浅睡/REM 时长、睡眠效率、日步数、心率等 11 维
- 输出：睡眠质量得分（0-100）
- 评估：5 折交叉验证 R² 得分
- 可解释性：模型系数作为特征重要性权重

### 4.可视化

全部可视化通过前端 ECharts 实现，无需手动操作后端：
- 折线图：睡眠质量/效率/时长多日趋势
- 散点图：心率 vs 质量、步数 vs 质量
- 直方图：步数分布、睡眠时长分布
- 热力图：多指标相关性矩阵
- 饼图：睡眠阶段占比
- 柱状图：群体质量分布、影响因素排行

