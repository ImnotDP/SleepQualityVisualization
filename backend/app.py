# ============================================================
# 睡眠质量分析系统 - Flask 主应用入口
#
# 启动方式：
#   cd backend && python app.py
#
# 模块划分（一个功能一个 py 文件）：
#   models.py      - 数据库模型
#   auth.py        - 用户注册/登录/登出/权限
#   data_manage.py - 数据上传/预览/预处理/删除
#   visualize.py   - 可视化数据接口
#   predict.py     - 睡眠质量预测/特征分析/建议
#   admin.py       - 管理员全局统计/用户管理
# ============================================================

import os
import sys
import logging

from flask import Flask
from flask_cors import CORS
from flask_login import LoginManager

# ---------- 配置加载 ----------
def _load_config(config_path: str) -> dict:
    cfg = {}
    with open(config_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                cfg[key.strip()] = val.strip()
    return cfg

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
CONFIG_PATH = os.path.join(BASE_DIR, "config.txt")
_cfg = _load_config(CONFIG_PATH)

# ---------- 日志 ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# ---------- Flask 应用工厂 ----------
app = Flask(__name__)
app.config["SECRET_KEY"] = _cfg.get("SECRET_KEY", "default-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+pymysql://{_cfg.get('MYSQL_USER', 'root')}:{_cfg.get('MYSQL_PASSWORD', 'root')}"
    f"@{_cfg.get('MYSQL_HOST', '127.0.0.1')}:{_cfg.get('MYSQL_PORT', '3306')}"
    f"/{_cfg.get('MYSQL_DATABASE', 'sleep_quality_db')}"
    f"?charset={_cfg.get('MYSQL_CHARSET', 'utf8mb4')}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_size": 5,
    "pool_recycle": 3600,
}

CORS(app, supports_credentials=True)

# ---------- 数据库初始化 ----------
from models import db, User
db.init_app(app)

# ---------- Flask-Login 初始化 ----------
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------- 注册蓝图（一个功能一个文件） ----------
from auth import auth_bp
from data_manage import data_bp
from visualize import vis_bp
from predict import predict_bp
from admin import admin_bp

app.register_blueprint(auth_bp)
app.register_blueprint(data_bp)
app.register_blueprint(vis_bp)
app.register_blueprint(predict_bp)
app.register_blueprint(admin_bp)


# ---------- 创建数据库表 & 默认管理员 ----------
def _init_db():
    """创建数据库和表，并确保默认管理员账号存在"""
    db_name = _cfg.get("MYSQL_DATABASE", "sleep_quality_db")
    # 先创建数据库（如果不存在）
    import pymysql
    try:
        conn = pymysql.connect(
            host=_cfg.get("MYSQL_HOST", "127.0.0.1"),
            port=int(_cfg.get("MYSQL_PORT", "3306")),
            user=_cfg.get("MYSQL_USER", "root"),
            password=_cfg.get("MYSQL_PASSWORD", "root"),
            charset=_cfg.get("MYSQL_CHARSET", "utf8mb4"),
        )
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                f"DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.close()
        log.info("数据库 %s 已就绪", db_name)
    except Exception as e:
        log.warning("无法自动创建数据库（可能 MySQL 未启动）：%s", e)

    with app.app_context():
        db.create_all()
        log.info("数据库表已就绪")

        # 创建默认管理员
        admin_username = _cfg.get("ADMIN_DEFAULT_USERNAME", "admin")
        admin_password = _cfg.get("ADMIN_DEFAULT_PASSWORD", "admin123")
        existing = User.query.filter_by(username=admin_username).first()
        if not existing:
            admin = User(username=admin_username, role="admin")
            admin.set_password(admin_password)
            db.session.add(admin)
            db.session.commit()
            log.info("默认管理员账号已创建：%s / %s", admin_username, admin_password)
        else:
            log.info("管理员账号已存在：%s", admin_username)


# ---------- 根路由 ----------
@app.route("/")
def index():
    return {"service": "睡眠质量分析系统 API", "version": "2.0"}


# ---------- 启动 ----------
if __name__ == "__main__":
    _init_db()

    host = _cfg.get("FLASK_HOST", "0.0.0.0")
    port = int(_cfg.get("FLASK_PORT", "5000"))
    debug = _cfg.get("FLASK_DEBUG", "true").lower() == "true"

    log.info("=" * 60)
    log.info("🌙 睡眠质量分析系统 v2.0 启动")
    log.info("   后端地址：http://%s:%s", host, port)
    log.info("   前端地址：http://localhost:%s", _cfg.get("FRONTEND_PORT", "3000"))
    log.info("   管理员账号：%s", _cfg.get("ADMIN_DEFAULT_USERNAME", "admin"))
    log.info("   调试模式：%s", debug)
    log.info("=" * 60)

    app.run(host=host, port=port, debug=debug)
