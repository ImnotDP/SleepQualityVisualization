
import os
import sys
import csv as csv_mod
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List

import numpy as np
import pandas as pd

# ---------- 日志 ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# ---------- 路径 ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)  # backend/ 的上一级即项目根目录
DATA_DIR = os.path.join(ROOT_DIR, "DATA")
OUTPUT_DIR = os.path.join(ROOT_DIR, "OUTPUT")
FINE_DIR = os.path.join(OUTPUT_DIR, "fine")

DAILY_PARQUET = os.path.join(OUTPUT_DIR, "sleep_daily.parquet")
DAILY_PREVIEW = os.path.join(OUTPUT_DIR, "sleep_daily_preview.csv")

# ---------- 生理阈值 ----------
HR_MIN, HR_MAX = 30, 220
STEPS_MAX_PER_MINUTE = 500
CALORIES_MAX_PER_DAY = 10_000

# ---------- 随机种子 ----------
random.seed(42)
np.random.seed(42)


def _read_sleep_csv_robust(fpath: str) -> pd.DataFrame:
    rows = []
    with open(fpath, "r", encoding="utf-8") as fh:
        reader = csv_mod.reader(fh, quoting=csv_mod.QUOTE_MINIMAL)
        header = next(reader)
        for line in reader:
            if len(line) >= 7:
                while len(line) < len(header):
                    line.append("")
                rows.append(line[:len(header)])
    return pd.DataFrame(rows, columns=header)


def read_all_csvs(data_dir: str) -> Dict[str, pd.DataFrame]:
    datasets = {}
    for folder in sorted(os.listdir(data_dir)):
        folder_path = os.path.join(data_dir, folder)
        if not os.path.isdir(folder_path):
            continue
        for fname in os.listdir(folder_path):
            if not fname.endswith(".csv"):
                continue
            key = folder.lower()
            fpath = os.path.join(folder_path, fname)
            try:
                df = pd.read_csv(fpath, encoding="utf-8")
            except pd.errors.ParserError:
                df = pd.read_csv(fpath, encoding="utf-8",
                                 quoting=0, on_bad_lines="skip")
                if len(df) < 100:
                    df = _read_sleep_csv_robust(fpath)
            datasets[key] = df
            log.info("读取 %s → %s 行 × %s 列", key, len(df), len(df.columns))
    return datasets



def preprocess_sleep(df: pd.DataFrame) -> pd.DataFrame:
    """SLEEP 每日睡眠汇总"""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    num_cols = ["deepSleepTime", "shallowSleepTime", "wakeTime", "REMTime"]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in num_cols:
        df = df[(df[c] >= 0) & (df[c] <= 1440)]
    total = df["deepSleepTime"] + df["shallowSleepTime"] + df["wakeTime"] + df["REMTime"]
    df = df[total <= 1440]
    for c in num_cols:
        med = df[c].median()
        df[c] = df[c].fillna(med if not pd.isna(med) else 0)
    if "naps" in df.columns:
        df["naps"] = df["naps"].fillna("[]")

    df["totalSleepMinutes"] = df["deepSleepTime"] + df["shallowSleepTime"] + df["REMTime"]
    df["deepSleepRatio"] = np.where(df["totalSleepMinutes"] > 0,
                                     df["deepSleepTime"] / df["totalSleepMinutes"], 0)
    df["REMRatio"] = np.where(df["totalSleepMinutes"] > 0,
                               df["REMTime"] / df["totalSleepMinutes"], 0)
    df["sleepEfficiency"] = np.where(
        (df["totalSleepMinutes"] + df["wakeTime"]) > 0,
        df["totalSleepMinutes"] / (df["totalSleepMinutes"] + df["wakeTime"]), 0)
    df["wakeRatio"] = np.where(
        (df["totalSleepMinutes"] + df["wakeTime"]) > 0,
        df["wakeTime"] / (df["totalSleepMinutes"] + df["wakeTime"]), 0)
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
    """ACTIVITY 每日活动汇总"""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    num_cols = ["steps", "distance", "runDistance", "calories"]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in num_cols:
        df[c] = df[c].fillna(df[c].median() if not pd.isna(df[c].median()) else 0)
    df = df[(df["steps"] >= 0) & (df["steps"] <= 100_000)]
    df = df[(df["calories"] >= 0) & (df["calories"] <= CALORIES_MAX_PER_DAY)]
    df = df[(df["distance"] >= 0) & (df["runDistance"] >= 0)]
    df = df[df["runDistance"] <= df["distance"]]
    df = df.drop_duplicates(subset=["date"], keep="last")
    df = df.rename(columns={
        "steps": "daySteps", "distance": "dayDistance",
        "runDistance": "dayRunDistance", "calories": "dayCalories"})
    keep = ["date", "daySteps", "dayDistance", "dayRunDistance", "dayCalories"]
    df = df[[c for c in keep if c in df.columns]]
    log.info("ACTIVITY 预处理完成：%s 行", len(df))
    return df


def preprocess_activity_minute(df: pd.DataFrame) -> pd.DataFrame:
    """ACTIVITY_MINUTE → datetime + steps"""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["steps"] = pd.to_numeric(df["steps"], errors="coerce").fillna(0)
    df = df[(df["steps"] >= 0) & (df["steps"] <= STEPS_MAX_PER_MINUTE)]
    df["datetime"] = pd.to_datetime(
        df["date"].dt.strftime("%Y-%m-%d") + " " + df["time"].astype(str),
        errors="coerce")
    df = df.dropna(subset=["datetime"])
    df["date_only"] = df["datetime"].dt.date
    df = df[["datetime", "date_only", "steps"]].rename(columns={"steps": "minuteSteps"})
    log.info("ACTIVITY_MINUTE 预处理完成：%s 行", len(df))
    return df


def preprocess_activity_stage(df: pd.DataFrame) -> pd.DataFrame:
    """ACTIVITY_STAGE → 展开为分钟级"""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for c in ["distance", "calories", "steps"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df = df[(df["steps"] >= 0) & (df["calories"] >= 0) & (df["distance"] >= 0)]

    rows = []
    for _, r in df.iterrows():
        try:
            start_dt = pd.to_datetime(
                str(r["date"].date()) + " " + str(r["start"]), errors="coerce")
            stop_dt = pd.to_datetime(
                str(r["date"].date()) + " " + str(r["stop"]), errors="coerce")
            if pd.isna(start_dt) or pd.isna(stop_dt):
                continue
            total_minutes = max(1, int((stop_dt - start_dt).total_seconds() / 60))
            dist_per_min = r["distance"] / total_minutes
            cal_per_min = r["calories"] / total_minutes
            steps_per_min = r["steps"] / total_minutes
            for m in range(total_minutes):
                dt = start_dt + timedelta(minutes=m)
                rows.append({
                    "datetime": dt,
                    "stageDistance": round(dist_per_min, 2),
                    "stageCalories": round(cal_per_min, 2),
                    "stageSteps": round(steps_per_min, 2),
                })
        except Exception:
            continue

    result = pd.DataFrame(rows)
    if len(result) > 0:
        result = result.groupby("datetime", as_index=False).sum()
    result["date_only"] = result["datetime"].dt.date
    log.info("ACTIVITY_STAGE 预处理完成：%s 行", len(result))
    return result


def preprocess_heartrate(df: pd.DataFrame) -> pd.DataFrame:
    """HEARTRATE → 线性插值 + 滑动窗口平滑 → 分钟级心率"""
    df = df.copy()
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    if hasattr(df["time"].dtype, "tz") and df["time"].dtype.tz is not None:
        df["time"] = df["time"].dt.tz_convert(None)
    df["heartRate"] = pd.to_numeric(df["heartRate"], errors="coerce")
    # 线性插值填充缺失
    df["heartRate"] = df["heartRate"].interpolate(method="linear", limit_direction="both")
    df["heartRate"] = df["heartRate"].fillna(
        df["heartRate"].median() if len(df) > 0 else 70)
    # 滑动窗口平滑（窗口大小=5）
    df["heartRate"] = df["heartRate"].rolling(window=5, center=True, min_periods=1).mean()
    df = df[(df["heartRate"] >= HR_MIN) & (df["heartRate"] <= HR_MAX)]
    df["datetime"] = df["time"].dt.floor("min")
    df = df.groupby("datetime", as_index=False)["heartRate"].mean()
    df = df.rename(columns={"heartRate": "heartRateSpot"})
    df["date_only"] = df["datetime"].dt.date
    log.info("HEARTRATE 预处理完成（含滑动窗口平滑）：%s 行", len(df))
    return df


def preprocess_heartrate_auto(df: pd.DataFrame) -> pd.DataFrame:
    """HEARTRATE_AUTO → 线性插值 + 滑动窗口平滑 → 分钟级心率"""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["heartRate"] = pd.to_numeric(df["heartRate"], errors="coerce")
    df["datetime"] = pd.to_datetime(
        df["date"].dt.strftime("%Y-%m-%d") + " " + df["time"].astype(str),
        errors="coerce")
    # 线性插值填充缺失
    df["heartRate"] = df["heartRate"].interpolate(method="linear", limit_direction="both")
    df["heartRate"] = df.groupby(df["datetime"].dt.date)["heartRate"].transform(
        lambda x: x.fillna(x.median() if not pd.isna(x.median()) else 70))
    df["heartRate"] = df["heartRate"].fillna(
        df["heartRate"].median() if len(df) > 0 else 70)
    # 滑动窗口平滑（窗口大小=5）
    df["heartRate"] = df["heartRate"].rolling(window=5, center=True, min_periods=1).mean()
    df = df[(df["heartRate"] >= HR_MIN) & (df["heartRate"] <= HR_MAX)]
    df = df.dropna(subset=["datetime"])
    df["date_only"] = df["datetime"].dt.date
    df = df[["datetime", "date_only", "heartRate"]].rename(
        columns={"heartRate": "heartRateAuto"})
    log.info("HEARTRATE_AUTO 预处理完成（含滑动窗口平滑）：%s 行", len(df))
    return df


def preprocess_sleep_minute(df: pd.DataFrame) -> pd.DataFrame:
    """SLEEP_MINUTE → datetime + stage/hr/rr"""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["hr"] = pd.to_numeric(df["hr"], errors="coerce")
    df["respiratory_rate"] = pd.to_numeric(df["respiratory_rate"], errors="coerce")
    df["datetime"] = pd.to_datetime(
        df["date"].dt.strftime("%Y-%m-%d") + " " + df["time"].astype(str),
        errors="coerce")

    for stage in df["stage"].dropna().unique():
        mask = df["stage"] == stage
        med = df.loc[mask, "hr"].median()
        if not pd.isna(med):
            df.loc[mask, "hr"] = df.loc[mask, "hr"].fillna(med)
    df["hr"] = df["hr"].fillna(df["hr"].median() if len(df) > 0 else 60)

    rr_defaults = {"LIGHT": 16, "DEEP": 14, "REM": 15, "WAKE": 18}
    for stage, default_rr in rr_defaults.items():
        mask = df["stage"] == stage
        df.loc[mask, "respiratory_rate"] = df.loc[mask, "respiratory_rate"].fillna(default_rr)
    df["respiratory_rate"] = df["respiratory_rate"].fillna(16)

    df = df[(df["hr"] >= HR_MIN) & (df["hr"] <= HR_MAX)]
    df = df[(df["respiratory_rate"] >= 5) & (df["respiratory_rate"] <= 60)]
    valid_stages = {"LIGHT", "DEEP", "REM", "WAKE", "UNKNOWN"}
    df = df[df["stage"].str.upper().isin(valid_stages)]
    df["stage"] = df["stage"].str.upper()
    df = df.dropna(subset=["datetime"])
    df["date_only"] = df["datetime"].dt.date

    df = df[["datetime", "date_only", "stage", "hr", "respiratory_rate"]].rename(columns={
        "stage": "sleepStage", "hr": "sleepMinuteHR",
        "respiratory_rate": "respiratoryRate"})
    log.info("SLEEP_MINUTE 预处理完成：%s 行", len(df))
    return df



def build_daily_table(processed: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    合并 SLEEP 每日 + ACTIVITY 每日 + 分钟级数据的每日聚合，
    形成一张 daily 总量表，每行一天。
    """
    log.info("构建每日总量表...")

    sleep = processed.get("sleep")
    activity = processed.get("activity")

    if sleep is None:
        raise ValueError("SLEEP 数据是每日表的核心，缺失！")

    daily = sleep.copy()
    daily["date_join"] = daily["date"].dt.date

    # 合并 ACTIVITY 每日
    if activity is not None:
        act = activity.copy()
        act["date_join"] = act["date"].dt.date
        daily = daily.merge(act.drop(columns=["date"]), on="date_join", how="left")

    # 从 HEARTRATE_AUTO 聚合每日心率
    hr_auto = processed.get("heartrate_auto")
    if hr_auto is not None:
        hr_daily = hr_auto.groupby("date_only").agg(
            avgHeartRate=("heartRateAuto", "mean"),
            minHeartRate=("heartRateAuto", "min"),
            maxHeartRate=("heartRateAuto", "max"),
            stdHeartRate=("heartRateAuto", "std"),
        ).reset_index().rename(columns={"date_only": "date_join"})
        daily = daily.merge(hr_daily, on="date_join", how="left")

    # 从 SLEEP_MINUTE 聚合各阶段分钟数 + 夜间统计
    sleep_min = processed.get("sleep_minute")
    if sleep_min is not None:
        sm = sleep_min.copy()
        stage_counts = sm.pivot_table(
            index="date_only", columns="sleepStage",
            values="datetime", aggfunc="count", fill_value=0)
        stage_counts = stage_counts.rename(columns=lambda x: f"stage_{x}_minutes")
        nightly_stats = sm.groupby("date_only").agg(
            nightAvgHR=("sleepMinuteHR", "mean"),
            nightAvgRR=("respiratoryRate", "mean"),
        ).reset_index()
        nightly = stage_counts.reset_index().merge(nightly_stats, on="date_only", how="outer")
        nightly = nightly.rename(columns={"date_only": "date_join"})
        daily = daily.merge(nightly, on="date_join", how="left")

    # 从 ACTIVITY_MINUTE 聚合每日步数（冗余验证）
    act_min = processed.get("activity_minute")
    if act_min is not None:
        am_daily = act_min.groupby("date_only")["minuteSteps"].sum().reset_index()
        am_daily = am_daily.rename(columns={"date_only": "date_join",
                                             "minuteSteps": "sumMinuteSteps"})
        daily = daily.merge(am_daily, on="date_join", how="left")

    daily = daily.drop(columns=["date_join"], errors="ignore")

    # 随机数填充缺失字段
    daily = fill_daily_missing_with_random(daily)

    # 列排序
    first_cols = ["date"]
    other_cols = sorted([c for c in daily.columns if c not in first_cols])
    daily = daily[first_cols + other_cols]

    log.info("每日总量表完成：%s 行 × %s 列", len(daily), len(daily.columns))
    log.info("列名：%s", list(daily.columns))
    return daily


def fill_daily_missing_with_random(df: pd.DataFrame) -> pd.DataFrame:
    """每日级别字段的随机填充"""
    df = df.copy()

    random_specs = {
        "deepSleepTime": (30, 120, 1), "shallowSleepTime": (120, 350, 1),
        "wakeTime": (0, 60, 1), "REMTime": (30, 150, 1),
        "totalSleepMinutes": (200, 500, 1),
        "deepSleepRatio": (0.05, 0.35, 4), "REMRatio": (0.10, 0.35, 4),
        "sleepEfficiency": (0.70, 0.98, 4), "wakeRatio": (0.00, 0.20, 4),
        "sleepQualityScore": (3, 9.5, 2),
        "daySteps": (1000, 20000, 0), "dayDistance": (500, 20000, 0),
        "dayRunDistance": (0, 5000, 0), "dayCalories": (100, 500, 0),
        "avgHeartRate": (50, 100, 1), "minHeartRate": (40, 70, 1),
        "maxHeartRate": (80, 160, 1), "stdHeartRate": (2, 20, 2),
        "stage_LIGHT_minutes": (0, 400, 0), "stage_DEEP_minutes": (0, 200, 0),
        "stage_REM_minutes": (0, 200, 0), "stage_WAKE_minutes": (0, 100, 0),
        "nightAvgHR": (45, 90, 1), "nightAvgRR": (12, 20, 1),
        "sumMinuteSteps": (2000, 30000, 0),
    }

    for col in df.columns:
        if col in random_specs:
            low, high, decimals = random_specs[col]
            mask = df[col].isna()
            n = mask.sum()
            if n > 0:
                if decimals == 0:
                    vals = np.random.randint(int(low), int(high) + 1, size=n)
                else:
                    vals = np.round(np.random.uniform(low, high, size=n), decimals)
                df.loc[mask, col] = vals.astype(float)
                log.info("  [daily] %s: %s 缺失 → 随机填充", col, n)

    if "naps" in df.columns:
        mask = df["naps"].isna()
        if mask.sum() > 0:
            df.loc[mask, "naps"] = "[]"

    remaining = df.isna().sum().sum()
    if remaining > 0:
        df = df.fillna(0)
        log.info("  [daily] 剩余 %s NaN → 填 0", remaining)

    return df


def collect_fine_sources(processed: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    收集所有分钟级数据源（带 date_only 列），
    后续按天拆分。保留实际数据的原始粒度，不强制填满每分钟。
    """
    sources = []
    source_keys = ["activity_minute", "heartrate_auto", "sleep_minute",
                   "heartrate", "activity_stage"]
    for key in source_keys:
        if key in processed and "date_only" in processed[key].columns:
            df = processed[key].copy()
            # 统一去除时区
            if "datetime" in df.columns:
                if hasattr(df["datetime"].dtype, "tz") and df["datetime"].dtype.tz is not None:
                    df["datetime"] = df["datetime"].dt.tz_convert(None)
            sources.append(df)

    if not sources:
        raise ValueError("没有分钟级数据源")

    # 按 datetime 全外连接
    all_dts = []
    for s in sources:
        all_dts.append(s[["datetime"]].drop_duplicates())
    base = pd.concat(all_dts).drop_duplicates().sort_values("datetime").reset_index(drop=True)
    base["date_only"] = base["datetime"].dt.date
    base["time"] = base["datetime"].dt.strftime("%H:%M")

    # 合并各数据源
    merge_cols_map = {
        "activity_minute": ["minuteSteps"],
        "heartrate_auto": ["heartRateAuto"],
        "sleep_minute": ["sleepStage", "sleepMinuteHR", "respiratoryRate"],
        "heartrate": ["heartRateSpot"],
        "activity_stage": ["stageDistance", "stageCalories", "stageSteps"],
    }

    for key, cols in merge_cols_map.items():
        if key in processed:
            sub = processed[key][["datetime"] + cols].copy()
            base = base.merge(sub, on="datetime", how="left")

    # 按天分组
    groups = base.groupby("date_only")
    log.info("精细数据共 %s 行，覆盖 %s 个日期", len(base), len(groups))
    return groups


def fill_fine_missing_with_random(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    random_specs = {
        "minuteSteps": (0, 200, 0), "heartRateAuto": (50, 120, 1),
        "heartRateSpot": (50, 120, 1), "sleepMinuteHR": (45, 100, 1),
        "respiratoryRate": (12, 20, 1),
        "stageDistance": (0, 50, 2), "stageCalories": (0, 5, 2),
        "stageSteps": (0, 60, 0),
    }

    for col in df.columns:
        if col in random_specs:
            low, high, decimals = random_specs[col]
            mask = df[col].isna()
            n = mask.sum()
            if n > 0:
                if decimals == 0:
                    vals = np.random.randint(int(low), int(high) + 1, size=n)
                else:
                    vals = np.round(np.random.uniform(low, high, size=n), decimals)
                df.loc[mask, col] = vals.astype(float)

    if "sleepStage" in df.columns:
        mask = df["sleepStage"].isna()
        n = mask.sum()
        if n > 0:
            stages = ["LIGHT", "DEEP", "REM", "WAKE"]
            weights = [0.45, 0.20, 0.25, 0.10]
            df.loc[mask, "sleepStage"] = np.random.choice(stages, size=n, p=weights)

    remaining = df.isna().sum().sum()
    if remaining > 0:
        df = df.fillna(0)

    return df


def build_and_save_fine_tables(groups, fine_dir: str) -> List[str]:
    """
    按天拆分，对每一天：
      - 随机填充缺失
      - 保存为 Parquet/maybe not needed
      - 跳过空表
    返回生成的文件路径列表。
    """
    os.makedirs(fine_dir, exist_ok=True)
    saved = []
    total_rows = 0

    for date_val, group_df in groups:
        date_str = str(date_val).replace("-", "")
        group_df = group_df.copy()

        # 填充随机数
        group_df = fill_fine_missing_with_random(group_df)

        # 删除辅助列
        group_df = group_df.drop(columns=["date_only"], errors="ignore")

        # 列排序
        first_cols = ["datetime", "time"]
        other_cols = sorted([c for c in group_df.columns if c not in first_cols])
        group_df = group_df[first_cols + other_cols]

        # 保存
        fname = f"sleep_fine_{date_str}.parquet"
        fpath = os.path.join(fine_dir, fname)
        group_df.to_parquet(fpath, index=False, compression="snappy")
        saved.append(fpath)
        total_rows += len(group_df)

    log.info("精细表：%s 个日期 → %s 个文件，共 %s 行",
             len(saved), len(saved), total_rows)
    return saved



def save_preview_csv(df: pd.DataFrame, output_path: str, n_rows: int = 500):
    preview = df.head(n_rows).copy()
    for col in preview.columns:
        if pd.api.types.is_datetime64_any_dtype(preview[col]):
            preview[col] = preview[col].astype(str)
    preview.to_csv(output_path, index=False, encoding="utf-8")
    size_kb = os.path.getsize(output_path) / 1024
    log.info("预览 CSV：%s (%.1f KB, %s 行)", output_path, size_kb, len(preview))


def print_daily_statistics(df: pd.DataFrame):
    log.info("=" * 60)
    log.info("📊 每日总量表统计：")
    log.info("   行数（天）：%s", len(df))
    log.info("   列数：%s", len(df.columns))
    if "date" in df.columns:
        dates = pd.to_datetime(df["date"])
        log.info("   日期范围：%s ~ %s",
                 dates.min().strftime("%Y-%m-%d"), dates.max().strftime("%Y-%m-%d"))
    log.info("   各列非空：全部 100%%（随机数已补全）")
    log.info("=" * 60)



def main():
    log.info("=" * 60)
    log.info("睡眠质量数据预处理（双表模式）")
    log.info("=" * 60)

    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(FINE_DIR, exist_ok=True)

    # ---- 1. 读取 ----
    log.info("【步骤 1/5】读取 DATA/ 原始 CSV 数据...")
    datasets = read_all_csvs(DATA_DIR)
    if not datasets:
        log.error("未找到任何 CSV 数据文件！")
        sys.exit(1)

    # ---- 2. 预处理 ----
    log.info("【步骤 2/5】各数据源独立预处理...")
    preprocessors = {
        "sleep": preprocess_sleep, "activity": preprocess_activity,
        "activity_minute": preprocess_activity_minute,
        "activity_stage": preprocess_activity_stage,
        "heartrate": preprocess_heartrate,
        "heartrate_auto": preprocess_heartrate_auto,
        "sleep_minute": preprocess_sleep_minute,
    }
    processed = {}
    for key, func in preprocessors.items():
        if key in datasets:
            try:
                processed[key] = func(datasets[key])
            except Exception as e:
                log.error("预处理 %s 失败：%s", key, e)
                raise

    # ---- 3. 每日总量表 ----
    log.info("【步骤 3/5】构建每日总量表...")
    daily_df = build_daily_table(processed)

    # ---- 4. 每日精细表（一天一表） ----
    log.info("【步骤 4/5】构建每日精细表（一天一表）...")
    fine_groups = collect_fine_sources(processed)
    fine_files = build_and_save_fine_tables(fine_groups, FINE_DIR)

    # ---- 5. 保存 ----
    log.info("【步骤 5/5】保存输出文件...")
    daily_df.to_parquet(DAILY_PARQUET, index=False, compression="snappy")
    log.info("每日总量表：%s (%.2f MB)", DAILY_PARQUET,
             os.path.getsize(DAILY_PARQUET) / 1024 / 1024)
    save_preview_csv(daily_df, DAILY_PREVIEW, n_rows=500)

    print_daily_statistics(daily_df)

    # 精细表统计
    fine_total_size = sum(os.path.getsize(f) for f in fine_files)
    log.info("📊 精细表：%s 个日期文件，共 %.2f MB", len(fine_files),
             fine_total_size / 1024 / 1024)

    log.info("=" * 60)
    log.info("✅ 全部完成！")
    log.info("   每日总量表：%s", DAILY_PARQUET)
    log.info("   每日总量预览：%s", DAILY_PREVIEW)
    log.info("   精细表目录：%s/ （%s 个文件）", FINE_DIR, len(fine_files))
    log.info("   请运行import_to_sql.py导入 MySQL")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
