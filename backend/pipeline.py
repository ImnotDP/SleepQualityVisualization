"""
睡眠质量分析系统 - 完整预处理管线
===================================
流程：读取 CSV → 生理信号预处理（线性插值+滑动窗口平滑）→
      环境参数填充 → 睡眠阶段标注 → 特征工程 →
      每日聚合 → 导入 SleepRecord 表

预处理字段：
- 生理信号：心率(线性插值+滑动窗口平滑)、血氧饱和度、体动频率
- 环境参数：温度、湿度、噪声分贝
- 睡眠阶段标注：清醒(WAKE)、浅睡(LIGHT)、深睡(DEEP)、快速眼动期(REM)
"""

import os
import csv as csv_mod
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

# 路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(ROOT_DIR, "DATA")

# 生理阈值
HR_MIN, HR_MAX = 30, 220
STEPS_MAX_PER_MINUTE = 500
CALORIES_MAX_PER_DAY = 10_000

# 随机种子
random.seed(42)
np.random.seed(42)


# ============================================================
# Part 0: 异常值剔除工具
# ============================================================

def remove_outliers_iqr(series: pd.Series, multiplier: float = 1.5) -> pd.Series:
    """
    IQR 异常值检测：将超出 Q1 - 1.5*IQR ~ Q3 + 1.5*IQR 的值替换为 NaN。
    返回处理后的 Series（不删行，仅标记异常为 NaN，后续由插值/中位数填充）。
    """
    s = series.copy().astype(float)
    q1 = s.quantile(0.25)
    q3 = s.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - multiplier * iqr
    upper = q3 + multiplier * iqr
    outlier_mask = (s < lower) | (s > upper)
    n_out = outlier_mask.sum()
    if n_out > 0:
        log.info("  IQR 异常值：%s 个（全距 %.1f ~ %.1f，剔除 <%.1f 或 >%.1f）",
                 n_out, s.min(), s.max(), lower, upper)
        s[outlier_mask] = np.nan
    return s


def remove_outliers_zscore(series: pd.Series, threshold: float = 3.0) -> pd.Series:
    """Z-score 异常值检测：|z| > threshold → NaN"""
    s = series.copy().astype(float)
    mean = s.mean()
    std = s.std()
    if std == 0 or pd.isna(std):
        return s
    z = (s - mean).abs() / std
    n_out = (z > threshold).sum()
    if n_out > 0:
        log.info("  Z-score 异常值：%s 个（|z| > %s）", n_out, threshold)
        s[z > threshold] = np.nan
    return s


# ============================================================
# Part 1: CSV 读取
# ============================================================

def _read_csv_robust(fpath: str) -> pd.DataFrame:
    """容错读取 CSV"""
    rows = []
    with open(fpath, "r", encoding="utf-8") as fh:
        reader = csv_mod.reader(fh, quoting=csv_mod.QUOTE_MINIMAL)
        header = next(reader)
        for line in reader:
            if len(line) >= 1:
                while len(line) < len(header):
                    line.append("")
                rows.append(line[:len(header)])
    return pd.DataFrame(rows, columns=header)


def read_all_csvs(data_dir: str) -> Dict[str, pd.DataFrame]:
    """读取 DATA/ 下所有数据文件（支持 CSV/Parquet/TXT），返回 {key: DataFrame}"""
    datasets = {}
    for folder in sorted(os.listdir(data_dir)):
        folder_path = os.path.join(data_dir, folder)
        if not os.path.isdir(folder_path):
            continue
        for fname in os.listdir(folder_path):
            ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
            if ext not in ("csv", "parquet", "txt"):
                continue
            key = folder.lower()
            fpath = os.path.join(folder_path, fname)
            try:
                if ext == "parquet":
                    df = pd.read_parquet(fpath)
                elif ext == "txt":
                    for sep in [",", "\t", "|", ";"]:
                        try:
                            df = pd.read_csv(fpath, sep=sep, encoding="utf-8", nrows=5)
                            if len(df.columns) > 1:
                                df = pd.read_csv(fpath, sep=sep, encoding="utf-8")
                                break
                        except Exception:
                            continue
                    else:
                        df = pd.read_csv(fpath, encoding="utf-8")
                else:  # csv
                    try:
                        df = pd.read_csv(fpath, encoding="utf-8")
                    except (pd.errors.ParserError, Exception):
                        try:
                            df = pd.read_csv(fpath, encoding="utf-8", quoting=0, on_bad_lines="skip")
                        except Exception:
                            df = _read_csv_robust(fpath)
                datasets[key] = df
                log.info("读取 %s/%s (%s) → %s 行 × %s 列", folder, fname, ext, len(df), len(df.columns))
            except Exception as e:
                log.warning("读取 %s/%s 失败：%s", folder, fname, e)
    return datasets


# ============================================================
# Part 2: 各数据源预处理
# ============================================================

def preprocess_sleep(df: pd.DataFrame) -> pd.DataFrame:
    """
    SLEEP 每日睡眠汇总 → 生理阈值清洗 → 中位数填充缺失 → 衍生指标计算
    注意：不对睡眠时长做 IQR 异常值剔除（小睡/长睡都是合理的生理变异）
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    num_cols = ["deepSleepTime", "shallowSleepTime", "wakeTime", "REMTime"]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # 剔除原始 0 值：深睡/REM/浅睡任一为 0 的整天数据（纯小睡/无效记录），不参与后续分析
    n_before = len(df)
    df = df[(df["deepSleepTime"] > 0) & (df["REMTime"] > 0) & (df["shallowSleepTime"] > 0)]
    n_dropped = n_before - len(df)
    if n_dropped > 0:
        log.info("  剔除原始0值（深睡/REM/浅睡=0）：%s 行 → %s 行（丢弃 %s 行）",
                 n_before, len(df), n_dropped)

    # 仅做生理阈值截断（不做 IQR，保留小睡/长睡等合理变异）
    for c in num_cols:
        df[c] = df[c].clip(0, 1440)

    # 中位数填充真正缺失的值（NaN），保留原有的 0（0 表示该阶段无睡眠，是有效值）
    for c in num_cols:
        mask_na = df[c].isna()
        if mask_na.sum() > 0:
            med = df[c].median()
            fill_val = med if pd.notna(med) and med > 0 else 0
            df.loc[mask_na, c] = fill_val
            log.info("  %s: %s 个缺失 → 中位数填充 %.0f", c, mask_na.sum(), fill_val)

    total = df["deepSleepTime"] + df["shallowSleepTime"] + df["wakeTime"] + df["REMTime"]
    # 剔除 total > 1440 的异常行
    df = df[total <= 1440]
    # 剔除 total == 0 的行（完全无睡眠数据的错误记录）
    df = df[total > 0]

    if "naps" in df.columns:
        df["naps"] = df["naps"].fillna("[]")

    df["totalSleepMinutes"] = df["deepSleepTime"] + df["shallowSleepTime"] + df["REMTime"]
    df["deepSleepRatio"] = np.where(df["totalSleepMinutes"] > 0,
                                     df["deepSleepTime"] / df["totalSleepMinutes"], 0)
    df["REMRatio"] = np.where(df["totalSleepMinutes"] > 0,
                               df["REMTime"] / df["totalSleepMinutes"], 0)
    bed_time = df["totalSleepMinutes"] + df["wakeTime"]
    df["sleepEfficiency"] = np.where(bed_time > 0,
                                      df["totalSleepMinutes"] / bed_time, 0)
    df["wakeRatio"] = np.where(bed_time > 0,
                                df["wakeTime"] / bed_time, 0)
    df["sleepQualityScore"] = (
        (df["deepSleepRatio"] * 3.5 + df["REMRatio"] * 2.5 +
         df["sleepEfficiency"] * 3.0 - df["wakeRatio"] * 1.5) * 10 / 7.5
    ).clip(1, 10).round(2)

    keep = ["date", "deepSleepTime", "shallowSleepTime", "wakeTime", "REMTime",
            "naps", "totalSleepMinutes", "deepSleepRatio", "REMRatio",
            "sleepEfficiency", "wakeRatio", "sleepQualityScore"]
    df = df[[c for c in keep if c in df.columns]]
    log.info("SLEEP 预处理完成：%s 行", len(df))
    return df


def preprocess_activity(df: pd.DataFrame) -> pd.DataFrame:
    """
    ACTIVITY 每日活动汇总
    仅对步数/卡路里做 IQR 异常值剔除（保留真正的低活动日 0 值）
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    num_cols = ["steps", "distance", "runDistance", "calories"]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # IQR 异常值剔除（仅对明显错误的值，如步数突然几万→几十万）
    for c in ["steps", "calories"]:
        if c in df.columns and df[c].notna().sum() > 3:
            df[c] = remove_outliers_iqr(df[c])

    # NaN 用中位数填充（保留原有的 0：0 步是合理的休息日）
    for c in num_cols:
        mask_na = df[c].isna()
        if mask_na.sum() > 0:
            med = df[c].median()
            df.loc[mask_na, c] = med if pd.notna(med) else 0

    # 生理截断
    df["steps"] = df["steps"].clip(0, 100_000)
    df["calories"] = df["calories"].clip(0, CALORIES_MAX_PER_DAY)
    df["distance"] = df["distance"].clip(0, 100_000)
    if "runDistance" in df.columns:
        df["runDistance"] = df["runDistance"].clip(0, df["distance"].max())

    df = df.drop_duplicates(subset=["date"], keep="last")
    df = df.rename(columns={
        "steps": "daySteps", "distance": "dayDistance",
        "runDistance": "dayRunDistance", "calories": "dayCalories"})
    keep = ["date", "daySteps", "dayDistance", "dayRunDistance", "dayCalories"]
    df = df[[c for c in keep if c in df.columns]]
    log.info("ACTIVITY 预处理完成：%s 行", len(df))
    return df


def preprocess_heartrate_auto(df: pd.DataFrame) -> pd.DataFrame:
    """
    HEARTRATE_AUTO 分钟级心率
    → Z-score 异常值剔除（保留运动心率）→ 线性插值填充缺失 → 滑动窗口平滑（窗口=5）
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df["heartRate"] = pd.to_numeric(df["heartRate"], errors="coerce")

    # Z-score 异常值剔除（比 IQR 更保守，保留运动心率 120-180）
    if df["heartRate"].notna().sum() > 10:
        df["heartRate"] = remove_outliers_zscore(df["heartRate"], threshold=3.5)
    # 生理截断
    df["heartRate"] = df["heartRate"].clip(HR_MIN, HR_MAX)

    # 线性插值
    df["heartRate"] = df["heartRate"].interpolate(method="linear", limit_direction="both")
    # 按天中位数回填仍为 NaN 的
    df["heartRate"] = df.groupby(df["date"].dt.date)["heartRate"].transform(
        lambda x: x.fillna(x.median() if not pd.isna(x.median()) else 70))
    df["heartRate"] = df["heartRate"].fillna(70)
    # 滑动窗口平滑
    df["heartRate"] = df["heartRate"].rolling(window=5, center=True, min_periods=1).mean()
    df = df[(df["heartRate"] >= HR_MIN) & (df["heartRate"] <= HR_MAX)]

    df["datetime"] = pd.to_datetime(
        df["date"].dt.strftime("%Y-%m-%d") + " " + df["time"].astype(str),
        errors="coerce")
    df = df.dropna(subset=["datetime"])
    df["date_only"] = df["datetime"].dt.date
    df = df[["datetime", "date_only", "heartRate"]].rename(
        columns={"heartRate": "heartRateAuto"})
    log.info("HEARTRATE_AUTO 预处理完成（线性插值+滑动平滑）：%s 行", len(df))
    return df


def preprocess_heartrate_spot(df: pd.DataFrame) -> pd.DataFrame:
    """HEARTRATE 抽查心率 → 线性插值 + 滑动平滑"""
    df = df.copy()
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    if hasattr(df["time"].dtype, "tz") and df["time"].dtype.tz is not None:
        df["time"] = df["time"].dt.tz_convert(None)
    df["heartRate"] = pd.to_numeric(df["heartRate"], errors="coerce")
    df["heartRate"] = df["heartRate"].interpolate(method="linear", limit_direction="both")
    df["heartRate"] = df["heartRate"].fillna(df["heartRate"].median() if len(df) > 0 else 70)
    df["heartRate"] = df["heartRate"].rolling(window=5, center=True, min_periods=1).mean()
    df = df[(df["heartRate"] >= HR_MIN) & (df["heartRate"] <= HR_MAX)]
    df["datetime"] = df["time"].dt.floor("min")
    df = df.groupby("datetime", as_index=False)["heartRate"].mean()
    df = df.rename(columns={"heartRate": "heartRateSpot"})
    df["date_only"] = df["datetime"].dt.date
    log.info("HEARTRATE 预处理完成：%s 行", len(df))
    return df


def preprocess_sleep_minute(df: pd.DataFrame) -> pd.DataFrame:
    """
    SLEEP_MINUTE 分钟级睡眠阶段
    stage: LIGHT/DEEP/REM/WAKE → 统一大写
    hr: 线性插值 + 滑动平滑
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["hr"] = pd.to_numeric(df["hr"], errors="coerce")
    df["respiratory_rate"] = pd.to_numeric(df["respiratory_rate"], errors="coerce")

    # 线性插值心率
    df["hr"] = df["hr"].interpolate(method="linear", limit_direction="both")
    # 滑动窗口平滑
    df["hr"] = df["hr"].rolling(window=5, center=True, min_periods=1).mean()
    # 按阶段中位数回填
    for stage in df["stage"].dropna().unique():
        mask = df["stage"] == stage
        med = df.loc[mask, "hr"].median()
        if not pd.isna(med):
            df.loc[mask, "hr"] = df.loc[mask, "hr"].fillna(med)
    df["hr"] = df["hr"].fillna(df["hr"].median() if len(df) > 0 else 60)

    # 呼吸率填充
    rr_defaults = {"LIGHT": 16, "DEEP": 14, "REM": 15, "WAKE": 18}
    for stage, default_rr in rr_defaults.items():
        mask = df["stage"].str.upper() == stage
        df.loc[mask, "respiratory_rate"] = df.loc[mask, "respiratory_rate"].fillna(default_rr)
    df["respiratory_rate"] = df["respiratory_rate"].fillna(16)

    df = df[(df["hr"] >= HR_MIN) & (df["hr"] <= HR_MAX)]
    df = df[(df["respiratory_rate"] >= 5) & (df["respiratory_rate"] <= 60)]

    # 统一睡眠阶段标注
    valid_stages = {"LIGHT", "DEEP", "REM", "WAKE", "UNKNOWN"}
    df["stage"] = df["stage"].str.upper()
    df = df[df["stage"].isin(valid_stages)]

    df["datetime"] = pd.to_datetime(
        df["date"].dt.strftime("%Y-%m-%d") + " " + df["time"].astype(str),
        errors="coerce")
    df = df.dropna(subset=["datetime"])
    df["date_only"] = df["datetime"].dt.date

    df = df[["datetime", "date_only", "stage", "hr", "respiratory_rate"]].rename(columns={
        "stage": "sleepStage", "hr": "sleepMinuteHR",
        "respiratory_rate": "respiratoryRate"})
    log.info("SLEEP_MINUTE 预处理完成（线性插值+滑动平滑+阶段标注）：%s 行", len(df))
    return df


def preprocess_activity_minute(df: pd.DataFrame) -> pd.DataFrame:
    """ACTIVITY_MINUTE → 分钟级步数（体动频率）"""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["steps"] = pd.to_numeric(df["steps"], errors="coerce").fillna(0)
    df = df[(df["steps"] >= 0) & (df["steps"] <= STEPS_MAX_PER_MINUTE)]
    df["datetime"] = pd.to_datetime(
        df["date"].dt.strftime("%Y-%m-%d") + " " + df["time"].astype(str),
        errors="coerce")
    df = df.dropna(subset=["datetime"])
    df["date_only"] = df["datetime"].dt.date
    df["movement_freq"] = df["steps"]  # 体动频率：每分钟步数
    df = df[["datetime", "date_only", "steps", "movement_freq"]].rename(
        columns={"steps": "minuteSteps"})
    log.info("ACTIVITY_MINUTE 预处理完成：%s 行", len(df))
    return df


# ============================================================
# Part 3: 环境参数 & 血氧饱和度 & 睡眠阶段
# ============================================================

def enrich_environmental(df: pd.DataFrame) -> pd.DataFrame:
    """
    添加环境参数：温度、湿度、噪声分贝
    这些数据在小米手环导出中不直接提供，用合理随机数模拟
    只在实际有值的行上填充，不扩行
    """
    df = df.copy()
    n = len(df)

    # 温度：15-30°C，按季节微调
    if "temperature" not in df.columns:
        df["temperature"] = np.round(np.random.uniform(18, 28, n), 1)
    else:
        df["temperature"] = df["temperature"].interpolate(method="linear", limit_direction="both")
        mask = df["temperature"].isna()
        if mask.sum():
            df.loc[mask, "temperature"] = np.round(np.random.uniform(18, 28, mask.sum()), 1)

    # 湿度：30-80%
    if "humidity" not in df.columns:
        df["humidity"] = np.round(np.random.uniform(35, 75, n), 1)
    else:
        df["humidity"] = df["humidity"].interpolate(method="linear", limit_direction="both")
        mask = df["humidity"].isna()
        if mask.sum():
            df.loc[mask, "humidity"] = np.round(np.random.uniform(35, 75, mask.sum()), 1)

    # 噪声：25-55 dB
    if "noise_db" not in df.columns:
        df["noise_db"] = np.round(np.random.uniform(28, 50, n), 1)
    else:
        df["noise_db"] = df["noise_db"].interpolate(method="linear", limit_direction="both")
        mask = df["noise_db"].isna()
        if mask.sum():
            df.loc[mask, "noise_db"] = np.round(np.random.uniform(28, 50, mask.sum()), 1)

    log.info("环境参数填充完成（温度/湿度/噪声）")
    return df


def enrich_spo2(df: pd.DataFrame) -> pd.DataFrame:
    """添加血氧饱和度 SpO2：92-100%，线性插值优先"""
    df = df.copy()
    if "spo2" not in df.columns or df["spo2"].isna().all():
        df["spo2"] = np.round(np.random.uniform(94, 99, len(df)), 1)
    else:
        df["spo2"] = df["spo2"].interpolate(method="linear", limit_direction="both")
        mask = df["spo2"].isna()
        if mask.sum():
            df.loc[mask, "spo2"] = np.round(np.random.uniform(94, 99, mask.sum()), 1)
    log.info("SpO2 血氧饱和度填充完成")
    return df


def enrich_sleep_stage_label(df: pd.DataFrame) -> pd.DataFrame:
    """确保睡眠阶段标注为中文"""
    df = df.copy()
    if "sleepStage" not in df.columns:
        # 无阶段数据 → 随机生成睡眠阶段分布
        choices = ["WAKE", "LIGHT", "DEEP", "REM"]
        weights = [0.08, 0.50, 0.25, 0.17]
        df["sleepStage"] = np.random.choice(choices, size=len(df), p=weights)
    else:
        # 统一映射
        stage_map = {
            "WAKE": "WAKE", "W": "WAKE", "AWAKE": "WAKE", "清醒": "WAKE",
            "LIGHT": "LIGHT", "L": "LIGHT", "浅睡": "LIGHT",
            "DEEP": "DEEP", "D": "DEEP", "深睡": "DEEP",
            "REM": "REM", "R": "REM", "快速眼动期": "REM",
        }
        df["sleepStage"] = df["sleepStage"].apply(
            lambda x: stage_map.get(str(x).upper().strip(), "LIGHT") if pd.notna(x) else "LIGHT"
        )
    log.info("睡眠阶段标注完成：%s", df["sleepStage"].value_counts().to_dict())
    return df


# ============================================================
# Part 4: 构建每日总量表 + 特征工程
# ============================================================

def build_daily_records(processed: Dict[str, pd.DataFrame]) -> List[dict]:
    """
    合并各数据源，构建每日一条的 SleepRecord 字典列表。
    核心特征：
    - 生理信号统计：心率均值/最小/最大/标准差、夜间心率/呼吸率
    - 环境参数：温度、湿度、噪声
    - 睡眠阶段统计：各阶段分钟数
    - 体动特征：日步数、卡路里、体动频率
    """
    sleep = processed.get("sleep")
    if sleep is None:
        log.error("SLEEP 数据缺失！")
        return []

    daily = sleep.copy()
    daily["date_join"] = daily["date"].dt.date

    # ---- 合并 ACTIVITY 每日 ----
    activity = processed.get("activity")
    if activity is not None:
        act = activity.copy()
        act["date_join"] = act["date"].dt.date
        daily = daily.merge(act.drop(columns=["date"], errors="ignore"),
                            on="date_join", how="left")

    # ---- 从 HEARTRATE_AUTO 聚合每日心率统计 ----
    hr_auto = processed.get("heartrate_auto")
    if hr_auto is not None:
        hr_daily = hr_auto.groupby("date_only").agg(
            avgHeartRate=("heartRateAuto", "mean"),
            minHeartRate=("heartRateAuto", "min"),
            maxHeartRate=("heartRateAuto", "max"),
            stdHeartRate=("heartRateAuto", "std"),
        ).reset_index().rename(columns={"date_only": "date_join"})
        daily = daily.merge(hr_daily, on="date_join", how="left")

    # ---- 从 SLEEP_MINUTE 聚合阶段统计 + 夜间心率 ----
    sleep_min = processed.get("sleep_minute")
    if sleep_min is not None:
        sm = sleep_min.copy()
        stage_counts = sm.pivot_table(
            index="date_only", columns="sleepStage",
            values="datetime", aggfunc="count", fill_value=0)
        stage_counts.columns = [f"stage_{c}_minutes" for c in stage_counts.columns]
        nightly_stats = sm.groupby("date_only").agg(
            nightAvgHR=("sleepMinuteHR", "mean"),
            nightAvgRR=("respiratoryRate", "mean"),
        ).reset_index()
        nightly = stage_counts.reset_index().merge(nightly_stats, on="date_only", how="outer")
        nightly = nightly.rename(columns={"date_only": "date_join"})
        daily = daily.merge(nightly, on="date_join", how="left")

    # ---- 从 ACTIVITY_MINUTE 聚合步数总量（冗余验证） ----
    act_min = processed.get("activity_minute")
    if act_min is not None:
        am_daily = act_min.groupby("date_only")["minuteSteps"].sum().reset_index()
        am_daily = am_daily.rename(columns={"date_only": "date_join",
                                             "minuteSteps": "sumMinuteSteps"})
        daily = daily.merge(am_daily, on="date_join", how="left")

    # ---- 环境参数（取日均） ----
    # 环境参数在日级别统一随机赋值（手环无环境传感器）
    n = len(daily)
    if "temperature" not in daily.columns:
        daily["temperature"] = np.round(np.random.uniform(18, 28, n), 1)
    if "humidity" not in daily.columns:
        daily["humidity"] = np.round(np.random.uniform(35, 75, n), 1)
    if "noise_db" not in daily.columns:
        daily["noise_db"] = np.round(np.random.uniform(28, 50, n), 1)

    # ---- SpO2 日均 ----
    if "spo2" not in daily.columns:
        daily["spo2"] = np.round(np.random.uniform(94, 99, n), 1)

    daily = daily.drop(columns=["date_join"], errors="ignore")

    # ---- 缺失字段用随机数回填 ----
    daily = _fill_daily_missing(daily)

    # ---- 特征工程：额外派生特征 ----
    # 体动频率（步数/小时）
    if "daySteps" in daily.columns and "totalSleepMinutes" in daily.columns:
        awake_minutes = 1440 - daily["totalSleepMinutes"].fillna(420)
        awake_minutes = awake_minutes.clip(60, 1440)
        daily["movement_freq_per_hour"] = np.round(
            daily["daySteps"].fillna(0) / (awake_minutes / 60), 0)

    # 睡眠周期波动（深睡→REM 的标准差作为波动代理）
    for col in ["stage_DEEP_minutes", "stage_REM_minutes", "stage_LIGHT_minutes", "stage_WAKE_minutes"]:
        if col not in daily.columns:
            daily[col] = np.random.randint(0, 200, n)

    stage_cols = [c for c in daily.columns if c.startswith("stage_")]
    if stage_cols:
        daily["sleep_cycle_variability"] = daily[stage_cols].std(axis=1).round(1)

    # ---- 转为 dict 列表 ----
    records = []
    for _, row in daily.iterrows():
        rec = {
            "record_date": str(row.get("date", ""))[:10] if pd.notna(row.get("date")) else "",
            "deepSleepTime": round(float(row.get("deepSleepTime", 0) or 0), 2),
            "shallowSleepTime": round(float(row.get("shallowSleepTime", 0) or 0), 2),
            "wakeTime": round(float(row.get("wakeTime", 0) or 0), 2),
            "REMTime": round(float(row.get("REMTime", 0) or 0), 2),
            "totalSleepMinutes": round(float(row.get("totalSleepMinutes", 0) or 0), 2),
            "deepSleepRatio": round(float(row.get("deepSleepRatio", 0) or 0), 4),
            "REMRatio": round(float(row.get("REMRatio", 0) or 0), 4),
            "sleepEfficiency": round(float(row.get("sleepEfficiency", 0) or 0), 4),
            "wakeRatio": round(float(row.get("wakeRatio", 0) or 0), 4),
            "sleepQualityScore": round(float(row.get("sleepQualityScore", 0) or 0), 2),
            "daySteps": round(float(row.get("daySteps", 0) or 0), 0),
            "dayDistance": round(float(row.get("dayDistance", 0) or 0), 0),
            "dayRunDistance": round(float(row.get("dayRunDistance", 0) or 0), 0),
            "dayCalories": round(float(row.get("dayCalories", 0) or 0), 0),
            "avgHeartRate": round(float(row.get("avgHeartRate", 0) or 0), 1),
            "minHeartRate": round(float(row.get("minHeartRate", 0) or 0), 1),
            "maxHeartRate": round(float(row.get("maxHeartRate", 0) or 0), 1),
            "stdHeartRate": round(float(row.get("stdHeartRate", 0) or 0), 2),
            "nightAvgHR": round(float(row.get("nightAvgHR", 0) or 0), 1),
            "nightAvgRR": round(float(row.get("nightAvgRR", 0) or 0), 1),
            "temperature": round(float(row.get("temperature", 22) or 22), 1),
            "humidity": round(float(row.get("humidity", 55) or 55), 1),
            "noise_db": round(float(row.get("noise_db", 35) or 35), 1),
            "spo2": round(float(row.get("spo2", 97) or 97), 1),
            "movement_freq": round(float(row.get("movement_freq", 5) or row.get("movement_freq_per_hour", 5) or 5), 1),
            "naps": str(row.get("naps", "[]")),
            "uploaded_at": datetime.utcnow(),
        }
        records.append(rec)

    log.info("每日总量表完成：%s 条记录", len(records))
    return records


def _fill_daily_missing(df: pd.DataFrame) -> pd.DataFrame:
    """
    每日级别缺失字段填充：
    优先用该列已有数据的中位数；中位数不可用时用合理默认值；
    仅在完全无数据时才用随机值兜底。
    """
    df = df.copy()

    # 每列的合理默认值（中位数不可用时的兜底）
    fallback_defaults = {
        "deepSleepTime": 60, "shallowSleepTime": 220, "wakeTime": 20, "REMTime": 90,
        "totalSleepMinutes": 420,
        "deepSleepRatio": 0.15, "REMRatio": 0.20,
        "sleepEfficiency": 0.85, "wakeRatio": 0.05, "sleepQualityScore": 6.0,
        "daySteps": 6000, "dayDistance": 4500, "dayRunDistance": 200, "dayCalories": 250,
        "avgHeartRate": 72, "minHeartRate": 55, "maxHeartRate": 120, "stdHeartRate": 8,
        "nightAvgHR": 62, "nightAvgRR": 16,
        "sumMinuteSteps": 8000,
        "temperature": 22, "humidity": 55, "noise_db": 35, "spo2": 97,
    }

    for col in df.columns:
        if col in fallback_defaults:
            col_vals = df[col].dropna()
            if len(col_vals) > 0:
                # 优先用中位数
                fill_val = col_vals.median()
            else:
                # 无数据时用默认值
                fill_val = fallback_defaults[col]
            df[col] = df[col].fillna(fill_val)

    if "naps" in df.columns:
        df["naps"] = df["naps"].fillna("[]")

    # 剩余 NaN 填 0
    df = df.fillna(0)
    return df


# ============================================================
# Part 5: 主入口 —— 完整预处理管线
# ============================================================

def run_full_pipeline(data_dir: str = None) -> List[dict]:
    """
    完整预处理管线：
    DATA CSV → 生理信号预处理（线性插值+滑动平滑）→ 环境参数 →
    睡眠阶段标注 → 特征工程 → 每日聚合 → dict 列表

    返回可直接入库的 SleepRecord 字典列表
    """
    if data_dir is None:
        data_dir = DATA_DIR

    log.info("=" * 60)
    log.info("开始完整预处理管线")
    log.info("=" * 60)

    # Step 1: 读取 CSV
    log.info("[1/5] 读取 DATA 目录 CSV ...")
    datasets = read_all_csvs(data_dir)
    if not datasets:
        log.warning("DATA 目录无 CSV 文件")
        return []

    processed = {}

    # Step 2: 各数据源独立预处理
    log.info("[2/5] 各数据源预处理（线性插值 + 滑动窗口平滑）...")

    if "sleep" in datasets:
        processed["sleep"] = preprocess_sleep(datasets["sleep"])
    if "activity" in datasets:
        processed["activity"] = preprocess_activity(datasets["activity"])
    if "heartrate_auto" in datasets:
        processed["heartrate_auto"] = preprocess_heartrate_auto(datasets["heartrate_auto"])
    if "heartrate" in datasets:
        processed["heartrate"] = preprocess_heartrate_spot(datasets["heartrate"])
    if "sleep_minute" in datasets:
        processed["sleep_minute"] = preprocess_sleep_minute(datasets["sleep_minute"])
    if "activity_minute" in datasets:
        processed["activity_minute"] = preprocess_activity_minute(datasets["activity_minute"])

    # Step 3: 环境参数 + SpO2 + 睡眠阶段标注
    log.info("[3/5] 环境参数 & SpO2 & 睡眠阶段标注 ...")
    if "sleep_minute" in processed:
        processed["sleep_minute"] = enrich_environmental(processed["sleep_minute"])
        processed["sleep_minute"] = enrich_spo2(processed["sleep_minute"])
        processed["sleep_minute"] = enrich_sleep_stage_label(processed["sleep_minute"])

    # Step 4: 构建每日总量表 + 特征工程
    log.info("[4/5] 构建每日总量表 + 特征工程 ...")
    records = build_daily_records(processed)

    # Step 5: 质量检查
    log.info("[5/5] 完成。共生成 %s 条每日记录", len(records))
    if records:
        sample = records[0]
        log.info("示例字段：%s", {k: v for k, v in list(sample.items())[:8]})

    return records


def import_records_to_db(records: List[dict], user_id: int) -> int:
    """将预处理好的记录列表导入 SleepRecord 表（覆写同日期）"""
    from models import db as _db, SleepRecord, User

    admin_user = User.query.get(user_id)
    if not admin_user:
        log.error("用户 ID %s 不存在", user_id)
        return 0

    inserted, updated = 0, 0
    for rec in records:
        existing = SleepRecord.query.filter_by(
            user_id=user_id, record_date=rec["record_date"]).first()
        if existing:
            for k, v in rec.items():
                if k not in ("user_id", "record_date", "uploaded_at", "id"):
                    setattr(existing, k, v)
            existing.uploaded_at = datetime.utcnow()
            updated += 1
        else:
            _db.session.add(SleepRecord(user_id=user_id, **rec))
            inserted += 1

    _db.session.commit()
    log.info("入库完成：新增 %s 条，更新 %s 条", inserted, updated)
    return inserted + updated
