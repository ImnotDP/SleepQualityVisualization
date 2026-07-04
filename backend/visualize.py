import logging, math, os, json
from flask import Blueprint, request, jsonify
from models import SleepRecord
from auth import login_required, get_current_user, admin_required

log = logging.getLogger(__name__)
vis_bp = Blueprint("visualize", __name__, url_prefix="/api/vis")

# 特征中文标签（用于模型缓存）
FEATURE_LABELS_ZH = {
    "totalSleepMinutes": "总睡眠时长(分钟)", "deepSleepTime": "深睡时长(分钟)",
    "shallowSleepTime": "浅睡时长(分钟)", "REMTime": "REM时长(分钟)",
    "wakeTime": "清醒时长(分钟)", "sleepEfficiency": "睡眠效率",
    "deepSleepRatio": "深睡比例", "REMRatio": "REM比例",
    "daySteps": "日步数", "dayCalories": "日卡路里消耗",
    "avgHeartRate": "平均心率(bpm)",
    "temperature": "环境温度(°C)", "humidity": "环境湿度(%)",
    "noise_db": "噪声分贝(dB)", "spo2": "血氧饱和度(%)",
    "movement_freq": "体动频率(次/分钟)",
}


def _get_user_records(user_id: int):
    return SleepRecord.query.filter_by(user_id=user_id).order_by(
        SleepRecord.record_date.asc()).all()



@vis_bp.route("/scatter", methods=["GET"])
@login_required
def scatter_data():
    """心率/步数/环境参数 vs 睡眠质量 散点图"""
    user = get_current_user()
    records = _get_user_records(user.id)
    hr_vs, steps_vs, temp_vs, noise_vs = [], [], [], []
    for r in records:
        if r.avgHeartRate and r.sleepQualityScore:
            hr_vs.append([round(r.avgHeartRate, 1), round(r.sleepQualityScore, 1)])
        if r.daySteps and r.sleepQualityScore:
            steps_vs.append([round(r.daySteps), round(r.sleepQualityScore, 1)])
        if r.temperature and r.sleepQualityScore:
            temp_vs.append([round(r.temperature, 1), round(r.sleepQualityScore, 1)])
        if r.noise_db and r.sleepQualityScore:
            noise_vs.append([round(r.noise_db, 1), round(r.sleepQualityScore, 1)])
    return jsonify({
        "hr_vs_quality": hr_vs, "steps_vs_quality": steps_vs,
        "temperature_vs_quality": temp_vs, "noise_vs_quality": noise_vs,
    })


@vis_bp.route("/histogram", methods=["GET"])
@login_required
def histogram_data():
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


@vis_bp.route("/correlation", methods=["GET"])
@login_required
def correlation_data():
    user = get_current_user()
    records = _get_user_records(user.id)

    fields = [
        "sleepQualityScore", "totalSleepMinutes", "deepSleepTime",
        "shallowSleepTime", "REMTime", "wakeTime", "sleepEfficiency",
        "deepSleepRatio", "REMRatio", "daySteps", "dayCalories",
        "avgHeartRate", "nightAvgHR",
        "temperature", "humidity", "noise_db", "spo2", "movement_freq",
    ]
    field_labels = {
        "sleepQualityScore": "睡眠质量分", "totalSleepMinutes": "总睡眠时长",
        "deepSleepTime": "深睡时长", "shallowSleepTime": "浅睡时长",
        "REMTime": "REM时长", "wakeTime": "清醒时长",
        "sleepEfficiency": "睡眠效率", "deepSleepRatio": "深睡比例",
        "REMRatio": "REM比例", "daySteps": "步数",
        "dayCalories": "卡路里", "avgHeartRate": "平均心率",
        "nightAvgHR": "夜间心率",
        "temperature": "温度(°C)", "humidity": "湿度(%)",
        "noise_db": "噪声(dB)", "spo2": "血氧(%)",
        "movement_freq": "体动频率",
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
    user = get_current_user()
    records = _get_user_records(user.id)

    dates, scores, sleep_hrs, efficiency, deep_hrs, rem_hrs = [], [], [], [], [], []
    temps, humids, noises, spo2s, movements = [], [], [], [], []
    for r in records:
        dates.append(r.record_date or "")
        scores.append(round(r.sleepQualityScore or 0, 1))
        sleep_hrs.append(round((r.totalSleepMinutes or 0)/60, 2))
        efficiency.append(round((r.sleepEfficiency or 0)*100, 1))
        deep_hrs.append(round((r.deepSleepTime or 0)/60, 2))
        rem_hrs.append(round((r.REMTime or 0)/60, 2))
        temps.append(round(r.temperature or 22, 1))
        humids.append(round(r.humidity or 55, 1))
        noises.append(round(r.noise_db or 35, 1))
        spo2s.append(round(r.spo2 or 97, 1))
        movements.append(round(r.movement_freq or 5, 1))

    return jsonify({
        "dates": dates, "quality_scores": scores,
        "total_sleep_hours": sleep_hrs, "efficiency_pct": efficiency,
        "deep_sleep_hours": deep_hrs, "rem_sleep_hours": rem_hrs,
        "temperature": temps, "humidity": humids,
        "noise_db": noises, "spo2": spo2s, "movement_freq": movements,
    })


@vis_bp.route("/scatter_matrix", methods=["GET"])
@login_required
def scatter_matrix_data():
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


@vis_bp.route("/admin/global_correlation", methods=["GET"])
@admin_required
def global_correlation():
    records = SleepRecord.query.all()
    fields = [
        "sleepQualityScore", "totalSleepMinutes", "deepSleepTime",
        "shallowSleepTime", "REMTime", "wakeTime", "sleepEfficiency",
        "deepSleepRatio", "REMRatio", "daySteps", "dayCalories",
        "avgHeartRate", "nightAvgHR",
        "temperature", "humidity", "noise_db", "spo2", "movement_freq",
    ]
    field_labels = {
        "sleepQualityScore": "睡眠质量分", "totalSleepMinutes": "总睡眠时长",
        "deepSleepTime": "深睡时长", "shallowSleepTime": "浅睡时长",
        "REMTime": "REM时长", "wakeTime": "清醒时长",
        "sleepEfficiency": "睡眠效率", "deepSleepRatio": "深睡比例",
        "REMRatio": "REM比例", "daySteps": "日步数",
        "dayCalories": "卡路里", "avgHeartRate": "平均心率",
        "nightAvgHR": "夜间心率",
        "temperature": "温度(°C)", "humidity": "湿度(%)",
        "noise_db": "噪声(dB)", "spo2": "血氧(%)",
        "movement_freq": "体动频率",
    }
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
        "fields": fields, "field_labels": field_labels,
        "correlation_matrix": matrix,
        "total_records": len(records),
    })


@vis_bp.route("/admin/global_distribution", methods=["GET"])
@admin_required
def global_distribution():
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


def _get_public_records():
    from models import User
    admin_user = User.query.filter_by(role="admin").first()
    if not admin_user:
        return []
    return SleepRecord.query.filter_by(user_id=admin_user.id).order_by(
        SleepRecord.record_date.asc()).all()


@vis_bp.route("/public/trend", methods=["GET"])
def public_trend():
    records = _get_public_records()
    dates, scores, sleep_hrs, efficiency, deep_hrs, rem_hrs = [], [], [], [], [], []
    for r in records:
        dates.append(r.record_date or "")
        scores.append(round(r.sleepQualityScore or 0, 1))
        sleep_hrs.append(round((r.totalSleepMinutes or 0) / 60, 2))
        efficiency.append(round((r.sleepEfficiency or 0) * 100, 1))
        deep_hrs.append(round((r.deepSleepTime or 0) / 60, 2))
        rem_hrs.append(round((r.REMTime or 0) / 60, 2))
    return jsonify({
        "dates": dates, "quality_scores": scores,
        "total_sleep_hours": sleep_hrs, "efficiency_pct": efficiency,
        "deep_sleep_hours": deep_hrs, "rem_sleep_hours": rem_hrs,
    })


@vis_bp.route("/public/stage_pie", methods=["GET"])
def public_stage_pie():
    records = _get_public_records()
    total_deep = sum(r.deepSleepTime or 0 for r in records)
    total_shallow = sum(r.shallowSleepTime or 0 for r in records)
    total_rem = sum(r.REMTime or 0 for r in records)
    total_wake = sum(r.wakeTime or 0 for r in records)
    total = total_deep + total_shallow + total_rem + total_wake or 1
    return jsonify({
        "stages": [
            {"name": "深睡", "value": round(total_deep, 1), "percent": round(total_deep / total * 100, 1)},
            {"name": "浅睡", "value": round(total_shallow, 1), "percent": round(total_shallow / total * 100, 1)},
            {"name": "REM", "value": round(total_rem, 1), "percent": round(total_rem / total * 100, 1)},
            {"name": "清醒", "value": round(total_wake, 1), "percent": round(total_wake / total * 100, 1)},
        ],
    })


@vis_bp.route("/public/correlation", methods=["GET"])
def public_correlation():
    records = _get_public_records()
    fields = [
        "sleepQualityScore", "totalSleepMinutes", "deepSleepTime",
        "shallowSleepTime", "REMTime", "wakeTime", "sleepEfficiency",
        "deepSleepRatio", "REMRatio", "daySteps", "dayCalories",
        "avgHeartRate", "nightAvgHR",
        "temperature", "humidity", "noise_db", "spo2", "movement_freq",
    ]
    field_labels = {
        "sleepQualityScore": "睡眠质量分", "totalSleepMinutes": "总睡眠时长",
        "deepSleepTime": "深睡时长", "shallowSleepTime": "浅睡时长",
        "REMTime": "REM时长", "wakeTime": "清醒时长",
        "sleepEfficiency": "睡眠效率", "deepSleepRatio": "深睡比例",
        "REMRatio": "REM比例", "daySteps": "步数",
        "dayCalories": "卡路里", "avgHeartRate": "平均心率",
        "nightAvgHR": "夜间心率",
        "temperature": "温度(°C)", "humidity": "湿度(%)",
        "noise_db": "噪声(dB)", "spo2": "血氧(%)",
        "movement_freq": "体动频率",
    }
    data_points = {f: [getattr(r, f, 0) or 0 for r in records] for f in fields}
    matrix = {}
    for f1 in fields:
        for f2 in fields:
            x, y = data_points[f1], data_points[f2]
            n = len(x)
            if n < 2:
                matrix[f"{f1}|{f2}"] = 0; continue
            mx, my = sum(x) / n, sum(y) / n
            sx = math.sqrt(sum((xi - mx) ** 2 for xi in x))
            sy = math.sqrt(sum((yi - my) ** 2 for yi in y))
            if sx == 0 or sy == 0:
                matrix[f"{f1}|{f2}"] = 0; continue
            matrix[f"{f1}|{f2}"] = round(
                sum((x[i] - mx) * (y[i] - my) for i in range(n)) / (sx * sy), 4)
    return jsonify({
        "fields": fields, "field_labels": field_labels,
        "correlation_matrix": matrix,
    })


@vis_bp.route("/public/scatter", methods=["GET"])
def public_scatter():
    records = _get_public_records()
    hr_vs, steps_vs, temp_vs, noise_vs = [], [], [], []
    for r in records:
        if r.avgHeartRate and r.sleepQualityScore:
            hr_vs.append([round(r.avgHeartRate, 1), round(r.sleepQualityScore, 1)])
        if r.daySteps and r.sleepQualityScore:
            steps_vs.append([round(r.daySteps), round(r.sleepQualityScore, 1)])
        if r.temperature and r.sleepQualityScore:
            temp_vs.append([round(r.temperature, 1), round(r.sleepQualityScore, 1)])
        if r.noise_db and r.sleepQualityScore:
            noise_vs.append([round(r.noise_db, 1), round(r.sleepQualityScore, 1)])
    return jsonify({
        "hr_vs_quality": hr_vs, "steps_vs_quality": steps_vs,
        "temperature_vs_quality": temp_vs, "noise_vs_quality": noise_vs,
    })


@vis_bp.route("/public/sleep_structure", methods=["GET"])
def public_sleep_structure():
    records = _get_public_records()
    dates = [r.record_date or "" for r in records]
    return jsonify({
        "dates": dates,
        "deep": [r.deepSleepTime or 0 for r in records],
        "shallow": [r.shallowSleepTime or 0 for r in records],
        "rem": [r.REMTime or 0 for r in records],
        "wake": [r.wakeTime or 0 for r in records],
    })


# ========== 环境参数可视化 ==========

@vis_bp.route("/environment", methods=["GET"])
@login_required
def environment_data():
    """环境参数综合数据：温度/湿度/噪声/血氧/体动日趋势 + 统计摘要"""
    user = get_current_user()
    records = _get_user_records(user.id)
    if not records:
        return jsonify({"error": "无数据"}), 404

    dates = [r.record_date or "" for r in records]
    temps = [round(r.temperature or 22, 1) for r in records]
    humids = [round(r.humidity or 55, 1) for r in records]
    noises = [round(r.noise_db or 35, 1) for r in records]
    spo2s = [round(r.spo2 or 97, 1) for r in records]
    movements = [round(r.movement_freq or 5, 1) for r in records]
    quality = [round(r.sleepQualityScore or 0, 1) for r in records]

    def stats(arr):
        if not arr: return {}
        return {
            "avg": round(sum(arr)/len(arr), 1),
            "min": min(arr), "max": max(arr),
        }

    return jsonify({
        "dates": dates,
        "temperature": temps, "temperature_stats": stats(temps),
        "humidity": humids, "humidity_stats": stats(humids),
        "noise_db": noises, "noise_stats": stats(noises),
        "spo2": spo2s, "spo2_stats": stats(spo2s),
        "movement_freq": movements, "movement_stats": stats(movements),
        "quality_scores": quality,
    })


@vis_bp.route("/environment_vs_quality", methods=["GET"])
@login_required
def environment_vs_quality():
    """环境参数 vs 睡眠质量散点数据（用于分析环境影响）"""
    user = get_current_user()
    records = _get_user_records(user.id)

    pairs = {
        "temperature": [], "humidity": [], "noise_db": [],
        "spo2": [], "movement_freq": [],
    }
    for r in records:
        sq = r.sleepQualityScore
        if not sq: continue
        for key, attr in [("temperature", "temperature"), ("humidity", "humidity"),
                           ("noise_db", "noise_db"), ("spo2", "spo2"),
                           ("movement_freq", "movement_freq")]:
            val = getattr(r, attr, None)
            if val is not None:
                pairs[key].append([round(val, 1), round(sq, 1)])

    # 计算各环境参数与睡眠质量的相关系数
    import math
    corrs = {}
    for key, data in pairs.items():
        if len(data) < 3:
            corrs[key] = 0; continue
        xs = [d[0] for d in data]; ys = [d[1] for d in data]
        n = len(xs)
        mx, my = sum(xs)/n, sum(ys)/n
        sx = math.sqrt(sum((x-mx)**2 for x in xs))
        sy = math.sqrt(sum((y-my)**2 for y in ys))
        if sx == 0 or sy == 0: corrs[key] = 0; continue
        corrs[key] = round(sum((xs[i]-mx)*(ys[i]-my) for i in range(n))/(sx*sy), 4)

    return jsonify({
        "scatter_data": pairs,
        "correlation_with_quality": corrs,
        "labels": {
            "temperature": "温度(°C)", "humidity": "湿度(%)",
            "noise_db": "噪声(dB)", "spo2": "血氧(%)",
            "movement_freq": "体动(次/分钟)",
        },
    })


# ========== 公开环境参数可视化 ==========

@vis_bp.route("/public/environment", methods=["GET"])
def public_environment_data():
    """公开版环境参数综合数据"""
    records = _get_public_records()
    if not records:
        return jsonify({"error": "无数据"}), 404

    dates = [r.record_date or "" for r in records]
    temps = [round(r.temperature or 22, 1) for r in records]
    humids = [round(r.humidity or 55, 1) for r in records]
    noises = [round(r.noise_db or 35, 1) for r in records]
    spo2s = [round(r.spo2 or 97, 1) for r in records]
    movements = [round(r.movement_freq or 5, 1) for r in records]
    quality = [round(r.sleepQualityScore or 0, 1) for r in records]

    def stats(arr):
        if not arr: return {}
        return {"avg": round(sum(arr)/len(arr), 1), "min": min(arr), "max": max(arr)}

    return jsonify({
        "dates": dates,
        "temperature": temps, "temperature_stats": stats(temps),
        "humidity": humids, "humidity_stats": stats(humids),
        "noise_db": noises, "noise_stats": stats(noises),
        "spo2": spo2s, "spo2_stats": stats(spo2s),
        "movement_freq": movements, "movement_stats": stats(movements),
        "quality_scores": quality,
    })


@vis_bp.route("/public/environment_vs_quality", methods=["GET"])
def public_environment_vs_quality():
    """公开版环境参数 vs 睡眠质量散点数据"""
    records = _get_public_records()

    pairs = {"temperature": [], "humidity": [], "noise_db": [], "spo2": [], "movement_freq": []}
    for r in records:
        sq = r.sleepQualityScore
        if not sq: continue
        for key, attr in [("temperature", "temperature"), ("humidity", "humidity"),
                           ("noise_db", "noise_db"), ("spo2", "spo2"),
                           ("movement_freq", "movement_freq")]:
            val = getattr(r, attr, None)
            if val is not None:
                pairs[key].append([round(val, 1), round(sq, 1)])

    import math
    corrs = {}
    for key, data in pairs.items():
        if len(data) < 3: corrs[key] = 0; continue
        xs = [d[0] for d in data]; ys = [d[1] for d in data]
        n = len(xs)
        mx, my = sum(xs)/n, sum(ys)/n
        sx = math.sqrt(sum((x-mx)**2 for x in xs))
        sy = math.sqrt(sum((y-my)**2 for y in ys))
        if sx == 0 or sy == 0: corrs[key] = 0; continue
        corrs[key] = round(sum((xs[i]-mx)*(ys[i]-my) for i in range(n))/(sx*sy), 4)

    return jsonify({
        "scatter_data": pairs,
        "correlation_with_quality": corrs,
        "labels": {
            "temperature": "温度(°C)", "humidity": "湿度(%)",
            "noise_db": "噪声(dB)", "spo2": "血氧(%)",
            "movement_freq": "体动(次/分钟)",
        },
    })


# ========== 公开全模型对比 ==========


def _build_model_data():
    """每次启动时实时训练模型，不缓存"""
    import numpy as np
    records = _get_public_records()
    if len(records) < 5:
        return None

    FEATURE_COLS = [
        "totalSleepMinutes", "deepSleepTime", "shallowSleepTime", "REMTime",
        "wakeTime", "sleepEfficiency", "deepSleepRatio", "REMRatio",
        "daySteps", "dayCalories", "avgHeartRate",
        "temperature", "humidity", "noise_db", "spo2", "movement_freq",
    ]

    X, y = [], []
    for r in records:
        feats = [getattr(r, f, 0) or 0 for f in FEATURE_COLS]
        X.append(feats)
        y.append(getattr(r, "sleepQualityScore", 0) or 0)
    X, y = np.array(X), np.array(y)

    from analysis_engine import train_regression_models
    reg_results = train_regression_models(X, y)
    if "error" in reg_results:
        return None

    algo_names = reg_results.get("algorithm_names", {})
    model_comparison = {}
    per_model_fi = {}
    for name, info in reg_results.items():
        if isinstance(info, dict) and "r2" in info:
            model_comparison[name] = {
                "name": algo_names.get(name, name),
                "r2": info.get("r2"),
                "mae": info.get("mae"),
                "rmse": info.get("rmse"),
            }
            # 提取每个模型的特征重要性
            if "feature_importance" in info:
                fi_list = info["feature_importance"]
                per_model_fi[name] = {
                    FEATURE_LABELS_ZH.get(FEATURE_COLS[i], FEATURE_COLS[i]): round(float(fi_list[i]), 4)
                    for i in range(min(len(FEATURE_COLS), len(fi_list)))
                }
            elif "coef" in info:
                coef_list = info["coef"]
                per_model_fi[name] = {
                    FEATURE_LABELS_ZH.get(FEATURE_COLS[i], FEATURE_COLS[i]): round(float(coef_list[i]), 4)
                    for i in range(min(len(FEATURE_COLS), len(coef_list)))
                }

    return {
        "model_comparison": model_comparison,
        "best_model": reg_results.get("best_model", ""),
        "best_model_name": algo_names.get(reg_results.get("best_model", ""), ""),
        "n_samples": int(len(X)),
        "algorithm_names": algo_names,
        "per_model_fi": per_model_fi,
    }


@vis_bp.route("/public/model_comparison", methods=["GET"])
def public_model_comparison():
    """公开版全模型算法对比：每次实时训练（不缓存）"""
    records = _get_public_records()
    if len(records) < 5:
        return jsonify({"error": "数据不足，至少需要5条记录"}), 400

    try:
        data = _build_model_data()
        if data:
            return jsonify(data)
    except Exception as e:
        log.warning("模型训练失败：%s", e)

    return jsonify({
        "error": "模型训练失败",
        "message": "请稍后重试",
    })
