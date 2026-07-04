import os
import sys
import json
import atexit
import secrets
import logging
from datetime import datetime

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
# 每次启动生成随机 SECRET_KEY，服务重启后所有旧会话自动失效
_base_secret = _cfg.get("SECRET_KEY", "default-secret-key")
app.config["SECRET_KEY"] = _base_secret + "_" + secrets.token_hex(16)

# 数据库 URI：优先 MySQL，不可用时自动回退 SQLite
_mysql_uri = (
    f"mysql+pymysql://{_cfg.get('MYSQL_USER', 'root')}:{_cfg.get('MYSQL_PASSWORD', 'root')}"
    f"@{_cfg.get('MYSQL_HOST', '127.0.0.1')}:{_cfg.get('MYSQL_PORT', '3306')}"
    f"/{_cfg.get('MYSQL_DATABASE', 'sleep_quality_db')}"
    f"?charset={_cfg.get('MYSQL_CHARSET', 'utf8mb4')}"
)
_sqlite_uri = f"sqlite:///{os.path.join(BASE_DIR, 'sleep_quality.db')}"

def _test_mysql():
    try:
        import pymysql
        conn = pymysql.connect(
            host=_cfg.get("MYSQL_HOST", "127.0.0.1"),
            port=int(_cfg.get("MYSQL_PORT", "3306")),
            user=_cfg.get("MYSQL_USER", "root"),
            password=_cfg.get("MYSQL_PASSWORD", "root"),
            charset=_cfg.get("MYSQL_CHARSET", "utf8mb4"),
            connect_timeout=3,
        )
        conn.close()
        return True, None
    except Exception as e:
        return False, str(e)

_use_mysql, _mysql_error = _test_mysql()
if _use_mysql:
    app.config["SQLALCHEMY_DATABASE_URI"] = _mysql_uri
    log.info("使用 MySQL 数据库")
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = _sqlite_uri
    log.warning("MySQL 不可用，回退 SQLite：%s", _mysql_error)
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
    if _use_mysql:
        db_name = _cfg.get("MYSQL_DATABASE", "sleep_quality_db")
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
            log.warning("无法自动创建数据库：%s", e)

    try:
        with app.app_context():
            db.create_all()
            log.info("数据库表已就绪")

            admin_username = _cfg.get("ADMIN_DEFAULT_USERNAME", "admin")
            admin_password = _cfg.get("ADMIN_DEFAULT_PASSWORD", "admin123")
            existing = User.query.filter_by(username=admin_username).first()
            if not existing:
                admin = User(username=admin_username, role="admin")
                admin.set_password(admin_password)
                db.session.add(admin)
                db.session.commit()
                log.info("默认管理员账号已就绪")
            else:
                log.info("管理员账号已存在")
    except Exception as e:
        log.error("数据库初始化失败：%s", e)
        raise


# ---------- 根路由 ----------
@app.route("/")
def index():
    return {"service": "睡眠质量分析系统 API", "version": "0.0.1"}


@app.route("/api/status")
def api_status():
    return {
        "mysql_available": _use_mysql,
        "db_type": "mysql" if _use_mysql else "sqlite",
        "mysql_error": _mysql_error,
    }


# ---------- 启动时自动检测并导入 DATA 数据 ----------
def _compute_data_state(data_dir: str) -> str:
    """计算 DATA 目录的状态哈希（基于文件名 + 修改时间 + 文件大小）"""
    import hashlib
    if not os.path.isdir(data_dir):
        return ""
    items = []
    for root, dirs, files in os.walk(data_dir):
        for fname in sorted(files):
            fpath = os.path.join(root, fname)
            try:
                stat = os.stat(fpath)
                items.append(f"{fpath}|{stat.st_mtime}|{stat.st_size}")
            except OSError:
                pass
    return hashlib.md5("|".join(items).encode()).hexdigest() if items else ""


def _auto_import_data():
    """
    每次启动时完整处理：清空旧数据 → 重新导入 → 重新分析
    不做任何缓存检测，保证每次启动都是全新状态。
    """
    from models import SleepRecord, User
    data_dir = os.path.join(ROOT_DIR, "DATA")
    if not os.path.isdir(data_dir):
        log.info("DATA 目录不存在，跳过自动导入")
        return

    current_state = _compute_data_state(data_dir)
    if not current_state:
        log.info("DATA 目录为空，跳过自动导入")
        return

    # 清空旧数据（每次启动全新导入）
    with app.app_context():
        try:
            from models import AnalysisReport
            AnalysisReport.query.delete()
            SleepRecord.query.delete()
            db.session.commit()
            log.info("已清空旧数据，准备全新导入")
        except Exception as e:
            log.warning("清空旧数据时出错：%s", e)
            db.session.rollback()

    log.info("开始完整预处理管线...")
    try:
        from pipeline import run_full_pipeline, import_records_to_db
        # 1. 运行完整预处理管线
        records = run_full_pipeline(data_dir)
        if not records:
            log.warning("预处理管线未产生任何记录")
            return

        # 2. 入库到 admin 用户
        with app.app_context():
            admin_user = User.query.filter_by(role="admin").first()
            if not admin_user:
                log.error("无管理员用户，无法导入")
                return
            total = import_records_to_db(records, admin_user.id)
            log.info("✅ DATA 数据导入完成：%s 条记录", total)

        # 3. 执行分析引擎（训练模型 + 生成分析报告入库）
        try:
            from analysis_engine import run_auto_analysis
            from models import AnalysisReport
            with app.app_context():
                result = run_auto_analysis()
                log.info("自动分析完成，最佳模型：%s", result.get("regression", {}).get("best_model", "N/A"))

                admin_user = User.query.filter_by(role="admin").first()
                if admin_user and "report" in result:
                    report_data = result["report"]
                    report = AnalysisReport(
                        user_id=admin_user.id,
                        predicted_score=result.get("data_summary", {}).get("avg_score", 0),
                        input_params=json.dumps(result.get("data_summary", {}), ensure_ascii=False),
                        shap_values=json.dumps(result.get("regression", {}), ensure_ascii=False),
                        suggestions="\n".join(report_data.get("suggestions", [])),
                        feature_importance=json.dumps(
                            result.get("regression", {}).get("rf", {}).get("feature_importance", []), ensure_ascii=False),
                    )
                    db.session.add(report)
                    db.session.commit()
                    log.info("✅ 分析报告已入库")
        except Exception as e:
            log.warning("自动分析失败（数据已导入，可稍后手动触发分析）：%s", e)

    except Exception as e:
        log.warning("自动导入 DATA 数据失败（可手动导入）：%s", e)


# ---------- 关闭时清理所有缓存文件 ----------
def _cleanup_on_exit():
    """服务关闭时删除所有缓存/状态文件"""
    files_to_clean = [
        os.path.join(BASE_DIR, ".data_state.json"),
        os.path.join(BASE_DIR, ".model_cache.json"),
    ]
    for fp in files_to_clean:
        if os.path.exists(fp):
            try:
                os.remove(fp)
                log.info("已清理缓存文件：%s", os.path.basename(fp))
            except Exception as e:
                log.warning("清理缓存文件失败 %s：%s", fp, e)

atexit.register(_cleanup_on_exit)


# ---------- 启动 ----------
if __name__ == "__main__":
    try:
        _init_db()
    except Exception as e:
        log.error("数据库初始化失败，后端无法启动：%s", e)
        sys.exit(1)

    # 每次启动完整导入 DATA 数据并重新分析
    _auto_import_data()

    host = _cfg.get("FLASK_HOST", "0.0.0.0")
    port = int(_cfg.get("FLASK_PORT", "5000"))
    log.info("后端启动：http://%s:%s", host, port)
    app.run(host=host, port=port, debug=False)
