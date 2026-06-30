# ============================================================
# 睡眠质量分析系统 - 预测与分析 API
# 功能：多模型预测（SVR/LR/RF）、特征重要性、睡眠评分、自动分析
# ============================================================

import os, json, logging
import numpy as np
import pandas as pd
from flask import Blueprint, request, jsonify

from models import db, SleepRecord, AnalysisReport
from auth import login_required, get_current_user, admin_required
from analysis_engine import (compute_sleep_score, generate_sleep_report,
                             train_regression_models,
                             run_auto_analysis)
from deepseek_suggestions import generate_suggestions_via_deepseek

log = logging.getLogger(__name__)
predict_bp = Blueprint("predict", __name__, url_prefix="/api/predict")

FEATURE_COLS = [
    "totalSleepMinutes", "deepSleepTime", "shallowSleepTime", "REMTime",
    "wakeTime", "sleepEfficiency", "deepSleepRatio", "REMRatio",
    "daySteps", "dayCalories", "avgHeartRate",
    "temperature", "humidity", "noise_db", "spo2", "movement_freq",
]

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


def model_comparison_for_ds(reg_results: dict) -> dict:
    """将回归结果转换为 DeepSeek API 可用的简化格式"""
    comp = {}
    algo_names = reg_results.get("algorithm_names", {})
    for name, info in reg_results.items():
        if isinstance(info, dict) and "r2" in info:
            comp[name] = {
                "name": algo_names.get(name, name),
                "r2": info.get("r2"),
                "mae": info.get("mae"),
            }
    return comp


@predict_bp.route("/score", methods=["POST"])
@login_required
def predict_score():
    """综合睡眠质量预测：全部算法对比，选最佳模型，DeepSeek 生成建议"""
    user = get_current_user()
    data = request.get_json() or {}

    records = SleepRecord.query.filter_by(user_id=user.id).all()
    if len(records) < 5:
        return jsonify({"error": "数据不足，至少需要5条历史记录"}), 400

    X, y = [], []
    for r in records:
        feats = [getattr(r, f, 0) or 0 for f in FEATURE_COLS]
        X.append(feats)
        y.append(getattr(r, "sleepQualityScore", 0) or 0)
    X, y = np.array(X), np.array(y)

    reg_results = train_regression_models(X, y)
    if "error" in reg_results:
        return jsonify({"error": reg_results["error"]}), 400

    input_params = {}
    for f in FEATURE_COLS:
        if f in data and data[f] is not None:
            input_params[f] = float(data[f])
        else:
            vals = [getattr(r, f, 0) or 0 for r in records if getattr(r, f, None)]
            input_params[f] = round(float(np.mean(vals)), 2) if vals else 0

    best_name = reg_results.get("best_model", "rf")
    best_info = reg_results.get(best_name, {})
    X_input = np.array([[input_params[f] for f in FEATURE_COLS]])

    # 用最佳模型预测
    if best_name in ("linear", "svr", "ridge", "lasso", "elastic_net", "bayesian_ridge", "knn") and best_info.get("scaler"):
        X_input_s = best_info["scaler"].transform(X_input)
        predicted = round(float(best_info["model"].predict(X_input_s)[0]), 2)
    else:
        predicted = round(float(best_info.get("model",
                             type("", (), {"predict": lambda x: [np.mean(y)]})()
                             ).predict(X_input)[0]), 2)
    predicted = max(1, min(10, predicted))

    # 获取特征重要性（优先从RF/GBRT/XGBoost的feature_importance，其次从线性模型coef）
    fi = {}
    for model_key in ["rf", "gradient_boosting", "xgboost"]:
        if model_key in reg_results and "feature_importance" in reg_results[model_key]:
            for i, f in enumerate(FEATURE_COLS):
                fi[f] = round(float(reg_results[model_key]["feature_importance"][i]), 4)
            break
    if not fi:
        for model_key in ["linear", "ridge", "lasso", "elastic_net", "bayesian_ridge"]:
            if model_key in reg_results and "coef" in reg_results[model_key]:
                for i, f in enumerate(FEATURE_COLS):
                    fi[f] = round(float(reg_results[model_key]["coef"][i]), 4)
                break

    # 基础建议 + DeepSeek 增强建议
    report_data = generate_sleep_report(input_params, reg_results)
    base_suggestions = "\n".join(report_data.get("suggestions", []))

    # 调用 DeepSeek API 生成个性化建议
    sleep_data_for_ai = {**input_params}
    deepseek_suggestions = generate_suggestions_via_deepseek(
        sleep_data=sleep_data_for_ai,
        model_comparison=model_comparison_for_ds(reg_results),
        feature_importance=fi,
        predicted_score=predicted,
    )
    # 优先使用 DeepSeek 建议，回退到规则引擎
    suggestions = deepseek_suggestions if deepseek_suggestions else base_suggestions

    # 构建全模型对比（包含所有算法和中文名）
    algo_names = reg_results.get("algorithm_names", {})
    model_comparison = {}
    for name, info in reg_results.items():
        if isinstance(info, dict) and "r2" in info:
            model_comparison[name] = {
                "name": algo_names.get(name, name),
                "r2": info.get("r2"),
                "mae": info.get("mae"),
                "rmse": info.get("rmse"),
            }

    report = AnalysisReport(
        user_id=user.id, predicted_score=predicted,
        input_params=json.dumps(input_params, ensure_ascii=False),
        shap_values=json.dumps(fi, ensure_ascii=False),
        suggestions=suggestions,
        feature_importance=json.dumps(fi, ensure_ascii=False),
    )
    db.session.add(report)
    db.session.commit()

    return jsonify({
        "predicted_score": predicted,
        "rating": report_data.get("rating", ""),
        "score_breakdown": report_data.get("breakdown", {}),
        "input_params": input_params,
        "feature_importance": fi,
        "suggestions": suggestions,
        "suggestions_source": "deepseek" if deepseek_suggestions else "rule_based",
        "model_comparison": model_comparison,
        "best_model": best_name,
        "best_model_name": algo_names.get(best_name, best_name),
        "report_id": report.id,
    })


@predict_bp.route("/feature_analysis", methods=["GET"])
@login_required
def feature_analysis():
    """特征重要性分析与全模型对比（优先读缓存）"""
    # 优先尝试从缓存加载
    from visualize import _load_model_cache, _build_model_cache
    cache = _load_model_cache()
    if cache:
        return jsonify(cache)

    # 无缓存 → 用当前用户数据训练
    user = get_current_user()
    records = SleepRecord.query.filter_by(user_id=user.id).all()
    if len(records) < 5:
        return jsonify({"error": "数据不足"}), 400

    X, y = [], []
    for r in records:
        X.append([getattr(r, f, 0) or 0 for f in FEATURE_COLS])
        y.append(getattr(r, "sleepQualityScore", 0) or 0)
    X, y = np.array(X), np.array(y)

    reg_results = train_regression_models(X, y)
    if "error" in reg_results:
        return jsonify({"error": reg_results["error"]}), 400

    fi = {}
    best_name = reg_results.get("best_model", "rf")
    best_info = reg_results.get(best_name, {})
    if "feature_importance" in best_info:
        for i, f in enumerate(FEATURE_COLS):
            fi[FEATURE_LABELS_ZH.get(f, f)] = round(
                float(best_info["feature_importance"][i]), 4)

    algo_names = reg_results.get("algorithm_names", {})
    model_comparison = {}
    for name, v in reg_results.items():
        if isinstance(v, dict) and "r2" in v:
            model_comparison[name] = {
                "name": algo_names.get(name, name),
                "r2": v.get("r2"),
                "mae": v.get("mae"),
                "rmse": v.get("rmse"),
            }

    return jsonify({
        "feature_importance": fi,
        "model_comparison": model_comparison,
        "best_model": best_name,
        "best_model_name": algo_names.get(best_name, best_name),
        "n_samples": int(len(X)),
        "algorithm_names": algo_names,
    })


@predict_bp.route("/auto_analysis", methods=["POST"])
@login_required
def auto_analysis():
    """一键自动化分析（管理员）"""
    user = get_current_user()
    if user.role != "admin":
        return jsonify({"error": "需要管理员权限"}), 403
    result = run_auto_analysis()
    return jsonify(result)


@predict_bp.route("/quick_score", methods=["POST"])
@login_required
def quick_score():
    """快速评分：基于输入特征计算1-10分，DeepSeek增强建议"""
    data = request.get_json() or {}
    features = {
        "deepSleepRatio": float(data.get("deepSleepRatio", 0.15)),
        "REMRatio": float(data.get("REMRatio", 0.2)),
        "sleepEfficiency": float(data.get("sleepEfficiency", 0.8)),
        "wakeRatio": float(data.get("wakeRatio", 0.05)),
        "avgHeartRate": float(data.get("avgHeartRate", 70)),
        "daySteps": float(data.get("daySteps", 5000)),
    }
    score = compute_sleep_score(
        features["deepSleepRatio"], features["REMRatio"],
        features["sleepEfficiency"], features["wakeRatio"])
    report = generate_sleep_report(features, {})

    # DeepSeek 增强建议
    ds_suggestions = generate_suggestions_via_deepseek(
        sleep_data=features,
        predicted_score=score,
    )
    suggestions = ds_suggestions if ds_suggestions else "\n".join(report["suggestions"])

    return jsonify({
        "score": score, "rating": report["rating"],
        "breakdown": report["breakdown"],
        "suggestions": suggestions,
        "suggestions_source": "deepseek" if ds_suggestions else "rule_based",
    })


@predict_bp.route("/reports", methods=["GET"])
@login_required
def list_reports():
    user = get_current_user()
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    query = AnalysisReport.query.filter_by(user_id=user.id).order_by(
        AnalysisReport.created_at.desc())
    total = query.count()
    reports = query.offset((page - 1) * page_size).limit(page_size).all()
    return jsonify({
        "data": [r.to_dict() for r in reports], "total": total,
        "page": page, "page_size": page_size,
    })


@predict_bp.route("/reports/<int:report_id>", methods=["GET"])
@login_required
def get_report(report_id):
    user = get_current_user()
    report = AnalysisReport.query.filter_by(id=report_id, user_id=user.id).first()
    if not report:
        return jsonify({"error": "报告不存在"}), 404
    return jsonify(report.to_dict())
