# ============================================================
# 睡眠质量分析系统 - DeepSeek API 个性化改善建议生成
# 使用 DeepSeek V4 Flash 标准思考工作量
# 配置项保存于 config.txt 中
# ============================================================

import os
import json
import logging
from typing import Dict, Optional

log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_deepseek_config() -> dict:
    """从 config.txt 加载 DeepSeek 配置"""
    cfg = {}
    config_path = os.path.join(BASE_DIR, "config.txt")
    try:
        with open(config_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    cfg[key.strip()] = val.strip()
    except Exception as e:
        log.warning("读取 config.txt 失败：%s", e)
    return cfg


def generate_suggestions_via_deepseek(
    sleep_data: Dict[str, float],
    model_comparison: Optional[Dict] = None,
    feature_importance: Optional[Dict[str, float]] = None,
    predicted_score: float = 0,
) -> str:
    """
    调用 DeepSeek API 生成个性化睡眠改善建议。

    参数:
        sleep_data: 用户睡眠指标字典，如 {deepSleepRatio, REMRatio, sleepEfficiency, avgHeartRate, ...}
        model_comparison: 多模型对比结果
        feature_importance: 特征重要性
        predicted_score: 预测的睡眠质量评分

    返回:
        中文个性化改善建议文本
    """
    cfg = _load_deepseek_config()

    api_key = cfg.get("DEEPSEEK_API_KEY", "")
    api_base = cfg.get("DEEPSEEK_API_BASE", "https://api.deepseek.com")
    model = cfg.get("DEEPSEEK_MODEL", "deepseek-chat")
    timeout = int(cfg.get("DEEPSEEK_TIMEOUT", "30"))
    max_tokens = int(cfg.get("DEEPSEEK_MAX_TOKENS", "1024"))
    temperature = float(cfg.get("DEEPSEEK_TEMPERATURE", "0.7"))

    # 如果没有配置 API Key，回退到规则引擎
    if not api_key or api_key.startswith("sk-your-"):
        log.info("DeepSeek API Key 未配置，使用规则引擎生成建议")
        return _generate_rule_based_suggestions(sleep_data, predicted_score)

    try:
        import requests

        # 构建提示词
        system_prompt = """你是一位专业的睡眠医学专家和健康顾问。请根据用户提供的睡眠数据指标，
生成3-5条具体的、可操作的个性化睡眠改善建议。

要求：
1. 每条建议应基于具体数据指标，而非泛泛而谈
2. 建议应涵盖不同方面：睡眠卫生、运动、饮食、环境优化、压力管理
3. 使用中文，语气专业但温暖
4. 每条建议以"• "开头，50-100字
5. 不要使用markdown格式，纯文本输出"""

        user_prompt = _build_user_prompt(sleep_data, predicted_score, feature_importance)

        url = f"{api_base}/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        resp = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        suggestions = data["choices"][0]["message"]["content"].strip()
        log.info("DeepSeek API 建议生成成功（%d 字符）", len(suggestions))
        return suggestions

    except ImportError as e:
        log.warning("requests 库未安装，使用规则引擎生成建议：%s", e)
        return _generate_rule_based_suggestions(sleep_data, predicted_score)
    except Exception as e:
        log.warning("DeepSeek API 调用失败（%s），回退规则引擎", e)
        return _generate_rule_based_suggestions(sleep_data, predicted_score)


def _build_user_prompt(
    sleep_data: Dict[str, float],
    predicted_score: float,
    feature_importance: Optional[Dict[str, float]] = None,
) -> str:
    """构建发送给 DeepSeek 的用户提示词"""
    # 指标中文映射
    labels = {
        "totalSleepMinutes": "总睡眠时长(分钟)",
        "deepSleepTime": "深睡时长(分钟)",
        "shallowSleepTime": "浅睡时长(分钟)",
        "REMTime": "REM时长(分钟)",
        "wakeTime": "清醒时长(分钟)",
        "sleepEfficiency": "睡眠效率(0-1)",
        "deepSleepRatio": "深睡比例(0-1)",
        "REMRatio": "REM比例(0-1)",
        "wakeRatio": "清醒比例(0-1)",
        "daySteps": "日步数",
        "dayCalories": "日卡路里消耗",
        "avgHeartRate": "平均心率(bpm)",
        "temperature": "环境温度(°C)",
        "humidity": "环境湿度(%)",
        "noise_db": "环境噪声(dB)",
        "spo2": "血氧饱和度(%)",
        "movement_freq": "体动频率(次/分钟)",
    }

    lines = [f"睡眠质量预测评分：{predicted_score:.1f}/10"]
    lines.append("\n用户的睡眠数据指标：")
    for key, val in sleep_data.items():
        if val is not None and key in labels:
            lines.append(f"  - {labels[key]}：{val}")

    if feature_importance:
        # 找出最重要的3个特征
        sorted_fi = sorted(feature_importance.items(), key=lambda x: abs(x[1]), reverse=True)[:3]
        lines.append("\n影响最大的因素：")
        for feat, imp in sorted_fi:
            lines.append(f"  - {labels.get(feat, feat)}（权重：{imp:.4f}）")

    # 评分解读
    if predicted_score >= 8:
        lines.append("\n评分解读：睡眠质量优秀，继续保持现有习惯。")
    elif predicted_score >= 6:
        lines.append("\n评分解读：睡眠质量良好，有小幅优化空间。")
    elif predicted_score >= 4:
        lines.append("\n评分解读：睡眠质量一般，建议采取改善措施。")
    else:
        lines.append("\n评分解读：睡眠质量较差，需要重点关注改善。")

    return "\n".join(lines)


def _generate_rule_based_suggestions(
    sleep_data: Dict[str, float],
    predicted_score: float,
) -> str:
    """
    基于规则的睡眠改善建议生成器（DeepSeek API 不可用时的回退方案）。
    根据各项指标与理想范围的偏差，生成针对性建议。
    """
    suggestions = []

    # 获取指标（带默认值）
    deep_ratio = sleep_data.get("deepSleepRatio", 0.2)
    rem_ratio = sleep_data.get("REMRatio", 0.2)
    efficiency = sleep_data.get("sleepEfficiency", 0.85)
    wake_ratio = sleep_data.get("wakeRatio", 0.05)
    total_sleep = sleep_data.get("totalSleepMinutes", 420)
    heart_rate = sleep_data.get("avgHeartRate", 68)
    steps = sleep_data.get("daySteps", 6000)
    spo2 = sleep_data.get("spo2", 97)
    movement = sleep_data.get("movement_freq", 5)
    temperature = sleep_data.get("temperature", 22)
    humidity = sleep_data.get("humidity", 50)
    noise = sleep_data.get("noise_db", 35)

    # 深睡比例评估（理想 15-25%）
    if deep_ratio < 0.15:
        suggestions.append(
            "• 深睡比例偏低（{:.0%}）。建议：睡前1小时避免使用电子设备，蓝光会抑制褪黑素分泌；"
            "保持卧室完全黑暗，温度控制在18-22°C；适量补充镁元素有助于增加深睡时长。".format(deep_ratio)
        )
    elif deep_ratio > 0.30:
        suggestions.append(
            "• 深睡比例较高（{:.0%}），可能反映身体处于恢复期。建议保持规律作息，"
            "避免过度疲劳导致身体需要额外深睡补偿。".format(deep_ratio)
        )

    # REM比例评估（理想 20-25%）
    if rem_ratio < 0.18:
        suggestions.append(
            "• REM睡眠（快速眼动期）比例偏低（{:.0%}）。REM睡眠对记忆巩固和情绪调节至关重要。"
            "建议：确保总睡眠时长充足（7-9小时），避免酒精摄入（酒精会抑制REM睡眠），"
            "睡前可进行冥想或深呼吸练习以降低压力水平。".format(rem_ratio)
        )

    # 睡眠效率评估（理想 >85%）
    if efficiency < 0.80:
        suggestions.append(
            "• 睡眠效率偏低（{:.0%}），表明卧床时间中有较多清醒时段。建议："
            "只在感到困倦时上床，如果20分钟内无法入睡则起床进行放松活动；"
            "建立固定的起床时间，避免白天长时间小睡（控制在20分钟内）。".format(efficiency)
        )

    # 清醒比例评估（理想 <10%）
    if wake_ratio > 0.15:
        suggestions.append(
            "• 夜间清醒时间偏多（{:.0%}）。建议：检查是否有夜间如厕需求（睡前2小时限制饮水）；"
            "保持卧室安静、黑暗；如果频繁醒来，考虑排查睡眠呼吸暂停等潜在问题。".format(wake_ratio)
        )

    # 心率评估（静息心率理想 50-70 bpm）
    if heart_rate > 75:
        suggestions.append(
            "• 平均心率偏高（{} bpm），可能影响睡眠深度。建议：定期进行有氧运动（每周150分钟中等强度）；"
            "睡前避免咖啡因和尼古丁；练习腹式呼吸法帮助降低睡前心率。".format(int(heart_rate))
        )
    elif heart_rate < 50:
        suggestions.append(
            "• 平均心率偏低（{} bpm）。如果您是经常锻炼者，这是良好心血管健康的标志；"
            "如有头晕、乏力等症状，建议咨询医生。".format(int(heart_rate))
        )

    # 运动量评估
    if steps < 5000:
        suggestions.append(
            "• 日步数偏少（{}步），运动不足会影响睡眠质量。建议：每天至少步行8000步；"
            "午后进行30分钟中等强度运动最能促进深度睡眠，但睡前2小时避免剧烈运动。".format(int(steps))
        )
    elif steps > 20000:
        suggestions.append(
            "• 日步数较高（{}步），注意避免过度训练。高强度运动后应充分补充营养和水分，"
            "确保足够的恢复时间以维持良好睡眠质量。".format(int(steps))
        )

    # 总睡眠时长评估
    if total_sleep < 360:
        suggestions.append(
            "• 总睡眠时长不足（{:.0f}小时）。成年人建议7-9小时睡眠。"
            "尝试每天提前15分钟上床，逐步调整生物钟；建立固定的睡前仪式（阅读、温水浴等）。".format(total_sleep / 60)
        )
    elif total_sleep > 600:
        suggestions.append(
            "• 总睡眠时长偏长（{:.0f}小时）。过长睡眠可能与睡眠质量不佳有关，"
            "也可能提示潜在健康问题。建议保持规律作息并关注日间精力水平。".format(total_sleep / 60)
        )

    # 环境参数建议
    env_suggestions = []
    if temperature < 16 or temperature > 26:
        env_suggestions.append(f"温度调整至18-22°C（当前{temperature:.0f}°C）")
    if humidity < 30 or humidity > 70:
        env_suggestions.append(f"湿度调整至40-60%（当前{humidity:.0f}%）")
    if noise > 40:
        env_suggestions.append(f"降低噪声至30dB以下（当前{noise:.0f}dB），可使用白噪音机或耳塞")
    if env_suggestions:
        suggestions.append(
            "• 睡眠环境优化建议：" + "；".join(env_suggestions) + "。"
        )

    # SpO2 评估
    if spo2 < 94:
        suggestions.append(
            "• 血氧饱和度偏低（{:.0f}%），可能影响睡眠质量。建议：保持卧室通风良好；"
            "侧卧睡姿有助于改善呼吸；如持续低于94%，建议就医排查睡眠呼吸问题。".format(spo2)
        )

    # 体动频率
    if movement > 15:
        suggestions.append(
            "• 夜间体动频率偏高（{:.0f}次/分钟），表明睡眠不安稳。建议："
            "检查床垫和枕头是否舒适；避免睡前饮酒（虽助入睡但增加后半夜体动）。".format(movement)
        )

    # 最少3条建议
    if len(suggestions) < 3:
        suggestions.append("• 您的整体睡眠状况良好。继续保持规律作息、均衡饮食和适度运动，定期监测睡眠质量变化。")
        suggestions.append("• 建议每周记录睡眠日志，追踪入睡时间、醒来次数和日间精力水平，以便及时发现潜在问题。")
        suggestions.append("• 可以尝试每周进行2-3次正念冥想练习，有助于降低压力、改善睡眠质量。")

    # 补充通用建议直到至少3条
    general_tips = [
        "• 保持固定的睡眠时间表，即使在周末也尽量在同一时间起床和入睡。",
        "• 睡前1小时建立放松仪式：温水浴、阅读纸质书、轻柔音乐或冥想。",
        "• 卧室仅用于睡眠和亲密关系，避免在床上工作或使用电子设备。",
        "• 白天适度接触自然光（至少30分钟），有助于调节昼夜节律。",
        "• 避免睡前3小时内进食大餐，可选择香蕉、温牛奶等助眠食物作为晚间零食。",
    ]
    for tip in general_tips:
        if len(suggestions) >= 5:
            break
        if tip not in suggestions:
            suggestions.append(tip)

    return "\n".join(suggestions[:5])
