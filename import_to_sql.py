# ============================================================
# 睡眠质量分析系统 - 手动 SQL 导入脚本（双表模式）
#
# 使用方法：
#   python import_to_sql.py
#
# 功能：
#   1. 导入 sleep_daily 每日总量表（1 张表）
#   2. 导入 sleep_fine_YYYYMMDD 每日精细表（每天 1 张表）
#   3. 可指定 --days N 只导入最近 N 天的精细表
# ============================================================

import os
import sys
import glob
import logging
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.types import Integer, Float, String, Text

# ---------- 日志 ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# ---------- 配置 ----------
from config import MYSQL_CONFIG

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "OUTPUT")
FINE_DIR = os.path.join(OUTPUT_DIR, "fine")
DAILY_PARQUET = os.path.join(OUTPUT_DIR, "sleep_daily.parquet")

DAILY_TABLE = "sleep_daily"
FINE_TABLE_PREFIX = "sleep_fine_"

DB_URL = (
    f"mysql+pymysql://{MYSQL_CONFIG['user']}:{MYSQL_CONFIG['password']}"
    f"@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}"
    f"/{MYSQL_CONFIG['database']}"
    f"?charset={MYSQL_CONFIG['charset']}"
)


def create_database_if_not_exists(engine):
    db_name = MYSQL_CONFIG["database"]
    conn_str = (
        f"mysql+pymysql://{MYSQL_CONFIG['user']}:{MYSQL_CONFIG['password']}"
        f"@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}"
        f"?charset={MYSQL_CONFIG['charset']}"
    )
    tmp_engine = create_engine(conn_str)
    with tmp_engine.connect() as conn:
        conn.execute(text("COMMIT"))
        result = conn.execute(
            text("SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA "
                 "WHERE SCHEMA_NAME = :db"), {"db": db_name})
        if not result.fetchone():
            conn.execute(text(
                f"CREATE DATABASE `{db_name}` "
                f"DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            log.info("数据库 %s 创建成功", db_name)
        else:
            log.info("数据库 %s 已存在", db_name)
    tmp_engine.dispose()


def infer_dtype_mapping(df: pd.DataFrame) -> dict:
    mapping = {}
    for col in df.columns:
        dtype = df[col].dtype
        if dtype in (np.int64, np.int32):
            mapping[col] = Integer()
        elif dtype in (np.float64, np.float32):
            mapping[col] = Float()
        elif col in ("datetime", "date", "time"):
            mapping[col] = Text()
        else:
            sample = df[col].dropna()
            if len(sample) > 0:
                max_len = df[col].astype(str).str.len().max()
                mapping[col] = Text() if max_len > 1000 else String(min(max(max_len * 2, 50), 2000))
            else:
                mapping[col] = String(255)
    return mapping


def save_table(df: pd.DataFrame, table_name: str, engine):
    log.info("  写入 %s → %s 行 × %s 列", table_name, len(df), len(df.columns))
    dtype_mapping = infer_dtype_mapping(df)
    df.to_sql(name=table_name, con=engine, if_exists="replace",
              index=False, dtype=dtype_mapping, chunksize=5000)


def import_daily_table(engine):
    """导入每日总量表（1 张表）"""
    log.info("--- 导入每日总量表 ---")
    if not os.path.exists(DAILY_PARQUET):
        log.error("❌ 找不到 %s，请先运行 preprocess.py", DAILY_PARQUET)
        return False

    df = pd.read_parquet(DAILY_PARQUET)
    # date 列转字符串
    if "date" in df.columns:
        df["date"] = df["date"].astype(str)

    save_table(df, DAILY_TABLE, engine)

    # 添加索引
    with engine.connect() as conn:
        conn.execute(text("COMMIT"))
        try:
            conn.execute(text(
                f"ALTER TABLE `{DAILY_TABLE}` "
                f"ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY FIRST"))
        except Exception:
            pass
        try:
            conn.execute(text(
                f"CREATE INDEX idx_daily_date ON `{DAILY_TABLE}` (date(255))"))
        except Exception:
            pass

    log.info("✅ 每日总量表导入完成：%s 行", len(df))
    return True


def import_fine_tables(engine, max_days: int = None):
    """导入每日精细表（一天一表）"""
    log.info("--- 导入每日精细表 ---")
    files = sorted(glob.glob(os.path.join(FINE_DIR, "sleep_fine_*.parquet")))
    if not files:
        log.error("❌ 找不到精细表文件，请先运行 preprocess.py")
        return 0

    if max_days and max_days > 0:
        files = files[-max_days:]
        log.info("  仅导入最近 %s 天", max_days)

    total_rows = 0
    for i, fpath in enumerate(files):
        fname = os.path.basename(fpath).replace(".parquet", "")
        table_name = f"{FINE_TABLE_PREFIX}{fname.split('_')[-1]}"  # sleep_fine_20231013

        df = pd.read_parquet(fpath)
        if "datetime" in df.columns:
            df["datetime"] = df["datetime"].astype(str)

        save_table(df, table_name, engine)
        total_rows += len(df)

        if (i + 1) % 50 == 0:
            log.info("  进度：%s/%s", i + 1, len(files))

    log.info("✅ 精细表导入完成：%s 张表，共 %s 行", len(files), total_rows)
    return len(files)


def main():
    log.info("=" * 60)
    log.info("睡眠质量数据 → MySQL 手动导入（双表模式）")
    log.info("=" * 60)

    # 解析参数
    max_days = None
    if "--days" in sys.argv:
        try:
            idx = sys.argv.index("--days")
            max_days = int(sys.argv[idx + 1])
        except (ValueError, IndexError):
            log.warning("--days 参数无效，将导入全部")

    # ---- 1. 连接 MySQL ----
    log.info("【步骤 1/3】连接 MySQL ...")
    log.info("   目标：%s@%s:%s/%s",
             MYSQL_CONFIG['user'], MYSQL_CONFIG['host'],
             MYSQL_CONFIG['port'], MYSQL_CONFIG['database'])
    engine = create_engine(DB_URL, pool_size=5, pool_recycle=3600)
    create_database_if_not_exists(engine)

    # ---- 2. 导入每日总量表 ----
    log.info("【步骤 2/3】导入每日总量表...")
    import_daily_table(engine)

    # ---- 3. 导入每日精细表 ----
    log.info("【步骤 3/3】导入每日精细表（一天一表）...")
    n_fine = import_fine_tables(engine, max_days=max_days)

    # ---- 汇总 ----
    log.info("=" * 60)
    log.info("✅ MySQL 导入完成！")
    log.info("   每日总量表：%s（1 张）", DAILY_TABLE)
    log.info("   每日精细表：%s_YYYYMMDD（%s 张）", FINE_TABLE_PREFIX, n_fine)
    log.info("   数据库：%s", MYSQL_CONFIG["database"])
    log.info("=" * 60)

    engine.dispose()


if __name__ == "__main__":
    main()
