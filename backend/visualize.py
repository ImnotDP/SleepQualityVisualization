# ============================================================
# 睡眠质量分析系统 - 可视化数据 API
# 提供：直方图/饼图/热力图/趋势图/散点图/相关性矩阵
# ============================================================

import logging, math
from flask import Blueprint, request, jsonify
from models import SleepRecord
from auth import login_required, get_current_user, admin_required

log = logging.getLogger(__name__)
vis_bp = Blueprint("visualize", __name__, url_prefix="/api/vis")


def _get_user_records(user_id: int):
    return SleepRecord.query.filter_by(user_id=user_id).order_by(
        SleepRecord.record_date.asc()).all()


# ==================== 基础图表 ====================

@vis_bp.route("/scatter", methods=["GET"])
@login_required
def scatter_data():
    """心率/步数 vs 睡眠质量 散点图"""
    user = get_current_user()
    records = _get_user_records(user.id)
    hr_vs, steps_vs = [], []
    for r in records:
        if r.avgHeartRate and r.sleepQualityScore:
            hr_vs.append([round(r.avgHeartRate, 1), round(r.sleepQualityScore, 1)])
        if r.daySteps and r.sleepQualityScore:
            steps_vs.append([round(r.daySteps), round(r.sleepQualityScore, 1)])
    return jsonify({"hr_vs_quality": hr_vs, "steps_vs_quality": steps_vs})


@vis_bp.route("/histogram", methods=["GET"])
@login_required
def histogram_data():
    """睡眠时长分布直方图 + 步数分布（Matplotlib 风格数据）"""
    user = get_current_user()
    records = _get_user_records(user.id)
    steps = [r.daySteps for r in records if r.daySteps]
    sleep_dur = [r.totalSleepMinutes for r in records if r.totalSleepMinutes]

    # 预计算分箱数据
    def make_bins(data, bin_count=12):
        if not data: return [], []
        mn, mx = min(data), max(data)
        if mn == mx: mx += 1
        w = (mx - mn) / bin_count
        edges, counts = [], [0]*bin_count
        for i in range(bin_count+1):
            edges.append(round(mn + i*w, 1))
        for v in data:
            idx = min(int((v-mn)/w), bin_count-1)
            counts[idx] += 1
        return edges, counts

    steps_edges, steps_counts = make_bins(steps)
    sleep_edges, sleep_counts = make_bins(sleep_dur)

    return jsonify({
        "steps_distribution": steps,
        "sleep_duration_distribution": sleep_dur,
        "sleep_histogram": {"edges": sleep_edges, "counts": sleep_counts},
        "steps_histogram": {"edges": steps_edges, "counts": steps_counts},
    })


@vis_bp.route("/stage_pie", methods=["GET"])
@login_required
def stage_pie_data():
    """睡眠阶段占比饼图（Seaborn 风格）"""
    user = get_current_user()
    records = _get_user_records(user.id)
    total_deep = sum(r.deepSleepTime or 0 for r in records)
    total_shallow = sum(r.shallowSleepTime or 0 for r in records)
    total_rem = sum(r.REMTime or 0 for r in records)
    total_wake = sum(r.wakeTime or 0 for r in records)
    total = total_deep + total_shallow + total_rem + total_wake or 1

    return jsonify({
        "stages": [
            {"name": "深睡", "value": round(total_deep, 1),
             "percent": round(total_deep/total*100, 1)},
            {"name": "浅睡", "value": round(total_shallow, 1),
             "percent": round(total_shallow/total*100, 1)},
            {"name": "REM", "value": round(total_rem, 1),
             "percent": round(total_rem/total*100, 1)},
            {"name": "清醒", "value": round(total_wake, 1),
             "percent": round(total_wake/total*100, 1)},
        ],
    })


# ==================== 高级图表 ====================

@vis_bp.route("/correlation", methods=["GET"])
@login_required
def correlation_data():
    """环境参数与睡眠质量热力图（Heatmap）"""
    user = get_current_user()
    records = _get_user_records(user.id)

    fields = [
        "sleepQualityScore", "totalSleepMinutes", "deepSleepTime",
        "shallowSleepTime", "REMTime", "wakeTime", "sleepEfficiency",
        "deepSleepRatio", "REMRatio", "daySteps", "dayCalories",
        "avgHeartRate", "nightAvgHR",
    ]
    field_labels = {
        "sleepQualityScore": "睡眠质量分", "totalSleepMinutes": "总睡眠时长",
        "deepSleepTime": "深睡时长", "shallowSleepTime": "浅睡时长",
        "REMTime": "REM时长", "wakeTime": "清醒时长",
        "sleepEfficiency": "睡眠效率", "deepSleepRatio": "深睡比例",
        "REMRatio": "REM比例", "daySteps": "步数",
        "dayCalories": "卡路里", "avgHeartRate": "平均心率",
        "nightAvgHR": "夜间心率",
    }

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
                matrix[f"{f1}|{f2}"] = 0; continue
            mx, my = sum(x)/n, sum(y)/n
            sx = math.sqrt(sum((xi-mx)**2 for xi in x))
            sy = math.sqrt(sum((yi-my)**2 for yi in y))
            if sx == 0 or sy == 0:
                matrix[f"{f1}|{f2}"] = 0; continue
            matrix[f"{f1}|{f2}"] = round(
                sum((x[i]-mx)*(y[i]-my) for i in range(n))/(sx*sy), 4)

    return jsonify({
        "fields": fields, "field_labels": field_labels,
        "correlation_matrix": matrix,
    })


@vis_bp.route("/trend", methods=["GET"])
@login_required
def trend_data():
    """多日睡眠趋势（Plotly 动态折线图数据）"""
    user = get_current_user()
    records = _get_user_records(user.id)

    dates, scores, sleep_hrs, efficiency, deep_hrs, rem_hrs = [], [], [], [], [], []
    for r in records:
        dates.append(r.record_date or "")
        scores.append(round(r.sleepQualityScore or 0, 1))
        sleep_hrs.append(round((r.totalSleepMinutes or 0)/60, 2))
        efficiency.append(round((r.sleepEfficiency or 0)*100, 1))
        deep_hrs.append(round((r.deepSleepTime or 0)/60, 2))
        rem_hrs.append(round((r.REMTime or 0)/60, 2))

    return jsonify({
        "dates": dates, "quality_scores": scores,
        "total_sleep_hours": sleep_hrs, "efficiency_pct": efficiency,
        "deep_sleep_hours": deep_hrs, "rem_sleep_hours": rem_hrs,
    })


@vis_bp.route("/scatter_matrix", methods=["GET"])
@login_required
def scatter_matrix_data():
    """特征散点矩阵"""
    user = get_current_user()
    records = _get_user_records(user.id)
    fields = ["totalSleepMinutes", "deepSleepTime", "REMTime",
              "sleepEfficiency", "daySteps", "avgHeartRate",
              "sleepQualityScore"]
    field_labels = {
        "totalSleepMinutes": "总睡眠时长", "deepSleepTime": "深睡时长",
        "REMTime": "REM时长", "sleepEfficiency": "睡眠效率",
        "daySteps": "步数", "avgHeartRate": "平均心率",
        "sleepQualityScore": "睡眠质量分",
    }
    points = {f: [getattr(r, f, 0) or 0 for r in records] for f in fields}
    return jsonify({"fields": fields, "field_labels": field_labels, "points": points})


@vis_bp.route("/sleep_structure", methods=["GET"])
@login_required
def sleep_structure():
    """睡眠结构分析：各阶段时长随时间变化"""
    user = get_current_user()
    records = _get_user_records(user.id)
    dates = [r.record_date or "" for r in records]
    return jsonify({
        "dates": dates,
        "deep": [r.deepSleepTime or 0 for r in records],
        "shallow": [r.shallowSleepTime or 0 for r in records],
        "rem": [r.REMTime or 0 for r in records],
        "wake": [r.wakeTime or 0 for r in records],
    })


# ==================== 管理员全局可视化 ====================

@vis_bp.route("/admin/global_correlation", methods=["GET"])
@admin_required
def global_correlation():
    """群体相关性热力图"""
    records = SleepRecord.query.all()
    fields = ["sleepQualityScore", "totalSleepMinutes", "deepSleepTime",
              "shallowSleepTime", "REMTime", "wakeTime",
              "sleepEfficiency", "daySteps", "avgHeartRate"]
    data_points = {f: [getattr(r, f, 0) or 0 for r in records] for f in fields}
    matrix = {}
    for f1 in fields:
        for f2 in fields:
            x, y = data_points[f1], data_points[f2]
            n = len(x)
            if n < 2: matrix[f"{f1}|{f2}"] = 0; continue
            mx, my = sum(x)/n, sum(y)/n
            sx = math.sqrt(sum((xi-mx)**2 for xi in x))
            sy = math.sqrt(sum((yi-my)**2 for yi in y))
            if sx == 0 or sy == 0: matrix[f"{f1}|{f2}"] = 0; continue
            matrix[f"{f1}|{f2}"] = round(
                sum((x[i]-mx)*(y[i]-my) for i in range(n))/(sx*sy), 4)
    return jsonify({
        "fields": fields, "correlation_matrix": matrix,
        "total_records": len(records),
    })


@vis_bp.route("/admin/global_distribution", methods=["GET"])
@admin_required
def global_distribution():
    """群体分布统计"""
    records = SleepRecord.query.all()
    durations = [r.totalSleepMinutes for r in records if r.totalSleepMinutes]
    quality_scores = [r.sleepQualityScore for r in records if r.sleepQualityScore]
    total_deep = sum(r.deepSleepTime or 0 for r in records)
    total_shallow = sum(r.shallowSleepTime or 0 for r in records)
    total_rem = sum(r.REMTime or 0 for r in records)
    total_wake = sum(r.wakeTime or 0 for r in records)
    return jsonify({
        "sleep_durations": durations, "quality_scores": quality_scores,
        "stage_breakdown": [
            {"name": "深睡", "value": round(total_deep, 1)},
            {"name": "浅睡", "value": round(total_shallow, 1)},
            {"name": "REM", "value": round(total_rem, 1)},
            {"name": "清醒", "value": round(total_wake, 1)},
        ],
        "total_users": len(set(r.user_id for r in records)),
        "total_records": len(records),
    })
