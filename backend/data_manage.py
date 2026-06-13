import os
import sys
import json
import logging
import uuid
from datetime import datetime

import pandas as pd
import numpy as np
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

from models import db, SleepRecord
from auth import login_required, get_current_user, admin_required

log = logging.getLogger(__name__)
data_bp = Blueprint("data_manage", __name__, url_prefix="/api/data")

# 将 preprocess.py 的核心函数引入
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)


def _allowed_file(filename: str, allowed: set) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


def _load_config():
    cfg = {}
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.txt")
    with open(config_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip()
    return cfg


_cfg = _load_config()
UPLOAD_FOLDER = _cfg.get("UPLOAD_FOLDER", "uploads")
MAX_SIZE_MB = int(_cfg.get("MAX_UPLOAD_SIZE_MB", "200"))
ALLOWED_EXT = set(_cfg.get("ALLOWED_EXTENSIONS", "csv").split(","))

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ---------- 快速预处理函数（内联 preprocess 核心逻辑） ----------

def _quick_preprocess_csv(filepath: str, user_id: int) -> list:
    """
    读取上传的 CSV，解析列并返回 SleepRecord 字典列表。
    兼容多种 CSV 格式（小米手环 Zepp 导出 / 自定义格式）。
    """
    try:
        df = pd.read_csv(filepath, encoding="utf-8")
    except Exception:
        df = pd.read_csv(filepath, encoding="utf-8", on_bad_lines="skip")

    records = []
    # 尝试自动识别日期列
    date_col = None
    for c in df.columns:
        if c.lower() in ("date", "record_date", "日期"):
            date_col = c
            break

    if date_col is None:
        # 如果没有日期列，尝试用当前日期
        date_col = "__date__"
        df[date_col] = datetime.now().strftime("%Y-%m-%d")

    df[date_col] = pd.to_datetime(df[date_col], errors="coerce").dt.strftime("%Y-%m-%d")

    # 映射常见列名
    col_map = {
        "deepSleepTime": ["deepSleepTime", "deep_sleep_time", "deepSleep", "深睡时长"],
        "shallowSleepTime": ["shallowSleepTime", "shallow_sleep_time", "shallowSleep", "浅睡时长"],
        "wakeTime": ["wakeTime", "wake_time", "wake", "清醒时长"],
        "REMTime": ["REMTime", "rem_time", "REM", "REM时长"],
        "totalSleepMinutes": ["totalSleepMinutes", "total_sleep", "总睡眠时长"],
        "daySteps": ["daySteps", "steps", "day_steps", "步数"],
        "dayCalories": ["dayCalories", "calories", "day_calories", "卡路里"],
        "avgHeartRate": ["avgHeartRate", "avg_heart_rate", "heartRate", "平均心率"],
        "sleepQualityScore": ["sleepQualityScore", "sleep_quality_score", "sleepQuality", "睡眠质量分"],
    }

    for _, row in df.iterrows():
        rec = {
            "user_id": user_id,
            "record_date": str(row.get(date_col, "")),
            "uploaded_at": datetime.utcnow(),
        }
        for target, sources in col_map.items():
            val = 0.0
            for s in sources:
                if s in df.columns:
                    v = row.get(s)
                    try:
                        val = float(v) if pd.notna(v) else 0.0
                        break
                    except (ValueError, TypeError):
                        continue
            rec[target] = round(val, 2)

        # 计算衍生指标
        deep = rec.get("deepSleepTime", 0) or 0
        shallow = rec.get("shallowSleepTime", 0) or 0
        rem = rec.get("REMTime", 0) or 0
        wake = rec.get("wakeTime", 0) or 0
        total = deep + shallow + rem
        rec["totalSleepMinutes"] = rec.get("totalSleepMinutes") or round(total, 2)
        rec["deepSleepRatio"] = round(deep / total, 4) if total > 0 else 0
        rec["REMRatio"] = round(rem / total, 4) if total > 0 else 0
        rec["sleepEfficiency"] = round(total / (total + wake), 4) if (total + wake) > 0 else 0
        rec["wakeRatio"] = round(wake / (total + wake), 4) if (total + wake) > 0 else 0
        rec["sleepQualityScore"] = rec.get("sleepQualityScore") or round(
            (rec["deepSleepRatio"] * 3.5 + rec["REMRatio"] * 2.5 +
             rec["sleepEfficiency"] * 3.0 - rec["wakeRatio"] * 1.5) * 10 / 7.5, 2
        )
        rec["sleepQualityScore"] = max(1, min(10, rec["sleepQualityScore"]))
        rec["naps"] = "[]"

        records.append(rec)

    return records


# ---------- 路由 ----------

@data_bp.route("/upload", methods=["POST"])
@login_required
def upload_csv():
    """上传个人睡眠 CSV 数据"""
    user = get_current_user()
    if "file" not in request.files:
        return jsonify({"error": "未选择文件"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "文件名为空"}), 400

    if not _allowed_file(file.filename, ALLOWED_EXT):
        return jsonify({"error": f"仅支持 {ALLOWED_EXT} 格式"}), 400

    filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    try:
        records = _quick_preprocess_csv(filepath, user.id)
        if not records:
            return jsonify({"error": "文件中未解析到有效数据"}), 400

        inserted = 0
        for rec in records:
            # 检查是否已存在同日期记录，存在则更新
            existing = SleepRecord.query.filter_by(
                user_id=user.id, record_date=rec["record_date"]).first()
            if existing:
                for k, v in rec.items():
                    if k not in ("user_id", "record_date", "uploaded_at", "id"):
                        setattr(existing, k, v)
                existing.uploaded_at = datetime.utcnow()
            else:
                db.session.add(SleepRecord(**rec))
                inserted += 1

        db.session.commit()
        log.info("用户 %s 上传数据：%s 条，新增 %s 条", user.username, len(records), inserted)
        return jsonify({
            "message": f"上传成功，解析 {len(records)} 条，新增 {inserted} 条",
            "total_parsed": len(records),
            "inserted": inserted,
            "updated": len(records) - inserted,
        })
    except Exception as e:
        log.error("数据上传处理失败：%s", e)
        return jsonify({"error": f"数据处理失败：{str(e)}"}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


@data_bp.route("/records", methods=["GET"])
@login_required
def list_records():
    """查看当前用户的睡眠数据列表（分页）"""
    user = get_current_user()
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 30))

    query = SleepRecord.query.filter_by(user_id=user.id).order_by(
        SleepRecord.record_date.desc())
    total = query.count()
    records = query.offset((page - 1) * page_size).limit(page_size).all()

    return jsonify({
        "data": [r.to_dict() for r in records],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@data_bp.route("/records/<int:record_id>", methods=["GET"])
@login_required
def get_record(record_id):
    """查看单条睡眠记录"""
    user = get_current_user()
    record = SleepRecord.query.filter_by(id=record_id, user_id=user.id).first()
    if not record:
        return jsonify({"error": "记录不存在"}), 404
    return jsonify({"data": record.to_dict()})


@data_bp.route("/records/<int:record_id>", methods=["DELETE"])
@login_required
def delete_record(record_id):
    """删除单条睡眠记录"""
    user = get_current_user()
    record = SleepRecord.query.filter_by(id=record_id, user_id=user.id).first()
    if not record:
        return jsonify({"error": "记录不存在"}), 404
    db.session.delete(record)
    db.session.commit()
    return jsonify({"message": "删除成功"})


@data_bp.route("/preprocess", methods=["POST"])
@login_required
def run_preprocess():
    """
    一键预处理：对当前用户全部数据重新计算衍生指标。
    相当于把 preprocess.py 的核心逻辑应用到用户数据上。
    """
    user = get_current_user()
    records = SleepRecord.query.filter_by(user_id=user.id).all()

    updated = 0
    for r in records:
        deep = r.deepSleepTime or 0
        shallow = r.shallowSleepTime or 0
        rem = r.REMTime or 0
        wake = r.wakeTime or 0
        total = deep + shallow + rem

        r.totalSleepMinutes = round(total, 2)
        r.deepSleepRatio = round(deep / total, 4) if total > 0 else 0
        r.REMRatio = round(rem / total, 4) if total > 0 else 0
        r.sleepEfficiency = round(total / (total + wake), 4) if (total + wake) > 0 else 0
        r.wakeRatio = round(wake / (total + wake), 4) if (total + wake) > 0 else 0
        r.sleepQualityScore = round(
            r.deepSleepRatio * 40 + r.REMRatio * 30 +
            r.sleepEfficiency * 20 - r.wakeRatio * 10, 2
        )
        r.sleepQualityScore = max(0, min(100, r.sleepQualityScore))
        updated += 1

    db.session.commit()
    log.info("用户 %s 一键预处理：更新 %s 条", user.username, updated)
    return jsonify({"message": f"预处理完成，更新 {updated} 条记录"})


@data_bp.route("/stats", methods=["GET"])
@login_required
def personal_stats():
    """当前用户的睡眠统计概览"""
    user = get_current_user()
    records = SleepRecord.query.filter_by(user_id=user.id).all()
    if not records:
        return jsonify({"stats": {"total_records": 0}})

    scores = [r.sleepQualityScore for r in records if r.sleepQualityScore]
    totals = [r.totalSleepMinutes for r in records if r.totalSleepMinutes]
    effs = [r.sleepEfficiency for r in records if r.sleepEfficiency]

    def _avg(lst):
        return round(sum(lst) / len(lst), 2) if lst else 0

    return jsonify({"stats": {
        "total_records": len(records),
        "avg_quality_score": _avg(scores),
        "avg_sleep_minutes": _avg(totals),
        "avg_efficiency": _avg(effs),
        "date_range_start": min(r.record_date for r in records if r.record_date) if records else None,
        "date_range_end": max(r.record_date for r in records if r.record_date) if records else None,
    }})


# ---------- 管理员路由 ----------

@data_bp.route("/admin/all_records", methods=["GET"])
@admin_required
def admin_all_records():
    """管理员查看全站所有用户数据"""
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 30))
    user_id_filter = request.args.get("user_id")

    query = SleepRecord.query.order_by(SleepRecord.uploaded_at.desc())
    if user_id_filter:
        query = query.filter_by(user_id=int(user_id_filter))
    total = query.count()
    records = query.offset((page - 1) * page_size).limit(page_size).all()

    return jsonify({
        "data": [r.to_dict() for r in records],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@data_bp.route("/admin/delete_record/<int:record_id>", methods=["DELETE"])
@admin_required
def admin_delete_record(record_id):
    """管理员删除任意记录"""
    record = SleepRecord.query.get(record_id)
    if not record:
        return jsonify({"error": "记录不存在"}), 404
    db.session.delete(record)
    db.session.commit()
    return jsonify({"message": "删除成功"})
