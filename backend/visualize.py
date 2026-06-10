# ============================================================
# 睡眠质量分析系统 - 可视化数据模块 (visualize)
# 功能：为前端 ECharts 提供可视化所需数据
#   散点图、直方图、热力图、相关性矩阵、阶段占比、趋势图
# ============================================================

import logging
from flask import Blueprint, request, jsonify
from models import SleepRecord
from auth import login_required, get_current_user, admin_required

log = logging.getLogger(__name__)
vis_bp = Blueprint("visualize", __name__, url_prefix="/api/vis")


def _get_user_records(user_id: int):
    return SleepRecord.query.filter_by(user_id=user_id).order_by(
        SleepRecord.record_date.asc()).all()


def _records_to_list(records):
    return [r.to_dict() for r in records]


# ---------- 散点图数据 ----------

@vis_bp.route("/scatter", methods=["GET"])
@login_required
def scatter_data():
    """
    返回散点图数据：
    - 心率 vs 睡眠质量
    - 步数 vs 睡眠质量
    """
    user = get_current_user()
    records = _get_user_records(user.id)

    hr_vs_quality = []
    steps_vs_quality = []
    for r in records:
        if r.avgHeartRate and r.sleepQualityScore:
            hr_vs_quality.append([round(r.avgHeartRate, 1), round(r.sleepQualityScore, 1)])
        if r.daySteps and r.sleepQualityScore:
            steps_vs_quality.append([round(r.daySteps, 0), round(r.sleepQualityScore, 1)])

    return jsonify({
        "hr_vs_quality": hr_vs_quality,
        "steps_vs_quality": steps_vs_quality,
    })


# ---------- 直方图数据 ----------

@vis_bp.route("/histogram", methods=["GET"])
@login_required
def histogram_data():
    """步数分布直方图、睡眠时长分布直方图"""
    user = get_current_user()
    records = _get_user_records(user.id)

    steps = [r.daySteps for r in records if r.daySteps]
    sleep_dur = [r.totalSleepMinutes for r in records if r.totalSleepMinutes]

    return jsonify({
        "steps_distribution": steps,
        "sleep_duration_distribution": sleep_dur,
    })


# ---------- 相关性热力图 ----------

@vis_bp.route("/correlation", methods=["GET"])
@login_required
def correlation_data():
    """返回指标相关性矩阵"""
    user = get_current_user()
    records = _get_user_records(user.id)

    fields = [
        "sleepQualityScore", "totalSleepMinutes", "deepSleepTime",
        "shallowSleepTime", "REMTime", "wakeTime", "sleepEfficiency",
        "deepSleepRatio", "REMRatio", "daySteps", "dayCalories",
        "avgHeartRate", "nightAvgHR",
    ]
    matrix = {}
    data_points = {f: [] for f in fields}
    for r in records:
        for f in fields:
            val = getattr(r, f, None)
            data_points[f].append(val if val is not None else 0)

    # 计算皮尔逊相关系数矩阵
    import math
    for f1 in fields:
        for f2 in fields:
            x = data_points[f1]
            y = data_points[f2]
            n = len(x)
            if n < 2:
                matrix[f"{f1}|{f2}"] = 0
                continue
            mx = sum(x) / n
            my = sum(y) / n
            sx = math.sqrt(sum((xi - mx) ** 2 for xi in x))
            sy = math.sqrt(sum((yi - my) ** 2 for yi in y))
            if sx == 0 or sy == 0:
                matrix[f"{f1}|{f2}"] = 0
                continue
            cov = sum((x[i] - mx) * (y[i] - my) for i in range(n))
            matrix[f"{f1}|{f2}"] = round(cov / (sx * sy), 4)

    return jsonify({
        "fields": fields,
        "field_labels": {
            "sleepQualityScore": "睡眠质量分",
            "totalSleepMinutes": "总睡眠时长",
            "deepSleepTime": "深睡时长",
            "shallowSleepTime": "浅睡时长",
            "REMTime": "REM时长",
            "wakeTime": "清醒时长",
            "sleepEfficiency": "睡眠效率",
            "deepSleepRatio": "深睡比例",
            "REMRatio": "REM比例",
            "daySteps": "步数",
            "dayCalories": "卡路里",
            "avgHeartRate": "平均心率",
            "nightAvgHR": "夜间心率",
        },
        "correlation_matrix": matrix,
    })


# ---------- 睡眠阶段占比 ----------

@vis_bp.route("/stage_pie", methods=["GET"])
@login_required
def stage_pie_data():
    """睡眠阶段占比（深睡/浅睡/REM/清醒）"""
    user = get_current_user()
    records = _get_user_records(user.id)

    total_deep = sum(r.deepSleepTime or 0 for r in records)
    total_shallow = sum(r.shallowSleepTime or 0 for r in records)
    total_rem = sum(r.REMTime or 0 for r in records)
    total_wake = sum(r.wakeTime or 0 for r in records)

    return jsonify({
        "stages": [
            {"name": "深睡", "value": round(total_deep, 1)},
            {"name": "浅睡", "value": round(total_shallow, 1)},
            {"name": "REM", "value": round(total_rem, 1)},
            {"name": "清醒", "value": round(total_wake, 1)},
        ],
    })


# ---------- 多日趋势 ----------

@vis_bp.route("/trend", methods=["GET"])
@login_required
def trend_data():
    """多日睡眠变化趋势"""
    user = get_current_user()
    records = _get_user_records(user.id)

    dates = []
    quality_scores = []
    total_sleep = []
    efficiency = []
    for r in records:
        dates.append(r.record_date or "")
        quality_scores.append(r.sleepQualityScore or 0)
        total_sleep.append(round((r.totalSleepMinutes or 0) / 60, 2))
        efficiency.append(round((r.sleepEfficiency or 0) * 100, 1))

    return jsonify({
        "dates": dates,
        "quality_scores": quality_scores,
        "total_sleep_hours": total_sleep,
        "efficiency_pct": efficiency,
    })


# ---------- 散点矩阵数据 ----------

@vis_bp.route("/scatter_matrix", methods=["GET"])
@login_required
def scatter_matrix_data():
    """特征散点矩阵数据"""
    user = get_current_user()
    records = _get_user_records(user.id)

    fields = ["totalSleepMinutes", "deepSleepTime", "REMTime", "sleepEfficiency",
              "daySteps", "avgHeartRate", "sleepQualityScore"]
    field_labels = {
        "totalSleepMinutes": "总睡眠时长", "deepSleepTime": "深睡时长",
        "REMTime": "REM时长", "sleepEfficiency": "睡眠效率",
        "daySteps": "步数", "avgHeartRate": "平均心率",
        "sleepQualityScore": "睡眠质量分",
    }
    points = {f: [] for f in fields}
    for r in records:
        for f in fields:
            points[f].append(getattr(r, f, 0) or 0)

    return jsonify({
        "fields": fields,
        "field_labels": field_labels,
        "points": points,
    })


# ---------- 管理员：全局可视化 ----------

@vis_bp.route("/admin/global_correlation", methods=["GET"])
@admin_required
def global_correlation():
    """管理员全局相关性热力图（聚合全体用户数据）"""
    records = SleepRecord.query.all()
    # 复用相同逻辑
    fields = [
        "sleepQualityScore", "totalSleepMinutes", "deepSleepTime",
        "shallowSleepTime", "REMTime", "wakeTime", "sleepEfficiency",
        "daySteps", "avgHeartRate",
    ]
    import math
    data_points = {f: [] for f in fields}
    for r in records:
        for f in fields:
            data_points[f].append(getattr(r, f, 0) or 0)

    matrix = {}
    for f1 in fields:
        for f2 in fields:
            x, y = data_points[f1], data_points[f2]
            n = len(x)
            if n < 2:
                matrix[f"{f1}|{f2}"] = 0
                continue
            mx, my = sum(x) / n, sum(y) / n
            sx = math.sqrt(sum((xi - mx) ** 2 for xi in x))
            sy = math.sqrt(sum((yi - my) ** 2 for yi in y))
            if sx == 0 or sy == 0:
                matrix[f"{f1}|{f2}"] = 0
                continue
            matrix[f"{f1}|{f2}"] = round(sum((x[i] - mx) * (y[i] - my) for i in range(n)) / (sx * sy), 4)

    return jsonify({
        "fields": fields,
        "correlation_matrix": matrix,
        "total_records": len(records),
    })


@vis_bp.route("/admin/global_distribution", methods=["GET"])
@admin_required
def global_distribution():
    """群体睡眠时长分布、睡眠结构占比"""
    records = SleepRecord.query.all()

    durations = [r.totalSleepMinutes for r in records if r.totalSleepMinutes]
    quality_scores = [r.sleepQualityScore for r in records if r.sleepQualityScore]
    total_deep = sum(r.deepSleepTime or 0 for r in records)
    total_shallow = sum(r.shallowSleepTime or 0 for r in records)
    total_rem = sum(r.REMTime or 0 for r in records)
    total_wake = sum(r.wakeTime or 0 for r in records)

    return jsonify({
        "sleep_durations": durations,
        "quality_scores": quality_scores,
        "stage_breakdown": [
            {"name": "深睡", "value": round(total_deep, 1)},
            {"name": "浅睡", "value": round(total_shallow, 1)},
            {"name": "REM", "value": round(total_rem, 1)},
            {"name": "清醒", "value": round(total_wake, 1)},
        ],
        "total_users": len(set(r.user_id for r in records)),
        "total_records": len(records),
    })
