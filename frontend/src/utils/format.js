/**
 * 时间格式化工具：将分钟数转换为 X小时Y分钟 格式
 */
export function formatMinutes(minutes) {
  if (minutes == null || isNaN(minutes) || minutes === 0) return '0分钟'
  const m = Math.round(minutes)
  const h = Math.floor(m / 60)
  const remain = m % 60
  if (h === 0) return `${remain}分钟`
  if (remain === 0) return `${h}小时`
  return `${h}小时${remain}分钟`
}

/**
 * 将分钟数格式化为简短形式（用于表格列）
 */
export function formatMinutesShort(minutes) {
  if (minutes == null || isNaN(minutes) || minutes === 0) return '-'
  const m = Math.round(minutes)
  const h = Math.floor(m / 60)
  const remain = m % 60
  if (h === 0) return `${remain}分`
  if (remain === 0) return `${h}时`
  return `${h}时${remain}分`
}
