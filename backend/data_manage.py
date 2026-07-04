import os
import sys
import json
import logging
import uuid
import zipfile
import tempfile
import shutil
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
ROOT_DIR = os.path.dirname(BASE_DIR)
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
UPLOAD_FOLDER = os.path.join(ROOT_DIR, _cfg.get("UPLOAD_FOLDER", "uploads"))
MAX_SIZE_MB = int(_cfg.get("MAX_UPLOAD_SIZE_MB", "200"))
ALLOWED_EXT = set(_cfg.get("ALLOWED_EXTENSIONS", "csv").split(","))

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ---------- 快速预处理函数（内联 preprocess 核心逻辑） ----------

def _quick_preprocess_csv(filepath: str, user_id: int) -> list:
    """
    读取上传的文件（支持 CSV/Parquet/TXT），解析列并返回 SleepRecord 字典列表。
    兼容多种格式（小米手环 Zepp 导出 / 自定义格式 / Parquet / TXT）。
    """
    ext = filepath.rsplit(".", 1)[-1].lower() if "." in filepath else "csv"

    try:
        if ext == "parquet":
            df = pd.read_parquet(filepath)
        elif ext == "txt":
            # TXT: 尝试多种分隔符
            for sep in [",", "\t", "|", ";"]:
                try:
                    df = pd.read_csv(filepath, sep=sep, encoding="utf-8", nrows=5)
                    if len(df.columns) > 1:
                        df = pd.read_csv(filepath, sep=sep, encoding="utf-8")
                        break
                except Exception:
                    continue
            else:
                df = pd.read_csv(filepath, encoding="utf-8")
        else:
            try:
                df = pd.read_csv(filepath, encoding="utf-8")
            except Exception:
                df = pd.read_csv(filepath, encoding="utf-8", on_bad_lines="skip")
    except Exception as e:
        log.warning("读取文件失败 %s：%s", filepath, e)
        return []

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


def _quick_preprocess_all() -> int:
    """
    扫描 DATA/ 目录下所有 CSV，导入到 SleepRecord 表（关联到 admin 用户）。
    返回更新的记录数。用于启动时自动导入。
    """
    from models import User
    admin_user = User.query.filter_by(role="admin").first()
    if not admin_user:
        log.warning("无管理员用户，无法自动导入 DATA")
        return 0

    data_dir = os.path.join(ROOT_DIR, "DATA")
    if not os.path.isdir(data_dir):
        return 0

    total_updated = 0
    for folder in sorted(os.listdir(data_dir)):
        folder_path = os.path.join(data_dir, folder)
        if not os.path.isdir(folder_path):
            continue
        for fname in os.listdir(folder_path):
            ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
            if ext not in ("csv", "parquet", "txt"):
                continue
            fpath = os.path.join(folder_path, fname)
            try:
                recs = _quick_preprocess_csv(fpath, admin_user.id)
                for rec in recs:
                    existing = SleepRecord.query.filter_by(
                        user_id=admin_user.id, record_date=rec["record_date"]).first()
                    if existing:
                        for k, v in rec.items():
                            if k not in ("user_id", "record_date", "uploaded_at", "id"):
                                setattr(existing, k, v)
                        existing.uploaded_at = datetime.utcnow()
                    else:
                        db.session.add(SleepRecord(**rec))
                    total_updated += 1
                db.session.commit()
                log.info("自动导入：%s/%s → %s 条", folder, fname, len(recs))
            except Exception as e:
                log.warning("自动导入 %s/%s 失败：%s", folder, fname, e)

    return total_updated


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


# ---------- ZIP 压缩包上传 ----------

def _extract_and_process_zip(zip_path: str, user_id: int) -> dict:
    """解压 ZIP 文件，识别其中所有 CSV，逐一处理并入库"""
    results = {"total_parsed": 0, "inserted": 0, "updated": 0, "files_processed": 0}
    extract_dir = tempfile.mkdtemp(prefix="sleep_zip_")

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

        for root, dirs, files in os.walk(extract_dir):
            for fname in files:
                ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
                if ext not in ("csv", "parquet", "txt"):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    recs = _quick_preprocess_csv(fpath, user_id)
                    if not recs:
                        continue
                    results["files_processed"] += 1
                    for rec in recs:
                        results["total_parsed"] += 1
                        existing = SleepRecord.query.filter_by(
                            user_id=user_id, record_date=rec["record_date"]).first()
                        if existing:
                            for k, v in rec.items():
                                if k not in ("user_id", "record_date", "uploaded_at", "id"):
                                    setattr(existing, k, v)
                            existing.uploaded_at = datetime.utcnow()
                            results["updated"] += 1
                        else:
                            db.session.add(SleepRecord(**rec))
                            results["inserted"] += 1
                    db.session.commit()
                except Exception as e:
                    log.warning("处理 ZIP 内文件 %s 失败：%s", fname, e)
    finally:
        shutil.rmtree(extract_dir, ignore_errors=True)

    return results


@data_bp.route("/upload_zip", methods=["POST"])
@login_required
def upload_zip():
    """上传 ZIP 压缩包，自动解压并导入所有 CSV"""
    user = get_current_user()
    if "file" not in request.files:
        return jsonify({"error": "未选择文件"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "文件名为空"}), 400

    if not file.filename.lower().endswith(".zip"):
        return jsonify({"error": "仅支持 .zip 压缩包"}), 400

    zip_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}_{secure_filename(file.filename)}")
    file.save(zip_path)

    try:
        results = _extract_and_process_zip(zip_path, user.id)
        log.info("用户 %s 上传 ZIP：解析 %s 条，新增 %s 条，处理 %s 个CSV",
                 user.username, results["total_parsed"], results["inserted"], results["files_processed"])
        return jsonify({
            "message": f"ZIP 处理完成：{results['files_processed']} 个CSV，"
                       f"解析 {results['total_parsed']} 条，新增 {results['inserted']} 条",
            **results,
        })
    except Exception as e:
        log.error("ZIP 上传处理失败：%s", e)
        return jsonify({"error": f"ZIP 处理失败：{str(e)}"}), 500
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)


# ---------- 多文件上传 ----------

@data_bp.route("/upload_multi", methods=["POST"])
@login_required
def upload_multi():
    """一次上传多个 CSV 文件"""
    user = get_current_user()
    files = request.files.getlist("files")
    if not files or all(f.filename == "" for f in files):
        return jsonify({"error": "未选择文件"}), 400

    total_parsed, total_inserted, total_updated, files_ok = 0, 0, 0, 0
    errors = []

    for file in files:
        if file.filename == "":
            continue
        if not _allowed_file(file.filename, ALLOWED_EXT):
            errors.append(f"{file.filename}: 不支持的格式")
            continue

        filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        try:
            records = _quick_preprocess_csv(filepath, user.id)
            if not records:
                errors.append(f"{file.filename}: 未解析到有效数据")
                continue

            files_ok += 1
            for rec in records:
                total_parsed += 1
                existing = SleepRecord.query.filter_by(
                    user_id=user.id, record_date=rec["record_date"]).first()
                if existing:
                    for k, v in rec.items():
                        if k not in ("user_id", "record_date", "uploaded_at", "id"):
                            setattr(existing, k, v)
                    existing.uploaded_at = datetime.utcnow()
                    total_updated += 1
                else:
                    db.session.add(SleepRecord(**rec))
                    total_inserted += 1
            db.session.commit()
        except Exception as e:
            errors.append(f"{file.filename}: {str(e)}")
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)

    log.info("用户 %s 批量上传：%s 个文件成功，解析 %s 条，新增 %s 条",
             user.username, files_ok, total_parsed, total_inserted)

    return jsonify({
        "message": f"批量上传完成：{files_ok} 个文件，解析 {total_parsed} 条，新增 {total_inserted} 条",
        "total_parsed": total_parsed,
        "inserted": total_inserted,
        "updated": total_updated,
        "files_processed": files_ok,
        "errors": errors if errors else None,
    })


# ---------- 一键处理（上传后自动完成全流程） ----------

@data_bp.route("/process_all", methods=["POST"])
@login_required
def process_all():
    """
    一键处理：对当前用户数据执行
    预处理 → 特征重计算 → 分析 → 返回可视化数据
    """
    user = get_current_user()
    records = SleepRecord.query.filter_by(user_id=user.id).all()
    if not records:
        return jsonify({"error": "暂无数据，请先上传"}), 400

    # 1. 预处理：重新计算衍生指标
    updated = 0
    for r in records:
        deep = r.deepSleepTime or 0
        shallow = r.shallowSleepTime or 0
        rem = r.REMTime or 0
        wake = r.wakeTime or 0
        total = deep + shallow + rem

        r.totalSleepMinutes = round(total, 2) if r.totalSleepMinutes == 0 else r.totalSleepMinutes
        r.deepSleepRatio = round(deep / total, 4) if total > 0 else 0
        r.REMRatio = round(rem / total, 4) if total > 0 else 0
        r.sleepEfficiency = round(total / (total + wake), 4) if (total + wake) > 0 else 0
        r.wakeRatio = round(wake / (total + wake), 4) if (total + wake) > 0 else 0
        if not r.sleepQualityScore or r.sleepQualityScore == 0:
            r.sleepQualityScore = round(
                r.deepSleepRatio * 40 + r.REMRatio * 30 +
                r.sleepEfficiency * 20 - r.wakeRatio * 10, 2
            )
            r.sleepQualityScore = max(1, min(10, round(r.sleepQualityScore, 1)))
        updated += 1

    db.session.commit()

    # 2. 生成可视化数据摘要
    dates = sorted(set(r.record_date for r in records if r.record_date))
    scores = [r.sleepQualityScore for r in records if r.sleepQualityScore]
    efficiencies = [r.sleepEfficiency for r in records if r.sleepEfficiency]
    total_sleep = [r.totalSleepMinutes for r in records if r.totalSleepMinutes]

    def _avg(lst):
        return round(sum(lst) / len(lst), 2) if lst else 0

    # 3. 阶段占比
    total_deep = sum(r.deepSleepTime or 0 for r in records)
    total_shallow = sum(r.shallowSleepTime or 0 for r in records)
    total_rem = sum(r.REMTime or 0 for r in records)
    total_wake = sum(r.wakeTime or 0 for r in records)
    total_all = total_deep + total_shallow + total_rem + total_wake or 1

    log.info("用户 %s 一键处理完成：%s 条记录", user.username, updated)

    return jsonify({
        "message": f"一键处理完成，共 {updated} 条记录",
        "summary": {
            "total_records": len(records),
            "avg_quality_score": _avg(scores),
            "avg_sleep_minutes": _avg(total_sleep),
            "avg_efficiency": _avg(efficiencies),
            "date_range": [dates[0] if dates else None, dates[-1] if dates else None],
        },
        "stage_distribution": [
            {"name": "深睡", "value": round(total_deep, 1), "percent": round(total_deep / total_all * 100, 1)},
            {"name": "浅睡", "value": round(total_shallow, 1), "percent": round(total_shallow / total_all * 100, 1)},
            {"name": "REM", "value": round(total_rem, 1), "percent": round(total_rem / total_all * 100, 1)},
            {"name": "清醒", "value": round(total_wake, 1), "percent": round(total_wake / total_all * 100, 1)},
        ],
        "dates": dates,
        "quality_scores": scores,
        "efficiency_list": [round(e * 100, 1) for e in efficiencies],
        "sleep_minutes_list": total_sleep,
    })


# ---------- 公开数据 API（无需登录，用于展示 DATA 数据可视化） ----------

@data_bp.route("/public_summary", methods=["GET"])
def public_summary():
    """无需登录，查看系统中 DATA 文件夹导入的公开数据摘要"""
    # 使用一个系统内置用户来存储 DATA 数据（admin 用户）
    admin_user = None
    from models import User
    admin_user = User.query.filter_by(role="admin").first()
    if not admin_user:
        return jsonify({"error": "系统未初始化"}), 500

    records = SleepRecord.query.filter_by(user_id=admin_user.id).order_by(
        SleepRecord.record_date.asc()).all()
    if not records:
        return jsonify({"error": "暂无公开数据"}), 404

    dates = [r.record_date for r in records if r.record_date]
    scores = [r.sleepQualityScore for r in records if r.sleepQualityScore]
    efficiencies = [round((r.sleepEfficiency or 0) * 100, 1) for r in records]
    total_sleep = [r.totalSleepMinutes for r in records if r.totalSleepMinutes]
    deep_sleep = [r.deepSleepTime for r in records if r.deepSleepTime]
    rem_sleep = [r.REMTime for r in records if r.REMTime]
    steps = [r.daySteps for r in records if r.daySteps]
    heart_rate = [r.avgHeartRate for r in records if r.avgHeartRate]

    def _avg(lst):
        return round(sum(lst) / len(lst), 2) if lst else 0

    return jsonify({
        "total_records": len(records),
        "avg_quality_score": _avg(scores),
        "avg_sleep_minutes": _avg(total_sleep),
        "avg_efficiency": _avg([r.sleepEfficiency for r in records if r.sleepEfficiency]),
        "dates": dates,
        "quality_scores": scores,
        "efficiency_list": efficiencies,
        "total_sleep_minutes": total_sleep,
        "deep_sleep_minutes": deep_sleep,
        "rem_sleep_minutes": rem_sleep,
        "day_steps": steps,
        "avg_heart_rate": heart_rate,
    })


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
