# Python睡眠质量分析预测 睡眠质量可视化



## 系统需求

| 组件 | 最低版本 | 说明 |
|------|----------|------|
| Python | ≥ 3.10 | 3.12+ |
| Node.js | ≥ 18 | 前端构建与运行 |
| npm | ≥ 9 | Node.js 自带 |
| Conda | Miniconda / Anaconda | 仅 Conda 安装方式需要 |
| MySQL | ≥ 5.7 (可选) | 未安装时自动回退 SQLite |

> **注意**：MySQL 为可选依赖，系统启动时自动检测——可用则使用 MySQL，不可用则自动回退 SQLite，无需手动配置。

## Env build

### Conda
```bash
conda env create -f environment.yml
conda activate sleepQualityVisualization
```

### Or use Python venv
```bash
# Linux / Mac
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Windows
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### update after git pull
```bash
# Conda
conda env update -f environment.yml --prune

# Python venv
pip install -r requirements.txt --upgrade
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




## 项目结构

```
SleepQualityVisualization/
├── environment.yml              # Conda 环境配置
├── README.md
├── backend/                     # Python 后端（一个功能一个 py 文件）
│   ├── config.txt               # 全量配置文件（数据库/端口/模型参数）
│   ├── app.py                   # 主入口：Flask 应用工厂、数据库初始化、自动导入
│   ├── models.py                # 数据库模型：User / SleepRecord / AnalysisReport
│   ├── auth.py                  # 用户认证：注册/登录/登出/权限装饰器
│   ├── data_manage.py           # 数据管理：CSV/ZIP上传/多文件/一键处理/预处理
│   ├── visualize.py             # 可视化数据：散点图/直方图/热力图/阶段占比/趋势（含公开API）
│   ├── predict.py               # 预测分析：SVR/LR/RF多模型对比/特征重要性/个性化建议
│   ├── admin.py                 # 管理员：全局统计/用户管理/群体数据聚合
│   ├── pipeline.py              # 完整预处理管线（线性插值+滑动平滑+IQR异常值+环境参数+阶段标注+特征工程）
│   ├── evaluate_model.py        # 模型评估脚本（R²/MSE/SHAP可解释性）
│   ├── preprocess.py            # 独立预处理引擎
│   ├── postprocess.py           # 独立二次处理引擎
│   └── import_to_sql.py         # 独立SQL导入脚本
│
└── frontend/                    # Vue 3 + Element Plus + ECharts 前端
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.js              # 路由配置 + 导航守卫（公开/登录/管理员三级权限）
        ├── App.vue              # 主布局（顶部导航栏 + 角色感知菜单）
        ├── api/
        │   └── sleep.js         # 全部 API 请求封装
        └── components/
            ├── LoginPage.vue        # 登录页
            ├── RegisterPage.vue     # 注册页（用户名-密码-确认密码）
            ├── PublicHome.vue       # 公开首页（无需登录，展示DATA可视化）
            ├── PublicVis.vue        # 公开可视化分析页
            ├── UserHome.vue         # 用户首页
            ├── UserCenter.vue       # 个人中心（历史报告）
            ├── DataManage.vue       # 数据管理（CSV/ZIP上传/多文件/一键处理）
            ├── VisualizePage.vue    # 可视化分析（6类图表含热力图）
            ├── PredictPage.vue      # 睡眠质量预测
            ├── AdminHome.vue        # 管理员首页
            ├── AdminUsers.vue       # 用户管理 + 全局数据
            └── AdminVis.vue         # 群体可视化分析
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
             │  SQLAlchemy（优先MySQL，自动回退SQLite）
┌────────────▼────────────────────────────────────────┐
│          数据库 (sleep_quality_db)                    │
│  ┌─────────────┬──────────────┬─────────────────┐  │
│  │   users     │sleep_records │analysis_reports │  │
│  │  用户表      │  睡眠数据表   │   分析报告表     │  │
│  └─────────────┴──────────────┴─────────────────┘  │
└─────────────────────────────────────────────────────┘
```


## 快速启动

```bash
# Windows
.\run.bat

# MacOS/Linux
./run.sh
```

> **公开浏览**：无需登录即可查看 DATA 文件夹的示例数据可视化。上传个人数据需注册账号后登录。
## 功能模块（全部通过前端操作）

### 模块一：用户权限管理
| 功能 | 前端页面 | 后端接口 |
|------|---------|---------|
| 用户注册 | `/register` | `POST /api/auth/register` |
| 用户登录 | `/login` | `POST /api/auth/login` |
| 角色识别 | 导航栏自动区分 | `GET /api/auth/me` |
| 权限拦截 | 路由守卫自动跳转 | 装饰器 `@login_required` / `@admin_required` |
| 退出登录 | 导航栏退出按钮 | `POST /api/auth/logout` |

- 普通用户：注册后即可使用全部个人功能（上传数据、可视化、预测）
- 管理员：使用 config.txt 中预设账号登录，可访问全局管理功能
- 公开访问：无需登录即可浏览 DATA 文件夹的示例数据可视化

### 模块二：数据管理
| 功能 | 前端页面 | 后端接口 |
|------|---------|---------|
| CSV 上传 | `/user/data` 拖拽上传 | `POST /api/data/upload` |
| ZIP 上传 | `/user/data` ZIP压缩包 | `POST /api/data/upload_zip` |
| 多文件上传 | `/user/data` 批量选择 | `POST /api/data/upload_multi` |
| 一键处理 | `/user/data` 按钮触发 | `POST /api/data/process_all` |
| 数据预览 | `/user/data` 表格展示 | `GET /api/data/records` |
| 数据删除 | `/user/data` 逐条删除 | `DELETE /api/data/records/<id>` |
| 个人统计 | `/user/home` 首页卡片 | `GET /api/data/stats` |

上传流程：选择 CSV/ZIP/多文件 → 系统自动解析列名 → 计算睡眠衍生指标（效率/比例/质量分）→ 存入数据库 → 一键处理生成可视化数据。

### 模块三：可视化分析
| 功能 | 前端页面 | 后端接口 |
|------|---------|---------|
| 多日趋势图 | `/user/vis` 趋势Tab | `GET /api/vis/trend` |
| 散点图（心率/步数 vs 质量） | `/user/vis` 散点Tab | `GET /api/vis/scatter` |
| 直方图（步数/时长分布） | `/user/vis` 直方图Tab | `GET /api/vis/histogram` |
| 相关性热力图 | `/user/vis` 热力图Tab | `GET /api/vis/correlation` |
| 睡眠阶段占比饼图 | `/user/vis` 阶段Tab | `GET /api/vis/stage_pie` |

所有图表基于 ECharts 渲染，支持悬浮查看数值、图片导出。

### 模块四：预测与分析
| 功能 | 前端页面 | 后端接口 |
|------|---------|---------|
| 睡眠质量预测 | `/user/predict` 输入参数 | `POST /api/predict/score` |
| 多模型对比 | 预测结果面板 | SVR / 线性回归 / 随机森林 |
| 特征重要性分析 | 预测结果面板 | LinearRegression.coef_ / RF.feature_importances_ |
| 个性化建议 | 预测结果面板 | 规则引擎自动生成 |
| 历史报告 | `/user/center` 个人中心 | `GET /api/predict/reports` |

预测流程：用户输入生理参数（或留空使用历史均值）→ SVR/LR/RF 三模型对比选最优 → 输出 1-10 质量分 + 各特征影响权重 + 中文改善建议。

> **模型性能**：线性回归 R²=0.9998，MSE<0.01（5折交叉验证）。运行 `python backend/evaluate_model.py` 查看完整评估报告（含 SHAP 可解释性分析）。

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



## 数据库设计

三张核心表，实现多用户数据隔离：

### 1. `users` — 用户信息表

| # | 列名 | 类型 | 约束 | 说明 |
|---|------|------|------|------|
| 1 | `id` | `INTEGER` | PK, AUTOINCREMENT | 用户唯一标识 |
| 2 | `username` | `VARCHAR(80)` | UNIQUE, NOT NULL, INDEX | 用户名 |
| 3 | `password_hash` | `VARCHAR(256)` | NOT NULL | 密码哈希 (werkzeug) |
| 4 | `role` | `VARCHAR(20)` | NOT NULL, DEFAULT `'user'` | 角色：`user` / `admin` |
| 5 | `created_at` | `DATETIME` | DEFAULT `utcnow` | 注册时间 |

### 2. `sleep_records` — 睡眠数据表

| # | 列名 | 类型 | 约束 | 说明 |
|---|------|------|------|------|
| 1 | `id` | `INTEGER` | PK, AUTOINCREMENT | 记录唯一标识 |
| 2 | `user_id` | `INTEGER` | FK → `users.id`, NOT NULL, INDEX | 所属用户 |
| 3 | `record_date` | `VARCHAR(20)` | NOT NULL | 记录日期 |
| 4 | `deepSleepTime` | `FLOAT` | DEFAULT `0` | 深睡时长 (min) |
| 5 | `shallowSleepTime` | `FLOAT` | DEFAULT `0` | 浅睡时长 (min) |
| 6 | `wakeTime` | `FLOAT` | DEFAULT `0` | 清醒时长 (min) |
| 7 | `REMTime` | `FLOAT` | DEFAULT `0` | REM 时长 (min) |
| 8 | `totalSleepMinutes` | `FLOAT` | DEFAULT `0` | 总睡眠时长 (min) |
| 9 | `deepSleepRatio` | `FLOAT` | DEFAULT `0` | 深睡比例 |
| 10 | `REMRatio` | `FLOAT` | DEFAULT `0` | REM 比例 |
| 11 | `sleepEfficiency` | `FLOAT` | DEFAULT `0` | 睡眠效率 |
| 12 | `wakeRatio` | `FLOAT` | DEFAULT `0` | 清醒比例 |
| 13 | `sleepQualityScore` | `FLOAT` | DEFAULT `0` | 睡眠质量分 (0-100) |
| 14 | `daySteps` | `FLOAT` | DEFAULT `0` | 当日步数 |
| 15 | `dayDistance` | `FLOAT` | DEFAULT `0` | 当日距离 (m) |
| 16 | `dayRunDistance` | `FLOAT` | DEFAULT `0` | 跑步距离 (m) |
| 17 | `dayCalories` | `FLOAT` | DEFAULT `0` | 当日卡路里 (kcal) |
| 18 | `avgHeartRate` | `FLOAT` | DEFAULT `0` | 日均心率 (bpm) |
| 19 | `minHeartRate` | `FLOAT` | DEFAULT `0` | 最小心率 (bpm) |
| 20 | `maxHeartRate` | `FLOAT` | DEFAULT `0` | 最大心率 (bpm) |
| 21 | `stdHeartRate` | `FLOAT` | DEFAULT `0` | 心率标准差 |
| 22 | `nightAvgHR` | `FLOAT` | DEFAULT `0` | 夜间平均心率 (bpm) |
| 23 | `nightAvgRR` | `FLOAT` | DEFAULT `0` | 夜间平均呼吸率 |
| 24 | `naps` | `TEXT` | DEFAULT `'[]'` | 小睡记录 (JSON 数组) |
| 25 | `uploaded_at` | `DATETIME` | DEFAULT `utcnow` | 上传时间 |

### 3. `analysis_reports` — 分析报告表

| # | 列名 | 类型 | 约束 | 说明 |
|---|------|------|------|------|
| 1 | `id` | `INTEGER` | PK, AUTOINCREMENT | 报告唯一标识 |
| 2 | `user_id` | `INTEGER` | FK → `users.id`, NOT NULL, INDEX | 所属用户 |
| 3 | `predicted_score` | `FLOAT` | DEFAULT `0` | 预测睡眠质量分 (0-100) |
| 4 | `input_params` | `TEXT` | DEFAULT `'{}'` | 用户输入参数 (JSON) |
| 5 | `shap_values` | `TEXT` | DEFAULT `'{}'` | SHAP 特征贡献值 (JSON) |
| 6 | `suggestions` | `TEXT` | DEFAULT `''` | 个性化改善建议 |
| 7 | `feature_importance` | `TEXT` | DEFAULT `'{}'` | 特征重要性排序 (JSON) |
| 8 | `created_at` | `DATETIME` | DEFAULT `utcnow` | 报告生成时间 |

> **关系说明**：所有睡眠数据通过 `user_id` 外键绑定到用户，级联删除；报告表记录每次预测的输入参数、输出结果和建议，支持历史回溯。





