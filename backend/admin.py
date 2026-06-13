import logging
from datetime import datetime
from flask import Blueprint, request, jsonify

from models import db, User, SleepRecord, AnalysisReport
from auth import admin_required, get_current_user

log = logging.getLogger(__name__)
admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

@admin_bp.route("/dashboard", methods=["GET"])
@admin_required
def dashboard():
    """管理员首页：全局统计概览"""
    total_users = User.query.count()
    total_records = SleepRecord.query.count()
    total_reports = AnalysisReport.query.count()

    # 今日新增
    today = datetime.utcnow().strftime("%Y-%m-%d")
    new_users_today = User.query.filter(
        User.created_at >= f"{today} 00:00:00").count()
    new_records_today = SleepRecord.query.filter(
        SleepRecord.uploaded_at >= f"{today} 00:00:00").count()

    # 平均睡眠质量
    records = SleepRecord.query.all()
    avg_quality = 0
    if records:
        scores = [r.sleepQualityScore for r in records if r.sleepQualityScore]
        avg_quality = round(sum(scores) / len(scores), 2) if scores else 0

    return jsonify({
        "stats": {
            "total_users": total_users,
            "total_records": total_records,
            "total_reports": total_reports,
            "new_users_today": new_users_today,
            "new_records_today": new_records_today,
            "avg_quality_all_users": avg_quality,
        },
    })


# ---------- 用户管理 ----------

@admin_bp.route("/users", methods=["GET"])
@admin_required
def list_users():
    """管理员查看所有用户"""
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 50))

    query = User.query.order_by(User.created_at.desc())
    total = query.count()
    users = query.offset((page - 1) * page_size).limit(page_size).all()

    user_list = []
    for u in users:
        d = u.to_dict()
        d["record_count"] = SleepRecord.query.filter_by(user_id=u.id).count()
        d["report_count"] = AnalysisReport.query.filter_by(user_id=u.id).count()
        user_list.append(d)

    return jsonify({
        "data": user_list,
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@admin_required
def delete_user(user_id):
    """管理员删除用户及其所有数据"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "用户不存在"}), 404
    if user.is_admin():
        return jsonify({"error": "不能删除管理员账号"}), 403

    # 级联删除关联数据
    SleepRecord.query.filter_by(user_id=user_id).delete()
    AnalysisReport.query.filter_by(user_id=user_id).delete()
    db.session.delete(user)
    db.session.commit()

    log.info("管理员删除了用户：%s", user.username)
    return jsonify({"message": f"已删除用户 {user.username} 及其所有数据"})


# ---------- 群体数据聚合 ----------

@admin_bp.route("/group_quality_distribution", methods=["GET"])
@admin_required
def group_quality_distribution():
    """全体用户睡眠质量分分布"""
    records = SleepRecord.query.all()
    scores = [r.sleepQualityScore for r in records if r.sleepQualityScore]

    # 分段统计
    bins = {"0-20": 0, "20-40": 0, "40-60": 0, "60-80": 0, "80-100": 0}
    for s in scores:
        if s < 20:
            bins["0-20"] += 1
        elif s < 40:
            bins["20-40"] += 1
        elif s < 60:
            bins["40-60"] += 1
        elif s < 80:
            bins["60-80"] += 1
        else:
            bins["80-100"] += 1

    return jsonify({
        "distribution": [{"range": k, "count": v} for k, v in bins.items()],
        "total_records": len(scores),
        "avg_quality": round(sum(scores) / len(scores), 2) if scores else 0,
    })


@admin_bp.route("/group_sleep_structure", methods=["GET"])
@admin_required
def group_sleep_structure():
    """全体用户睡眠结构总览"""
    records = SleepRecord.query.all()
    total_deep = sum(r.deepSleepTime or 0 for r in records)
    total_shallow = sum(r.shallowSleepTime or 0 for r in records)
    total_rem = sum(r.REMTime or 0 for r in records)
    total_wake = sum(r.wakeTime or 0 for r in records)

    return jsonify({
        "stages": [
            {"name": "深睡", "value": round(total_deep, 1), "avg_per_person": round(total_deep / max(len(records), 1), 1)},
            {"name": "浅睡", "value": round(total_shallow, 1), "avg_per_person": round(total_shallow / max(len(records), 1), 1)},
            {"name": "REM", "value": round(total_rem, 1), "avg_per_person": round(total_rem / max(len(records), 1), 1)},
            {"name": "清醒", "value": round(total_wake, 1), "avg_per_person": round(total_wake / max(len(records), 1), 1)},
        ],
        "total_records": len(records),
    })


@admin_bp.route("/group_influence_ranking", methods=["GET"])
@admin_required
def group_influence_ranking():
    """
    群体影响因素排行：基于全体数据计算各特征与睡眠质量的相关系数，
    按绝对值排序返回。
    """
    records = SleepRecord.query.all()
    import math

    features = [
        "totalSleepMinutes", "deepSleepTime", "shallowSleepTime", "REMTime",
        "wakeTime", "sleepEfficiency", "daySteps", "dayCalories", "avgHeartRate",
    ]
    labels = {
        "totalSleepMinutes": "总睡眠时长", "deepSleepTime": "深睡时长",
        "shallowSleepTime": "浅睡时长", "REMTime": "REM时长",
        "wakeTime": "清醒时长", "sleepEfficiency": "睡眠效率",
        "daySteps": "日步数", "dayCalories": "日卡路里", "avgHeartRate": "平均心率",
    }

    quality = [r.sleepQualityScore or 0 for r in records]
    ranking = []
    for feat in features:
        vals = [getattr(r, feat, 0) or 0 for r in records]
        n = len(vals)
        if n < 2:
            ranking.append({"feature": feat, "label": labels.get(feat, feat), "correlation": 0})
            continue
        mx, my = sum(vals) / n, sum(quality) / n
        sx = math.sqrt(sum((v - mx) ** 2 for v in vals))
        sy = math.sqrt(sum((q - my) ** 2 for q in quality))
        if sx == 0 or sy == 0:
            ranking.append({"feature": feat, "label": labels.get(feat, feat), "correlation": 0})
            continue
        corr = sum((vals[i] - mx) * (quality[i] - my) for i in range(n)) / (sx * sy)
        ranking.append({
            "feature": feat,
            "label": labels.get(feat, feat),
            "correlation": round(corr, 4),
        })

    ranking.sort(key=lambda x: abs(x["correlation"]), reverse=True)

    return jsonify({
        "ranking": ranking,
        "total_records": len(records),
    })


# ---------- 全局数据管理 ----------

@admin_bp.route("/all_records", methods=["GET"])
@admin_required
def admin_all_records():
    """管理员查看全站所有用户数据"""
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 30))
    user_id_filter = request.args.get("user_id")

    query = SleepRecord.query.order_by(SleepRecord.uploaded_at.desc())
    if user_id_filter:
        query = query.filter_by(user_id=int(user_id_filter))
    total = query.count()
    records = query.offset((page - 1) * page_size).limit(page_size).all()

    return jsonify({
        "data": [r.to_dict() for r in records],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@admin_bp.route("/delete_record/<int:record_id>", methods=["DELETE"])
@admin_required
def admin_delete_record(record_id):
    """管理员删除任意记录"""
    record = SleepRecord.query.get(record_id)
    if not record:
        return jsonify({"error": "记录不存在"}), 404
    db.session.delete(record)
    db.session.commit()
    return jsonify({"message": "删除成功"})
