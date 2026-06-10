# ============================================================
# 睡眠质量分析系统 - 数据库模型 (SQLAlchemy)
# 三张核心表：用户表、睡眠数据表、分析报告表
# ============================================================

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """用户信息表：存储用户名、密码、角色权限、注册时间"""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")  # "user" 或 "admin"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联
    sleep_records = db.relationship("SleepRecord", backref="owner", lazy="dynamic",
                                     cascade="all, delete-orphan")
    analysis_reports = db.relationship("AnalysisReport", backref="owner", lazy="dynamic",
                                        cascade="all, delete-orphan")

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def is_admin(self) -> bool:
        return self.role == "admin"

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SleepRecord(db.Model):
    """睡眠数据表：绑定用户ID，存储每日睡眠汇总指标"""
    __tablename__ = "sleep_records"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    record_date = db.Column(db.String(20), nullable=False)
    deepSleepTime = db.Column(db.Float, default=0)
    shallowSleepTime = db.Column(db.Float, default=0)
    wakeTime = db.Column(db.Float, default=0)
    REMTime = db.Column(db.Float, default=0)
    totalSleepMinutes = db.Column(db.Float, default=0)
    deepSleepRatio = db.Column(db.Float, default=0)
    REMRatio = db.Column(db.Float, default=0)
    sleepEfficiency = db.Column(db.Float, default=0)
    wakeRatio = db.Column(db.Float, default=0)
    sleepQualityScore = db.Column(db.Float, default=0)
    daySteps = db.Column(db.Float, default=0)
    dayDistance = db.Column(db.Float, default=0)
    dayRunDistance = db.Column(db.Float, default=0)
    dayCalories = db.Column(db.Float, default=0)
    avgHeartRate = db.Column(db.Float, default=0)
    minHeartRate = db.Column(db.Float, default=0)
    maxHeartRate = db.Column(db.Float, default=0)
    stdHeartRate = db.Column(db.Float, default=0)
    nightAvgHR = db.Column(db.Float, default=0)
    nightAvgRR = db.Column(db.Float, default=0)
    naps = db.Column(db.Text, default="[]")
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "record_date": self.record_date,
            "deepSleepTime": self.deepSleepTime,
            "shallowSleepTime": self.shallowSleepTime,
            "wakeTime": self.wakeTime,
            "REMTime": self.REMTime,
            "totalSleepMinutes": self.totalSleepMinutes,
            "deepSleepRatio": self.deepSleepRatio,
            "REMRatio": self.REMRatio,
            "sleepEfficiency": self.sleepEfficiency,
            "wakeRatio": self.wakeRatio,
            "sleepQualityScore": self.sleepQualityScore,
            "daySteps": self.daySteps,
            "dayDistance": self.dayDistance,
            "dayRunDistance": self.dayRunDistance,
            "dayCalories": self.dayCalories,
            "avgHeartRate": self.avgHeartRate,
            "minHeartRate": self.minHeartRate,
            "maxHeartRate": self.maxHeartRate,
            "stdHeartRate": self.stdHeartRate,
            "nightAvgHR": self.nightAvgHR,
            "nightAvgRR": self.nightAvgRR,
            "naps": self.naps,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
        }


class AnalysisReport(db.Model):
    """分析报告表：绑定用户ID，存储预测结果与分析结论"""
    __tablename__ = "analysis_reports"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    predicted_score = db.Column(db.Float, default=0)
    input_params = db.Column(db.Text, default="{}")        # JSON: 用户输入参数
    shap_values = db.Column(db.Text, default="{}")          # JSON: SHAP特征贡献值
    suggestions = db.Column(db.Text, default="")            # 个性化建议文本
    feature_importance = db.Column(db.Text, default="{}")   # JSON: 特征重要性
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "user_id": self.user_id,
            "predicted_score": self.predicted_score,
            "input_params": json.loads(self.input_params) if self.input_params else {},
            "shap_values": json.loads(self.shap_values) if self.shap_values else {},
            "suggestions": self.suggestions,
            "feature_importance": json.loads(self.feature_importance) if self.feature_importance else {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
