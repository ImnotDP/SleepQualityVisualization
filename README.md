# Python睡眠质量分析预测 睡眠质量可视化



## 系统需求

| 组件 | 最低版本 | 说明 |
|------|----------|------|
| Python | ≥ 3.10 | Conda 环境内置 3.12.13 |
| Node.js | ≥ 18 | 前端构建与运行 |
| npm | ≥ 9 | Node.js 自带 |
| Conda | Miniconda / Anaconda / Miniforge | 仅 Conda 安装方式需要 |
| MySQL | ≥ 5.7 (推荐 8.0) | 数据库存储 |

> **注意**：如果使用 Python venv 方式安装，无需 Conda；Node.js 仅前端构建需要。

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



## 数据库设计

三张核心表，实现多用户数据隔离：

| 表名 | 说明 | 关键字段 |
|------|------|---------|
| `users` | 用户信息表 | id, username, password_hash, role(user/admin), created_at |
| `sleep_records` | 睡眠数据表 | id, user_id(FK), record_date, deepSleepTime, shallowSleepTime, REMTime, wakeTime, sleepQualityScore, daySteps, avgHeartRate, ... |
| `analysis_reports` | 分析报告表 | id, user_id(FK), predicted_score, input_params(JSON), shap_values(JSON), suggestions, feature_importance(JSON), created_at |

- 所有睡眠数据通过 `user_id` 外键绑定到用户，实现数据隔离
- 报告表记录每次预测的输入参数、输出结果和建议，支持历史回溯



