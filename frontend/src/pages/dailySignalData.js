// 兼容旧简报快照（尚无 signals 字段）；不修改原始内容列表。
export function getSignalItems(briefing, track) {
  const items = briefing?.signals?.[track]
  return Array.isArray(items) ? items : []
}

// 旧归档没有 events 字段；空事件不是使用灵感/执行数据补足的理由。
export function getEventItems(briefing) {
  const items = briefing?.signals?.events
  return Array.isArray(items) ? items : []
}

export function getAccountItems(briefing) {
  const groups = briefing?.signals?.accounts
  return Array.isArray(groups)
    ? groups.filter(group => group && typeof group.handle === 'string')
      .map(group => ({ ...group, posts: Array.isArray(group.posts) ? group.posts : [] }))
    : []
}
