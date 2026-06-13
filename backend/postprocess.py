"""
二次处理：整合生理信号、环境参数与睡眠阶段 → 统一 CSV
- 生理信号: heart_rate(线性插值+平滑), spo2, movement_freq
- 环境参数: temperature, humidity, noise_db
- 睡眠阶段: 清醒、浅睡、深睡、快速眼动期(REM)
- 缺失值：优先线性插值，回退合理随机数填充
"""

import os, glob, logging
from typing import List

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
FINE_DIR = os.path.join(ROOT_DIR, "OUTPUT", "fine")
OUT_PATH = os.path.join(ROOT_DIR, "OUTPUT", "secondary_processed.csv")

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)
np.random.seed(42)


def load_fine_parquets(fine_dir: str) -> pd.DataFrame:
    files = sorted(glob.glob(os.path.join(fine_dir, "*.parquet")))
    if not files:
        raise FileNotFoundError(f"未找到 parquet 文件：{fine_dir}")
    parts = []
    for f in files:
        try:
            parts.append(pd.read_parquet(f))
        except Exception:
            log.warning("跳过：%s", f)
    if not parts:
        raise RuntimeError("无可用精细表数据")
    df = pd.concat(parts, ignore_index=True)
    log.info("加载 %d 文件，共 %d 行", len(parts), len(df))
    return df


def choose_heart_rate(row):
    """心率来源优先级：sleepMinuteHR > heartRateAuto > heartRateSpot"""
    for col in ("sleepMinuteHR", "heartRateAuto", "heartRateSpot"):
        if col in row and pd.notna(row[col]):
            return float(row[col])
    return np.nan


def map_stage_to_label(stage_val):
    """睡眠阶段映射为中文标签"""
    if pd.isna(stage_val) or stage_val is None:
        return np.nan
    s = str(stage_val).upper()
    if s in ("WAKE", "W", "AWAKE", "清醒"): return "清醒"
    if s in ("LIGHT", "L", "浅睡"): return "浅睡"
    if s in ("DEEP", "D", "深睡"): return "深睡"
    if s in ("REM", "R", "快速眼动期"): return "快速眼动期"
    return "浅睡"


def fill_missing_smart(df: pd.DataFrame) -> pd.DataFrame:
    """
    智能填充缺失值：优先线性插值，回退中位数，最后随机填充
    """
    df = df.copy()

    # spo2: 线性插值 → 中位数 → 随机(92-100)
    if "spo2" not in df.columns:
        df["spo2"] = np.nan
    df["spo2"] = df["spo2"].interpolate(method="linear", limit_direction="both")
    mask = df["spo2"].isna()
    if mask.sum():
        df.loc[mask, "spo2"] = np.round(np.random.uniform(92, 100, size=mask.sum()), 1)

    # movement_freq: 从 stageSteps/minuteSteps 继承 → 插值 → 随机填充
    if "movement_freq" not in df.columns:
        df["movement_freq"] = np.nan
    for src in ("stageSteps", "minuteSteps"):
        if src in df.columns:
            df.loc[df["movement_freq"].isna(), "movement_freq"] = \
                df.loc[df["movement_freq"].isna(), src]
    df["movement_freq"] = df["movement_freq"].interpolate(
        method="linear", limit_direction="both")
    mask = df["movement_freq"].isna()
    if mask.sum():
        df.loc[mask, "movement_freq"] = np.round(
            np.random.uniform(0, 20, size=mask.sum()), 1)

    # 环境参数：温度(15-30) 湿度(20-80) 噪声(25-60)
    for col, low, high in (("temperature", 15, 30), ("humidity", 20, 80),
                            ("noise_db", 25, 60)):
        if col not in df.columns:
            df[col] = np.nan
        df[col] = df[col].interpolate(method="linear", limit_direction="both")
        mask = df[col].isna()
        if mask.sum():
            df.loc[mask, col] = np.round(
                np.random.uniform(low, high, size=mask.sum()), 1)

    # heart_rate: 线性插值 → 中位数
    if "heart_rate" not in df.columns:
        df["heart_rate"] = np.nan
    df["heart_rate"] = df["heart_rate"].interpolate(
        method="linear", limit_direction="both")
    mask = df["heart_rate"].isna()
    if mask.sum():
        med = df["heart_rate"].median()
        df.loc[mask, "heart_rate"] = med if pd.notna(med) else 70

    # sleep_stage: 前向填充（同晚阶段通常连续）
    if "sleep_stage" not in df.columns:
        df["sleep_stage"] = np.nan
    df["sleep_stage"] = df["sleep_stage"].fillna(method="ffill").fillna(method="bfill")
    mask = df["sleep_stage"].isna()
    if mask.sum():
        choices = ["清醒", "浅睡", "深睡", "快速眼动期"]
        weights = [0.08, 0.5, 0.25, 0.17]
        df.loc[mask, "sleep_stage"] = np.random.choice(
            choices, size=mask.sum(), p=weights)

    # 类型转换
    for col in ("heart_rate", "spo2", "movement_freq",
                "temperature", "humidity", "noise_db"):
        if col in df.columns:
            df[col] = df[col].astype(float)

    return df


def build_secondary_table(df: pd.DataFrame) -> pd.DataFrame:
    """构建统一二次表，包含全部 7 个字段"""
    if "datetime" not in df.columns:
        raise ValueError("缺少 datetime 列")
    out = pd.DataFrame()
    out["datetime"] = pd.to_datetime(df["datetime"])

    out["heart_rate"] = df.apply(choose_heart_rate, axis=1)
    out["spo2"] = df["spo2"] if "spo2" in df.columns else np.nan
    out["movement_freq"] = (df["movement_freq"] if "movement_freq" in df.columns
                            else df.get("stageSteps", df.get("minuteSteps", np.nan)))
    for col in ("temperature", "humidity", "noise_db"):
        out[col] = df[col] if col in df.columns else np.nan
    out["sleep_stage"] = (df["sleepStage"].apply(map_stage_to_label)
                          if "sleepStage" in df.columns else np.nan)

    out = fill_missing_smart(out)
    cols = ["datetime", "heart_rate", "spo2", "movement_freq",
            "temperature", "humidity", "noise_db", "sleep_stage"]
    return out[cols]


def main():
    df = load_fine_parquets(FINE_DIR)
    sec = build_secondary_table(df)
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    sec.to_csv(OUT_PATH, index=False, encoding="utf-8")
    log.info("已保存：%s (%d 行)", OUT_PATH, len(sec))


if __name__ == "__main__":
    main()
