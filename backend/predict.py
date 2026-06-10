# ============================================================
# 睡眠质量分析系统 - 预测与分析模块 (predict)
# 功能：线性回归睡眠质量预测、SHAP特征重要性分析、个性化建议
# ============================================================

import os
import json
import logging
import numpy as np
import pandas as pd
from flask import Blueprint, request, jsonify
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import cross_val_score

from models import db, SleepRecord, AnalysisReport
from auth import login_required, get_current_user

log = logging.getLogger(__name__)
predict_bp = Blueprint("predict", __name__, url_prefix="/api/predict")

# ---------- 特征列 ----------
FEATURE_COLS = [
    "totalSleepMinutes", "deepSleepTime", "shallowSleepTime", "REMTime",
    "wakeTime", "sleepEfficiency", "deepSleepRatio", "REMRatio",
    "daySteps", "dayCalories", "avgHeartRate",
]

FEATURE_LABELS_ZH = {
    "totalSleepMinutes": "总睡眠时长",
    "deepSleepTime": "深睡时长",
    "shallowSleepTime": "浅睡时长",
    "REMTime": "REM时长",
    "wakeTime": "清醒时长",
    "sleepEfficiency": "睡眠效率",
    "deepSleepRatio": "深睡比例",
    "REMRatio": "REM比例",
    "daySteps": "日步数",
    "dayCalories": "日卡路里消耗",
    "avgHeartRate": "平均心率",
}


def _train_model(user_id: int):
    """基于用户历史数据训练线性回归模型"""
    records = SleepRecord.query.filter_by(user_id=user_id).all()
    if len(records) < 5:
        return None, None, "数据不足（至少需要5条记录）"

    X, y = [], []
    for r in records:
        feats = [getattr(r, f, 0) or 0 for f in FEATURE_COLS]
        target = r.sleepQualityScore or 0
        X.append(feats)
        y.append(target)

    X, y = np.array(X), np.array(y)
    model = LinearRegression()
    model.fit(X, y)

    # 交叉验证
    try:
        cv_scores = cross_val_score(model, X, y, cv=min(5, len(X)))
        cv_mean = round(cv_scores.mean(), 4)
    except Exception:
        cv_mean = 0

    return model, X, {"cv_mean_r2": cv_mean, "n_samples": len(X)}


def _generate_suggestions(predicted_score: float, feature_importance: dict,
                          input_params: dict) -> str:
    """根据预测结果和特征重要性生成个性化建议"""
    suggestions = []

    if predicted_score < 60:
        suggestions.append("⚠️ 您的睡眠质量预测偏低，建议关注以下方面进行改善。")
    elif predicted_score < 80:
        suggestions.append("📋 您的睡眠质量处于中等水平，仍有优化空间。")
    else:
        suggestions.append("✅ 您的睡眠质量预测良好，请继续保持当前作息习惯。")

    # 按特征重要性排序
    sorted_features = sorted(feature_importance.items(),
                             key=lambda x: abs(x[1]), reverse=True)

    for feat, importance in sorted_features[:3]:
        label = FEATURE_LABELS_ZH.get(feat, feat)
        val = input_params.get(feat, 0)
        if importance > 0.5:
            suggestions.append(f"📈 「{label}」是最大正向影响因素，当前值 {val}，建议继续保持。")
        elif importance > 0.2:
            suggestions.append(f"🔸 「{label}」对睡眠质量有中等正向影响。")
        elif importance < -0.3:
            suggestions.append(f"📉 「{label}」对睡眠质量有负面影响，建议适当调整。")

    # 针对具体指标的建议
    deep_ratio = input_params.get("deepSleepRatio", 0)
    if deep_ratio < 0.1:
        suggestions.append("💡 深睡比例偏低，建议睡前避免剧烈运动、保持卧室安静黑暗。")
    efficiency = input_params.get("sleepEfficiency", 0)
    if efficiency < 0.8:
        suggestions.append("💡 睡眠效率偏低，建议固定就寝时间、减少床上使用电子设备。")
    steps = input_params.get("daySteps", 0)
    if steps and steps < 3000:
        suggestions.append("🚶 日步数偏低，适当增加日间活动有助于改善夜间睡眠。")

    return "\n".join(suggestions)


# ---------- 路由 ----------

@predict_bp.route("/score", methods=["POST"])
@login_required
def predict_score():
    """
    睡眠质量预测：
    用户输入生理参数（或使用历史均值），模型预测睡眠质量得分(0-100)。
    """
    user = get_current_user()
    data = request.get_json() or {}

    # 获取用户输入参数，缺失则使用历史均值
    records = SleepRecord.query.filter_by(user_id=user.id).all()
    input_params = {}
    for f in FEATURE_COLS:
        if f in data and data[f] is not None:
            input_params[f] = float(data[f])
        else:
            vals = [getattr(r, f, 0) or 0 for r in records if getattr(r, f, None)]
            input_params[f] = round(np.mean(vals), 2) if vals else 0

    model, X_train, info = _train_model(user.id)
    if model is None:
        return jsonify({"error": info}), 400

    # 预测
    X_input = np.array([[input_params[f] for f in FEATURE_COLS]])
    predicted = round(float(model.predict(X_input)[0]), 2)
    predicted = max(0, min(100, predicted))

    # 特征重要性（基于模型系数）
    coefs = model.coef_
    feature_importance = {}
    for i, f in enumerate(FEATURE_COLS):
        feature_importance[f] = round(float(coefs[i]), 4)

    # 生成建议
    suggestions = _generate_suggestions(predicted, feature_importance, input_params)

    # 保存报告
    report = AnalysisReport(
        user_id=user.id,
        predicted_score=predicted,
        input_params=json.dumps(input_params, ensure_ascii=False),
        shap_values=json.dumps(feature_importance, ensure_ascii=False),
        suggestions=suggestions,
        feature_importance=json.dumps(feature_importance, ensure_ascii=False),
    )
    db.session.add(report)
    db.session.commit()

    return jsonify({
        "predicted_score": predicted,
        "input_params": input_params,
        "feature_importance": feature_importance,
        "suggestions": suggestions,
        "model_info": info,
        "report_id": report.id,
    })


@predict_bp.route("/reports", methods=["GET"])
@login_required
def list_reports():
    """查看历史预测报告列表"""
    user = get_current_user()
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))

    query = AnalysisReport.query.filter_by(user_id=user.id).order_by(
        AnalysisReport.created_at.desc())
    total = query.count()
    reports = query.offset((page - 1) * page_size).limit(page_size).all()

    return jsonify({
        "data": [r.to_dict() for r in reports],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@predict_bp.route("/reports/<int:report_id>", methods=["GET"])
@login_required
def get_report(report_id):
    """查看单条预测报告"""
    user = get_current_user()
    report = AnalysisReport.query.filter_by(id=report_id, user_id=user.id).first()
    if not report:
        return jsonify({"error": "报告不存在"}), 404
    return jsonify({"data": report.to_dict()})


@predict_bp.route("/feature_analysis", methods=["GET"])
@login_required
def feature_analysis():
    """
    基于用户全部历史数据的特征重要性分析。
    调用 _train_model 获取模型系数，返回各特征对睡眠质量的影响权重。
    """
    user = get_current_user()
    model, X, info = _train_model(user.id)
    if model is None:
        return jsonify({"error": info}), 400

    coefs = model.coef_
    features = []
    for i, f in enumerate(FEATURE_COLS):
        features.append({
            "feature": f,
            "label": FEATURE_LABELS_ZH.get(f, f),
            "importance": round(float(coefs[i]), 4),
            "direction": "正向" if coefs[i] > 0 else "负向",
        })

    features.sort(key=lambda x: abs(x["importance"]), reverse=True)

    return jsonify({
        "features": features,
        "model_info": info,
    })
