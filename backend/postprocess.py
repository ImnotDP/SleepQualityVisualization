"""
二次处理：整合生理信号、环境参数与睡眠阶段，输出统一 CSV

- 生理信号: heart_rate, spo2, movement_freq
- 环境参数: temperature, humidity, noise_db
- 睡眠阶段: 清醒、浅睡、深睡、快速眼动期（REM）

缺失值按合理区间填充随机数。
"""
import os
import glob
import logging
from typing import List

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)  # backend/ 的上一级即项目根目录
FINE_DIR = os.path.join(ROOT_DIR, "OUTPUT", "fine")
OUT_PATH = os.path.join(ROOT_DIR, "OUTPUT", "secondary_processed.csv")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# 固定随机种子以便可复现
np.random.seed(42)


def load_fine_parquets(fine_dir: str) -> pd.DataFrame:
    files = sorted(glob.glob(os.path.join(fine_dir, "*.parquet")))
    if not files:
        raise FileNotFoundError(f"未找到任何 parquet 文件：{fine_dir}")
    parts: List[pd.DataFrame] = []
    for f in files:
        try:
            df = pd.read_parquet(f)
            parts.append(df)
        except Exception:
            log.warning("跳过无法读取的文件：%s", f)
    if not parts:
        raise RuntimeError("没有可用的精细表数据")
    df = pd.concat(parts, ignore_index=True)
    log.info("加载 %s 个文件，共 %s 行", len(parts), len(df))
    return df


def choose_heart_rate(row):
    # 优先使用 sleepMinuteHR，再使用 heartRateAuto，再使用 heartRateSpot
    for col in ("sleepMinuteHR", "heartRateAuto", "heartRateSpot"):
        if col in row and pd_notna(row[col]):
            return float(row[col])
    return np.nan


def pd_notna(x):
    return not (pd.isna(x) or x is None)


def map_stage_to_label(stage_val):
    if not pd_notna(stage_val):
        return np.nan
    s = str(stage_val).upper()
    if s in ("WAKE", "W", "AWAKE"):
        return "清醒"
    if s in ("LIGHT", "L", "浅睡"):
        return "浅睡"
    if s in ("DEEP", "D", "深睡"):
        return "深睡"
    if s in ("REM", "R"):
        return "快速眼动期"
    return "浅睡"


def fill_missing_with_random(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # spo2: 90-100
    if "spo2" not in df.columns:
        df["spo2"] = np.nan
    mask = df["spo2"].isna()
    n = mask.sum()
    if n:
        df.loc[mask, "spo2"] = np.round(np.random.uniform(92, 100, size=n), 1)

    # movement_freq: 次/分钟（用 stageSteps / minuteSteps 或随机）
    if "movement_freq" not in df.columns:
        df["movement_freq"] = np.nan
    if "stageSteps" in df.columns:
        df.loc[df["movement_freq"].isna(), "movement_freq"] = df.loc[df["movement_freq"].isna(), "stageSteps"].fillna(np.nan)
    if "minuteSteps" in df.columns:
        df.loc[df["movement_freq"].isna(), "movement_freq"] = df.loc[df["movement_freq"].isna(), "minuteSteps"].fillna(np.nan)
    mask = df["movement_freq"].isna()
    n = mask.sum()
    if n:
        df.loc[mask, "movement_freq"] = np.round(np.random.uniform(0, 20, size=n), 1)

    # 环境参数: temperature (15-30), humidity (20-80), noise_db (30-80)
    for col, low, high, prec in (("temperature", 15, 30, 1), ("humidity", 20, 80, 1), ("noise_db", 30, 80, 1)):
        if col not in df.columns:
            df[col] = np.nan
        mask = df[col].isna()
        n = mask.sum()
        if n:
            vals = np.round(np.random.uniform(low, high, size=n), prec)
            df.loc[mask, col] = vals

    # heart_rate already prepared; fill missing with median or random
    if "heart_rate" not in df.columns:
        df["heart_rate"] = np.nan
    mask = df["heart_rate"].isna()
    n = mask.sum()
    if n:
        med = df["heart_rate"].median()
        if pd_notna(med):
            df.loc[mask, "heart_rate"] = med
        else:
            df.loc[mask, "heart_rate"] = np.round(np.random.uniform(50, 95, size=n), 1)

    # sleep_stage: map and fill missing randomly with weights
    if "sleep_stage" not in df.columns:
        df["sleep_stage"] = np.nan
    mask = df["sleep_stage"].isna()
    n = mask.sum()
    if n:
        choices = ["清醒", "浅睡", "深睡", "快速眼动期"]
        weights = [0.08, 0.5, 0.25, 0.17]
        df.loc[mask, "sleep_stage"] = np.random.choice(choices, size=n, p=weights)

    # 最后确保顺序与类型
    df["heart_rate"] = df["heart_rate"].astype(float)
    df["spo2"] = df["spo2"].astype(float)
    df["movement_freq"] = df["movement_freq"].astype(float)
    df["temperature"] = df["temperature"].astype(float)
    df["humidity"] = df["humidity"].astype(float)
    df["noise_db"] = df["noise_db"].astype(float)

    return df


def build_secondary_table(df: pd.DataFrame) -> pd.DataFrame:
    # 统一 datetime 列
    if "datetime" not in df.columns:
        raise ValueError("数据中缺少 datetime 列，无法构建二次表")
    out = pd.DataFrame()
    out["datetime"] = pd.to_datetime(df["datetime"])

    # heart_rate
    out["heart_rate"] = df.apply(lambda r: choose_heart_rate(r), axis=1)

    # spo2: 直接使用存在列或留空，后续填充
    if "spo2" in df.columns:
        out["spo2"] = df["spo2"]
    else:
        out["spo2"] = np.nan

    # movement_freq
    if "movement_freq" in df.columns:
        out["movement_freq"] = df["movement_freq"]
    elif "stageSteps" in df.columns:
        out["movement_freq"] = df["stageSteps"]
    elif "minuteSteps" in df.columns:
        out["movement_freq"] = df["minuteSteps"]
    else:
        out["movement_freq"] = np.nan

    # 环境参数若存在则拷贝
    for col in ("temperature", "humidity", "noise_db"):
        out[col] = df[col] if col in df.columns else np.nan

    # sleep_stage: 优先映射已有 sleepStage 字段
    if "sleepStage" in df.columns:
        out["sleep_stage"] = df["sleepStage"].apply(map_stage_to_label)
    else:
        out["sleep_stage"] = np.nan

    out = fill_missing_with_random(out)
    # 将 datetime 放在第一列
    cols = ["datetime", "heart_rate", "spo2", "movement_freq", "temperature", "humidity", "noise_db", "sleep_stage"]
    out = out[cols]
    return out


def main():
    df = load_fine_parquets(FINE_DIR)

    # 如果原始精细表中没有 sleepStage，但有小写或其他命名，尝试兼容
    # 另外，保留原来的 minuteSteps/stageSteps 等列作为候选

    # 构建二次表
    sec = build_secondary_table(df)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    sec.to_csv(OUT_PATH, index=False, encoding="utf-8")
    log.info("已保存二次处理文件：%s (%s 行)", OUT_PATH, len(sec))


if __name__ == "__main__":
    main()
