# 睡眠质量分析与可视化系统

> 基于 Flask + Vue 3 + 机器学习 的睡眠质量分析预测平台，支持小米手环 Zepp 导出的 CSV 数据。

---

## 系统需求

| 组件 | 最低版本 | 说明 |
|------|----------|------|
| Python | ≥ 3.10 | 推荐 3.12+ |
| Node.js | ≥ 18 | 前端构建与运行 |
| npm | ≥ 9 | Node.js 自带 |
| Conda | Miniconda / Anaconda | 仅 Conda 安装方式需要 |
| MySQL | ≥ 5.7（可选） | 未安装时自动回退 SQLite |

> **注意**：MySQL 为可选依赖，系统启动时自动检测——可用则使用 MySQL，不可用则自动回退 SQLite，无需手动配置。

---

## 一、环境搭建

### 方式 A：Conda（推荐）

```bash
conda env create -f environment.yml
conda activate sleepQualityVisualization
```

### 方式 B：Python venv

**Windows：**
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**Linux / Mac：**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> 也可直接运行 `install_with_python.bat`（Windows）或 `install_with_python.sh`（Linux/Mac）一键完成 venv 创建和依赖安装。

### 更新依赖（git pull 后）

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
├── requirements.txt             # pip 依赖清单
├── run.bat                      # Windows 一键启动脚本
├── run.sh                       # Linux/Mac 一键启动脚本
├── install_with_python.bat      # Windows venv 快速安装
├── install_with_python.sh       # Linux/Mac venv 快速安装
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


## 二、初次部署完整指南

> 以下步骤假设你已完成 **环境搭建**（Conda 或 venv 已激活，Python 依赖已安装）。

---

### 🚀 推荐方式：一键启动（`run.bat` / `run.sh`）

项目提供了全自动启动脚本，自动完成：环境检测 → 前端依赖安装 → 前端构建 → 启动后端 → 启动前端 → 打开浏览器。

**Windows：**
```bash
.\run.bat
```

**Linux / Mac：**
```bash
chmod +x run.sh
./run.sh
```

`run.bat` 的工作流程（`run.sh` 同理）：

1. 检测 Node.js 是否安装
2. 若 `.venv` 不存在，自动创建 venv 并 `pip install -r requirements.txt`
3. 若 `frontend/node_modules` 不存在，自动 `npm install`
4. 执行 `npm run build` 构建前端
5. 启动后端（`python app.py`）
6. 轮询等待后端就绪（最多 60 秒）
7. 启动前端静态服务（`node serve.cjs`）
8. 自动打开浏览器访问 `http://localhost:3000`

> **首次运行** 会自动安装依赖，耗时较长（取决于网络）。后续启动直接复用已有环境，几秒内完成。

---

### 🔧 手动分步启动（排查问题或自定义配置时使用）

如果你需要精细控制每个步骤，或一键脚本遇到问题，可按以下步骤手动启动。

---

#### 手动步骤①：配置 `config.txt`

后端配置文件位于 `backend/config.txt`。首次部署需要检查和修改以下关键项：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `MYSQL_HOST` | `127.0.0.1` | MySQL 地址（不用 MySQL 可忽略） |
| `MYSQL_PORT` | `3306` | MySQL 端口 |
| `MYSQL_USER` | `root` | MySQL 用户名 |
| `MYSQL_PASSWORD` | `root` | MySQL 密码 |
| `MYSQL_DATABASE` | `sleep_quality_db` | 数据库名（会自动创建） |
| `FLASK_PORT` | `5000` | 后端 API 端口 |
| `FRONTEND_PORT` | `3000` | 前端页面端口 |
| `SECRET_KEY` | `sleep-quality-secret-key-change-in-production` | **生产环境务必修改** |
| `ADMIN_DEFAULT_USERNAME` | `admin` | 默认管理员用户名 |
| `ADMIN_DEFAULT_PASSWORD` | `admin123` | 默认管理员密码 |
| `DEEPSEEK_API_KEY` | `sk-xxx...` | DeepSeek API 密钥（AI 建议功能） |

**最小配置（仅 SQLite，开箱即用）：** 无需修改任何配置，直接跳到步骤 2。

**使用 MySQL（可选）：**
1. 确保 MySQL 服务已启动
2. 修改 `MYSQL_HOST`、`MYSQL_PORT`、`MYSQL_USER`、`MYSQL_PASSWORD`
3. 无需手动创建数据库——系统启动时会自动创建 `sleep_quality_db`

**使用 DeepSeek AI 建议（可选）：**
1. 前往 [platform.deepseek.com](https://platform.deepseek.com) 注册并获取 API Key
2. 将 `DEEPSEEK_API_KEY` 替换为你的密钥
3. 不配置也不影响系统核心功能（预测、可视化均可正常使用）

---

#### 手动步骤②：准备数据（可选）

如果你想用自己的手环数据，将 Zepp App 导出的 CSV 文件放入 `DATA/` 目录下的对应子文件夹：

```
DATA/
├── SLEEP/              # 睡眠汇总数据
├── SLEEP_MINUTE/       # 逐分钟睡眠阶段
├── ACTIVITY/           # 每日活动汇总
├── ACTIVITY_MINUTE/    # 逐分钟步数
├── ACTIVITY_STAGE/     # 活动阶段
├── HEARTRATE/          # 心率数据
└── HEARTRATE_AUTO/     # 自动心率监测
```

> 系统已预置示例数据，无需额外准备即可体验全部功能。

---

#### 手动步骤③：安装前端依赖并构建

```bash
cd frontend

# 安装 npm 依赖（仅首次需要）
npm install

# 构建生产版本（生成 dist/ 目录）
npm run build

cd ..
```

> 构建产物输出到 `frontend/dist/`，由 `serve.cjs` 作为静态文件提供服务。

---

#### 手动步骤④：启动后端服务

确保已激活 Python 环境（Conda 或 venv）：

```bash
cd backend
python app.py
```

启动成功后会看到类似输出：

```
[INFO] 使用 SQLite 数据库
[INFO] 数据库 sleep_quality_db 已就绪
[INFO] 数据库表已就绪
[INFO] 默认管理员账号已就绪
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
```

> 后端默认监听 `http://127.0.0.1:5000`。请保持此终端窗口打开。

---

#### 手动步骤⑤：启动前端服务

**新开一个终端窗口**，在项目根目录下：

```bash
cd frontend
node serve.cjs
```

启动成功后会看到：

```
Sleep Quality Frontend Server
Listening on http://localhost:3000
```

---

#### 手动步骤⑥：访问系统

在浏览器中打开 **http://localhost:3000**，即可进入系统首页。

| 访问方式 | URL | 说明 |
|----------|-----|------|
| 前端页面 | `http://localhost:3000` | 用户入口 |
| 后端 API | `http://127.0.0.1:5000` | API 根路径 |
| API 状态检查 | `http://127.0.0.1:5000/api/status` | 数据库中英文/MySQL 可用性 |

---

#### 手动步骤⑦：登录与使用

| 角色 | 用户名 | 密码 | 说明 |
|------|--------|------|------|
| 管理员 | `admin` | `admin123` | 全局管理、用户管理、群体分析 |
| 普通用户 | 自行注册 | 自行设定 | 上传数据、个人可视化、睡眠预测 |

1. **公开浏览**：无需登录，首页即可查看 DATA 目录中预置数据的可视化图表
2. **注册账号**：点击导航栏"注册"，填写用户名和密码
3. **上传个人数据**：登录后进入"数据管理"，上传你的手环 CSV/ZIP 文件
4. **一键处理**：上传后点击"一键处理"，系统自动完成：预处理 → 特征工程 → 模型训练 → 生成报告
5. **可视化分析**：查看散点图、直方图、热力图、睡眠阶段占比、趋势图等
6. **质量预测**：输入睡眠参数，系统用最优模型预测你的睡眠质量评分（1-10 分）

---

### 停止服务

- **一键脚本启动的**：关闭两个分别标有 `Backend` 和 `Frontend` 的终端窗口
- **手动启动的**：在各自终端窗口中按 `Ctrl + C`

---

### 验证部署是否成功

在浏览器中依次检查：

1. **`http://localhost:3000`** — 能看到系统首页，顶部有导航栏
2. **`http://localhost:3000/public`** — 公开可视化页面，图表正常加载
3. **`http://127.0.0.1:5000/api/status`** — 返回 JSON，`db_type` 为 `sqlite` 或 `mysql`
4. **注册并登录** — 能够正常注册新用户、登录、上传数据

---

## 三、常见问题排查

### `run.bat` / `run.sh` 一键脚本问题

| 现象 | 原因 | 解决方法 |
|------|------|----------|
| `Node.js not found` | 未安装 Node.js | 安装 Node.js ≥ 18（[nodejs.org](https://nodejs.org)） |
| `venv create failed` | Python 未安装或不在 PATH | 确认 `python --version` 可用 |
| `pip install failed` | 网络问题 | 切换 pip 镜像：`pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple` |
| `npm install failed` | 网络或权限问题 | 手动 `cd frontend && npm install`，或切换镜像 |
| `npm run build failed` | 前端代码编译错误 | 检查 `frontend/src/` 下 `.vue` 文件语法 |
| `Backend took too long` | 后端启动超时 | 检查 `backend/config.txt` 配置，确认端口未被占用 |
| 两个窗口闪退 | Python 或 Node.js 环境异常 | 改用**手动分步启动**方式排查具体错误 |

### 后端启动失败

| 现象 | 原因 | 解决方法 |
|------|------|----------|
| `ModuleNotFoundError: No module named 'flask'` | Python 环境未激活或依赖未安装 | 激活环境后执行 `pip install -r requirements.txt` |
| `Address already in use` / 端口被占用 | 5000 端口已被其他程序占用 | 修改 `config.txt` 中 `FLASK_PORT`，同时修改 `FRONTEND_API_TARGET` |
| `MySQL connection refused` | MySQL 未启动或配置错误 | 检查 MySQL 服务状态，或忽略（系统自动回退 SQLite） |
| `config.txt not found` | 配置文件缺失 | 将 `rename_it_to_config,txt` 重命名为 `config.txt` |

### 前端构建失败

| 现象 | 原因 | 解决方法 |
|------|------|----------|
| `npm: command not found` | Node.js 未安装 | 安装 Node.js ≥ 18（[nodejs.org](https://nodejs.org)） |
| `npm install` 报错 | 网络问题或依赖冲突 | 尝试 `npm install --registry=https://registry.npmmirror.com` |
| `dist not found` | 未执行构建 | 运行 `cd frontend && npm run build` |
| 页面空白/API 请求失败 | 后端未启动或端口不匹配 | 确认后端已启动，检查 `serve.cjs` 代理配置 |

### 数据相关

| 现象 | 原因 | 解决方法 |
|------|------|----------|
| 首页图表无数据 | DATA 目录下无 CSV 文件 | 确保 `DATA/` 各子目录中有 CSV 文件，然后重启后端 |
| 上传 CSV 失败 | 文件格式不匹配或过大 | CSV 需符合 Zepp 导出格式，单文件不超过 50MB（可在 config.txt 调整） |
| "一键处理"卡住 | 数据量大、模型训练耗时 | 耐心等待，首次处理可能需要 30 秒 ~ 2 分钟 |

### 端口修改后如何联动

如果你修改了 `config.txt` 中的 `FLASK_PORT`：

1. 同步修改 `FRONTEND_API_TARGET=http://127.0.0.1:<新端口>`
2. 重启后端和前端服务

---

## 四、功能模块（全部通过前端操作）

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





