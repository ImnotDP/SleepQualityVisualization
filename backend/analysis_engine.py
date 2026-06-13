# ============================================================
# 睡眠质量分析引擎 - 核心模块
# 功能：预处理 → 特征工程 → 多模型训练 → 评估 → 可视化数据生成
# ============================================================

import os, logging, json
import numpy as np
import pandas as pd
from datetime import datetime
from collections import defaultdict

from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.svm import SVR
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import GridSearchCV, cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import (accuracy_score, f1_score, r2_score,
                             mean_absolute_error, mean_squared_error,
                             classification_report)

log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(ROOT_DIR, "DATA")
SEED = 42
np.random.seed(SEED)

# ============================================================
# Part 1: 数据加载与预处理
# ============================================================

def load_raw_data(data_dir: str = DATA_DIR) -> dict:
    """加载 DATA/ 下所有 CSV，返回 {key: DataFrame}"""
    datasets = {}
    for folder in sorted(os.listdir(data_dir)):
        fp = os.path.join(data_dir, folder)
        if not os.path.isdir(fp):
            continue
        for fname in os.listdir(fp):
            if not fname.endswith(".csv"):
                continue
            key = folder.lower()
            fpath = os.path.join(fp, fname)
            try:
                df = pd.read_csv(fpath, encoding="utf-8")
            except Exception:
                df = pd.read_csv(fpath, encoding="utf-8", on_bad_lines="skip")
            datasets[key] = df
    return datasets


def linear_interpolate(series: pd.Series) -> pd.Series:
    """线性插值填充缺失值"""
    return series.interpolate(method="linear", limit_direction="both")


def sliding_window_smooth(series: pd.Series, window: int = 5) -> pd.Series:
    """滑动窗口平滑（心率数据专用）"""
    return series.rolling(window=window, center=True, min_periods=1).mean()


def extract_features(daily_df: pd.DataFrame,
                     minute_dfs: dict = None) -> pd.DataFrame:
    """
    特征工程：从每日汇总 + 分钟级数据中提取统计特征与时序特征
    返回完整特征矩阵
    """
    df = daily_df.copy()

    # --- 基本派生特征 ---
    if "deepSleepTime" in df.columns and "shallowSleepTime" in df.columns \
       and "REMTime" in df.columns:
        df["totalSleepMinutes"] = (df["deepSleepTime"].fillna(0) +
                                    df["shallowSleepTime"].fillna(0) +
                                    df["REMTime"].fillna(0))
    if "totalSleepMinutes" in df.columns and "wakeTime" in df.columns:
        bed = df["totalSleepMinutes"].fillna(0) + df["wakeTime"].fillna(0)
        df["sleepEfficiency"] = np.where(bed > 0,
                                         df["totalSleepMinutes"].fillna(0) / bed, 0)
    if "totalSleepMinutes" in df.columns:
        df["deepSleepRatio"] = np.where(df["totalSleepMinutes"] > 0,
                                        df.get("deepSleepTime", pd.Series(0)).fillna(0)
                                        / df["totalSleepMinutes"], 0)
        df["REMRatio"] = np.where(df["totalSleepMinutes"] > 0,
                                  df.get("REMTime", pd.Series(0)).fillna(0)
                                  / df["totalSleepMinutes"], 0)

    # --- 心率统计特征 ---
    for col in ["avgHeartRate", "nightAvgHR", "heart_rate"]:
        if col in df.columns:
            df[col] = linear_interpolate(df[col].astype(float))
            # 添加心率变异性代理
            if col == "avgHeartRate":
                df["hr_rolling_mean"] = sliding_window_smooth(df[col], 3)
                df["hr_trend"] = df[col].diff().fillna(0)

    # --- 体动特征 ---
    if "daySteps" in df.columns:
        df["daySteps"] = df["daySteps"].fillna(df["daySteps"].median()
                                                if len(df) > 0 else 0)
    if "movement_freq" in df.columns:
        df["movement_freq"] = linear_interpolate(df["movement_freq"].astype(float))

    # --- 环境参数 ---
    for col in ["temperature", "humidity", "noise_db"]:
        if col in df.columns:
            df[col] = linear_interpolate(df[col].astype(float))

    # --- 睡眠阶段特征 ---
    stage_cols = [c for c in df.columns if c.startswith("stage_")]
    for sc in stage_cols:
        df[sc] = df[sc].fillna(0)

    # --- 觉醒次数估算 ---
    if "wakeTime" in df.columns and "stage_WAKE_minutes" in df.columns:
        df["awakenings_est"] = np.where(df["stage_WAKE_minutes"] > 0,
                                        np.ceil(df["stage_WAKE_minutes"] / 5), 0)
    elif "wakeTime" in df.columns:
        df["awakenings_est"] = np.where(df["wakeTime"] > 0,
                                        np.ceil(df["wakeTime"] / 10), 0)

    # --- 周期性特征 ---
    if "record_date" in df.columns or "date" in df.columns:
        date_col = "record_date" if "record_date" in df.columns else "date"
        try:
            dates = pd.to_datetime(df[date_col])
            df["day_of_week"] = dates.dt.dayofweek
            df["is_weekend"] = (dates.dt.dayofweek >= 5).astype(int)
        except Exception:
            pass

    return df


# ============================================================
# Part 2: 睡眠质量评分模型
# ============================================================

def compute_sleep_score(deep_ratio: float, rem_ratio: float,
                        efficiency: float, wake_ratio: float) -> float:
    """计算睡眠质量评分（1-10分制）"""
    score = (deep_ratio * 3.5 + rem_ratio * 2.5 +
             efficiency * 3.0 - wake_ratio * 1.5) * 10 / 7.5
    return round(max(1, min(10, score)), 1)


def train_regression_models(X: np.ndarray, y: np.ndarray) -> dict:
    """
    训练回归模型预测睡眠质量评分（1-10分）
    模型：SVR, LinearRegression, RandomForestRegressor
    """
    if len(X) < 10:
        return {"error": "数据不足，至少需要10条记录"}

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=SEED)

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    results = {}

    # --- SVR with GridSearch ---
    svr_params = {"kernel": ["rbf", "linear"],
                  "C": [0.1, 1, 10],
                  "gamma": ["scale", "auto"]}
    svr_gs = GridSearchCV(SVR(), svr_params, cv=min(5, len(X_train)),
                          scoring="r2", n_jobs=-1)
    svr_gs.fit(X_train_s, y_train)
    svr_pred = svr_gs.best_estimator_.predict(X_test_s)
    results["svr"] = {
        "model": svr_gs.best_estimator_,
        "scaler": scaler,
        "best_params": svr_gs.best_params_,
        "r2": round(r2_score(y_test, svr_pred), 4),
        "mae": round(mean_absolute_error(y_test, svr_pred), 4),
        "rmse": round(np.sqrt(mean_squared_error(y_test, svr_pred)), 4),
    }

    # --- Linear Regression ---
    lr = LinearRegression()
    lr.fit(X_train_s, y_train)
    lr_pred = lr.predict(X_test_s)
    results["linear"] = {
        "model": lr,
        "scaler": scaler,
        "r2": round(r2_score(y_test, lr_pred), 4),
        "mae": round(mean_absolute_error(y_test, lr_pred), 4),
        "rmse": round(np.sqrt(mean_squared_error(y_test, lr_pred)), 4),
        "coef": lr.coef_.tolist(),
    }

    # --- RandomForest Regressor ---
    rf = RandomForestRegressor(n_estimators=100, random_state=SEED)
    rf.fit(X_train, y_train)
    rf_pred = rf.predict(X_test)
    results["rf"] = {
        "model": rf,
        "r2": round(r2_score(y_test, rf_pred), 4),
        "mae": round(mean_absolute_error(y_test, rf_pred), 4),
        "rmse": round(np.sqrt(mean_squared_error(y_test, rf_pred)), 4),
        "feature_importance": rf.feature_importances_.tolist(),
    }

    # 选出最佳模型
    best = max(results.keys(), key=lambda k: results[k].get("r2", -999))
    results["best_model"] = best
    results["test_size"] = len(X_test)
    return results


# ============================================================
# Part 3: 睡眠阶段分类模型
# ============================================================

def train_classification_models(X: np.ndarray, y: np.ndarray,
                                class_names: list = None) -> dict:
    """
    训练分类模型预测睡眠阶段
    模型：RandomForest, LogisticRegression, KNN
    """
    if len(X) < 30 or len(np.unique(y)) < 2:
        return {"error": "分类数据不足"}

    le = LabelEncoder()
    y_enc = le.fit_transform(y)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_enc, test_size=0.2, random_state=SEED, stratify=y_enc)

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    results = {}

    # --- Random Forest with GridSearch ---
    rf_params = {"n_estimators": [50, 100, 200],
                 "max_depth": [5, 10, 15, None],
                 "min_samples_split": [2, 5]}
    rf_gs = GridSearchCV(RandomForestClassifier(random_state=SEED),
                         rf_params, cv=min(5, len(X_train)),
                         scoring="f1_weighted", n_jobs=-1)
    rf_gs.fit(X_train_s, y_train)
    rf_pred = rf_gs.best_estimator_.predict(X_test_s)
    results["random_forest"] = {
        "model": rf_gs.best_estimator_,
        "scaler": scaler,
        "encoder": le,
        "best_params": rf_gs.best_params_,
        "accuracy": round(accuracy_score(y_test, rf_pred), 4),
        "f1_weighted": round(f1_score(y_test, rf_pred, average="weighted"), 4),
        "feature_importance": rf_gs.best_estimator_.feature_importances_.tolist(),
    }

    # --- Logistic Regression ---
    lr = LogisticRegression(max_iter=2000, random_state=SEED)
    lr.fit(X_train_s, y_train)
    lr_pred = lr.predict(X_test_s)
    results["logistic_regression"] = {
        "model": lr,
        "scaler": scaler,
        "encoder": le,
        "accuracy": round(accuracy_score(y_test, lr_pred), 4),
        "f1_weighted": round(f1_score(y_test, lr_pred, average="weighted"), 4),
    }

    # --- KNN ---
    knn_params = {"n_neighbors": [3, 5, 7, 9]}
    knn_gs = GridSearchCV(KNeighborsClassifier(), knn_params,
                          cv=min(5, len(X_train)), scoring="f1_weighted")
    knn_gs.fit(X_train_s, y_train)
    knn_pred = knn_gs.best_estimator_.predict(X_test_s)
    results["knn"] = {
        "model": knn_gs.best_estimator_,
        "scaler": scaler,
        "encoder": le,
        "best_params": knn_gs.best_params_,
        "accuracy": round(accuracy_score(y_test, knn_pred), 4),
        "f1_weighted": round(f1_score(y_test, knn_pred, average="weighted"), 4),
    }

    # 选出最佳模型
    best = max(results.keys(),
               key=lambda k: results[k].get("f1_weighted", -999))
    results["best_model"] = best
    results["class_names"] = le.classes_.tolist()
    results["test_size"] = len(X_test)
    return results


# ============================================================
# Part 4: 综合评分与建议
# ============================================================

def generate_sleep_report(features: dict, model_results: dict) -> dict:
    """
    根据特征和模型结果生成综合睡眠报告
    包含评分、分析、改善建议
    """
    # 计算综合评分 (1-10)
    deep_ratio = features.get("deepSleepRatio", 0.15)
    rem_ratio = features.get("REMRatio", 0.2)
    efficiency = features.get("sleepEfficiency", 0.8)
    wake_ratio = features.get("wakeRatio", 0.05)

    score = compute_sleep_score(deep_ratio, rem_ratio, efficiency, wake_ratio)

    # 生成评级
    if score >= 8:
        rating, rating_color = "优秀", "green"
    elif score >= 6:
        rating, rating_color = "良好", "blue"
    elif score >= 4:
        rating, rating_color = "一般", "orange"
    else:
        rating, rating_color = "较差", "red"

    # 生成建议
    suggestions = []
    if deep_ratio < 0.1:
        suggestions.append("深睡比例偏低，建议保持规律作息、睡前避免咖啡因。")
    if efficiency < 0.75:
        suggestions.append("睡眠效率偏低，建议固定就寝时间，减少卧床清醒时间。")
    if wake_ratio > 0.15:
        suggestions.append("夜间清醒时间较长，建议改善睡眠环境（遮光、降噪）。")
    if rem_ratio < 0.15:
        suggestions.append("REM睡眠偏少，可能与压力或睡眠不足有关。")
    if features.get("avgHeartRate", 70) > 85:
        suggestions.append("夜间平均心率偏高，建议进行适度有氧运动改善心肺功能。")
    if features.get("daySteps", 0) < 3000:
        suggestions.append("日间活动量偏低，适当增加运动有助于改善睡眠。")

    if not suggestions:
        suggestions.append("您当前的睡眠指标整体良好，请继续保持。")

    return {
        "score": score,
        "rating": rating,
        "rating_color": rating_color,
        "suggestions": suggestions,
        "breakdown": {
            "deep_sleep_quality": round(min(10, deep_ratio * 25), 1),
            "rem_quality": round(min(10, rem_ratio * 20), 1),
            "efficiency_quality": round(min(10, efficiency * 12), 1),
            "continuity_quality": round(max(1, 10 - wake_ratio * 50), 1),
        },
    }


# ============================================================
# Part 5: 可视化数据生成
# ============================================================

def generate_visualization_data(daily_df: pd.DataFrame) -> dict:
    """
    生成前端可视化所需的全部数据
    - 直方图数据 (Matplotlib 风格)
    - 饼图数据 (Seaborn 风格)
    - 热力图数据
    - 趋势折线图数据 (Plotly 交互式)
    """
    df = daily_df.copy()

    # --- 1. 睡眠时长分布直方图 ---
    sleep_dur = df["totalSleepMinutes"].dropna().tolist() if "totalSleepMinutes" in df.columns else []

    # --- 2. 睡眠阶段占比饼图 ---
    stage_data = []
    for col, name in [("deepSleepTime", "深睡"), ("shallowSleepTime", "浅睡"),
                       ("REMTime", "REM"), ("wakeTime", "清醒")]:
        if col in df.columns:
            total = df[col].dropna().sum()
            stage_data.append({"name": name, "value": round(total, 1)})

    # --- 3. 环境参数与睡眠质量热力图 ---
    heatmap_cols = []
    for c in ["totalSleepMinutes", "deepSleepRatio", "REMRatio",
              "sleepEfficiency", "avgHeartRate", "daySteps",
              "temperature", "humidity", "noise_db", "sleepQualityScore"]:
        if c in df.columns and df[c].notna().sum() > 1:
            heatmap_cols.append(c)

    corr_matrix = {}
    if len(heatmap_cols) >= 2:
        corr_df = df[heatmap_cols].corr()
        for c1 in heatmap_cols:
            for c2 in heatmap_cols:
                corr_matrix[f"{c1}|{c2}"] = round(
                    corr_df.loc[c1, c2] if not pd.isna(corr_df.loc[c1, c2]) else 0, 4)

    # --- 4. 多日趋势（Plotly 风格） ---
    date_col = "record_date" if "record_date" in df.columns else (
        "date" if "date" in df.columns else None)
    trend_data = {"dates": [], "scores": [], "sleep_hours": [],
                  "efficiency": [], "deep_hours": [], "rem_hours": []}
    if date_col:
        df_sorted = df.sort_values(date_col)
        trend_data["dates"] = df_sorted[date_col].astype(str).tolist()
        trend_data["scores"] = [round(v, 1) for v in
                                df_sorted.get("sleepQualityScore", pd.Series([0]*len(df))).fillna(0).tolist()]
        trend_data["sleep_hours"] = [round(v/60, 2) for v in
                                     df_sorted.get("totalSleepMinutes", pd.Series([0]*len(df))).fillna(0).tolist()]
        trend_data["efficiency"] = [round(v*100, 1) for v in
                                    df_sorted.get("sleepEfficiency", pd.Series([0]*len(df))).fillna(0).tolist()]
        trend_data["deep_hours"] = [round(v/60, 2) for v in
                                    df_sorted.get("deepSleepTime", pd.Series([0]*len(df))).fillna(0).tolist()]
        trend_data["rem_hours"] = [round(v/60, 2) for v in
                                   df_sorted.get("REMTime", pd.Series([0]*len(df))).fillna(0).tolist()]

    # --- 5. 散点图数据 ---
    scatter = {}
    if "avgHeartRate" in df.columns and "sleepQualityScore" in df.columns:
        scatter["hr_vs_quality"] = [
            [round(r["avgHeartRate"], 1), round(r["sleepQualityScore"], 1)]
            for _, r in df.iterrows()
            if pd.notna(r.get("avgHeartRate")) and pd.notna(r.get("sleepQualityScore"))
        ]
    if "daySteps" in df.columns and "sleepQualityScore" in df.columns:
        scatter["steps_vs_quality"] = [
            [round(r["daySteps"]), round(r["sleepQualityScore"], 1)]
            for _, r in df.iterrows()
            if pd.notna(r.get("daySteps")) and pd.notna(r.get("sleepQualityScore"))
        ]

    return {
        "histogram": {"sleep_duration": sleep_dur},
        "stage_pie": {"stages": stage_data},
        "heatmap": {"fields": heatmap_cols, "matrix": corr_matrix},
        "trend": trend_data,
        "scatter": scatter,
    }


# ============================================================
# Part 6: 自动化分析管线
# ============================================================

def run_auto_analysis(data_dir: str = DATA_DIR) -> dict:
    """
    一键自动化分析：
    加载数据 → 预处理 → 特征工程 → 训练模型 → 生成报告 → 可视化数据
    """
    log.info("=== 自动化分析引擎启动 ===")
    raw = load_raw_data(data_dir)
    if not raw:
        return {"error": "DATA 目录下未找到任何 CSV 文件"}

    # 构建每日数据
    daily = _build_daily_from_raw(raw)
    if daily is None or len(daily) == 0:
        return {"error": "无法构建每日汇总数据"}

    # 特征工程
    daily = extract_features(daily)

    # 计算睡眠质量评分
    daily["sleepQualityScore"] = daily.apply(
        lambda r: compute_sleep_score(
            r.get("deepSleepRatio", 0.15), r.get("REMRatio", 0.2),
            r.get("sleepEfficiency", 0.8), r.get("wakeRatio", 0.05)), axis=1)

    # --- 回归模型：预测睡眠质量评分 ---
    reg_features = [c for c in ["totalSleepMinutes", "deepSleepTime",
                     "shallowSleepTime", "REMTime", "wakeTime",
                     "deepSleepRatio", "REMRatio", "sleepEfficiency",
                     "daySteps", "dayCalories", "avgHeartRate",
                     "temperature", "humidity", "noise_db",
                     "awakenings_est", "day_of_week", "is_weekend"]
                    if c in daily.columns and daily[c].notna().sum() > 5]
    reg_X = daily[reg_features].fillna(0).values
    reg_y = daily["sleepQualityScore"].fillna(5).values
    reg_results = train_regression_models(reg_X, reg_y)

    # --- 分类模型：预测睡眠阶段 ---
    cls_features = [c for c in ["avgHeartRate", "deepSleepTime",
                     "sleepEfficiency", "daySteps", "dayCalories",
                     "temperature", "humidity", "noise_db"]
                    if c in daily.columns]
    # 生成阶段标签（基于深睡比例）
    daily["stage_label"] = daily["deepSleepRatio"].apply(
        lambda x: "深睡主导" if x > 0.2 else ("浅睡主导" if x > 0.1 else "睡眠不足"))
    cls_X = daily[cls_features].fillna(0).values
    cls_y = daily["stage_label"].values
    cls_results = train_classification_models(cls_X, cls_y)

    # --- 生成可视化数据 ---
    vis_data = generate_visualization_data(daily)

    # --- 综合报告 ---
    avg_features = {c: daily[c].mean() for c in reg_features
                    if c in daily.columns}
    avg_features.update({
        "deepSleepRatio": daily["deepSleepRatio"].mean() if "deepSleepRatio" in daily.columns else 0.15,
        "REMRatio": daily["REMRatio"].mean() if "REMRatio" in daily.columns else 0.2,
        "sleepEfficiency": daily["sleepEfficiency"].mean() if "sleepEfficiency" in daily.columns else 0.8,
        "wakeRatio": daily["wakeRatio"].mean() if "wakeRatio" in daily.columns else 0.05,
    })
    report = generate_sleep_report(avg_features, reg_results)

    log.info("=== 自动化分析完成：%d 条数据, 最佳回归模型=%s, 最佳分类模型=%s ===",
             len(daily), reg_results.get("best_model", "N/A"),
             cls_results.get("best_model", "N/A"))

    return {
        "data_summary": {
            "total_records": int(len(daily)),
            "date_range": [str(daily.iloc[0].get("record_date", "")),
                           str(daily.iloc[-1].get("record_date", ""))],
            "avg_score": round(float(daily["sleepQualityScore"].mean()), 2),
        },
        "regression": {k: {kk: vv for kk, vv in v.items()
                           if kk != "model" and kk != "scaler"}
                       for k, v in reg_results.items() if isinstance(v, dict)},
        "classification": {k: {kk: vv for kk, vv in v.items()
                               if kk not in ("model", "scaler", "encoder")}
                           for k, v in cls_results.items() if isinstance(v, dict)},
        "report": report,
        "visualization": vis_data,
        "feature_columns": reg_features,
    }


def _build_daily_from_raw(raw: dict) -> pd.DataFrame:
    """从原始数据构建每日汇总 DataFrame"""
    # 以 SLEEP 表为基础
    sleep = raw.get("sleep")
    if sleep is None:
        return None
    df = sleep.copy()
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.rename(columns={"date": "record_date"})

    for col in ["deepSleepTime", "shallowSleepTime", "wakeTime", "REMTime"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # 合并 ACTIVITY 每日
    act = raw.get("activity")
    if act is not None and "date" in act.columns:
        act["date"] = pd.to_datetime(act["date"], errors="coerce")
        for col in ["steps", "distance", "calories"]:
            if col in act.columns:
                act[col] = pd.to_numeric(act[col], errors="coerce").fillna(0)
        act = act.rename(columns={"steps": "daySteps", "distance": "dayDistance",
                                   "calories": "dayCalories"})
        on_col = "record_date" if "record_date" in df.columns else "date"
        act_on = "date"
        if on_col in df.columns:
            df = df.merge(act[[act_on, "daySteps", "dayDistance", "dayCalories"]],
                          left_on=on_col, right_on=act_on, how="left")
            if act_on != on_col:
                df = df.drop(columns=[act_on], errors="ignore")

    # 合并 HEARTRATE_AUTO 聚合
    hr_auto = raw.get("heartrate_auto")
    if hr_auto is not None:
        if "date" in hr_auto.columns:
            hr_auto["date"] = pd.to_datetime(hr_auto["date"], errors="coerce")
        if "heartRate" in hr_auto.columns:
            hr_auto["heartRate"] = pd.to_numeric(hr_auto["heartRate"], errors="coerce")
            hr_daily = hr_auto.groupby(hr_auto["date"].dt.date).agg(
                avgHeartRate=("heartRate", "mean")).reset_index()
            hr_daily["date"] = pd.to_datetime(hr_daily["date"])
            on_c = "record_date" if "record_date" in df.columns else "date"
            if on_c in df.columns:
                df[on_c] = pd.to_datetime(df[on_c]).dt.date
                hr_daily["date"] = hr_daily["date"].dt.date
                df = df.merge(hr_daily, left_on=on_c, right_on="date", how="left")
                df = df.drop(columns=["date_y"], errors="ignore").rename(
                    columns={"date_x": on_c} if "date_x" in df.columns else {},
                    errors="ignore")

    # 填充环境参数（模拟数据）
    for col, low, high in [("temperature", 18, 28), ("humidity", 30, 70),
                            ("noise_db", 25, 60)]:
        if col not in df.columns:
            df[col] = np.random.uniform(low, high, len(df)).round(1)

    return df


# ============================================================
# 独立运行入口
# ============================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")
    result = run_auto_analysis()
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ("visualization",)},
                     indent=2, ensure_ascii=False, default=str))
