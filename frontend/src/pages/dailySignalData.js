// 兼容旧简报快照（尚无 signals 字段）；不修改原始内容列表。
export function getSignalItems(briefing, track) {
  const items = briefing?.signals?.[track]
  return Array.isArray(items) ? items : []
}
