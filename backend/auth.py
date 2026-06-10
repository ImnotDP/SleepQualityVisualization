# ============================================================
# 睡眠质量分析系统 - 用户认证模块 (auth)
# 功能：注册、登录、登出、会话检查、权限校验
# ============================================================

import logging
from flask import Blueprint, request, jsonify, session
from models import db, User

log = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


# ---------- 辅助装饰器 ----------

def login_required(f):
    """登录校验装饰器"""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "请先登录"}), 401
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """管理员权限校验装饰器"""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "请先登录"}), 401
        user = User.query.get(session["user_id"])
        if not user or not user.is_admin():
            return jsonify({"error": "需要管理员权限"}), 403
        return f(*args, **kwargs)
    return decorated


def get_current_user():
    """获取当前登录用户"""
    if "user_id" in session:
        return User.query.get(session["user_id"])
    return None


# ---------- 路由 ----------

@auth_bp.route("/register", methods=["POST"])
def register():
    """用户注册"""
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if not username or not password:
        return jsonify({"error": "用户名和密码不能为空"}), 400
    if len(username) < 3:
        return jsonify({"error": "用户名至少3个字符"}), 400
    if len(password) < 6:
        return jsonify({"error": "密码至少6个字符"}), 400

    existing = User.query.filter_by(username=username).first()
    if existing:
        return jsonify({"error": "用户名已存在"}), 409

    user = User(username=username, role="user")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    log.info("新用户注册：%s", username)
    return jsonify({"message": "注册成功", "user": user.to_dict()}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    """用户登录"""
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if not username or not password:
        return jsonify({"error": "用户名和密码不能为空"}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "用户名或密码错误"}), 401

    session["user_id"] = user.id
    session["username"] = user.username
    session["role"] = user.role

    log.info("用户登录：%s (角色：%s)", username, user.role)
    return jsonify({
        "message": "登录成功",
        "user": user.to_dict(),
    })


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """用户登出"""
    session.clear()
    return jsonify({"message": "已退出登录"})


@auth_bp.route("/me", methods=["GET"])
def current_user_info():
    """获取当前登录用户信息"""
    user = get_current_user()
    if not user:
        return jsonify({"error": "未登录"}), 401
    return jsonify({"user": user.to_dict()})


@auth_bp.route("/check_admin", methods=["GET"])
def check_admin():
    """检查当前用户是否为管理员"""
    user = get_current_user()
    if not user:
        return jsonify({"error": "未登录"}), 401
    return jsonify({"is_admin": user.is_admin()})
