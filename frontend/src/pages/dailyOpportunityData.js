const inFlightDailyOpportunityLoads = new Map()

export function loadDailyOpportunityData(date) {
  if (inFlightDailyOpportunityLoads.has(date)) {
    return inFlightDailyOpportunityLoads.get(date)
  }

  const request = Promise.all([
    fetch(`/api/briefing/${date}/opportunities`),
    fetch(`/api/briefing/${date}/rdev-opportunities`),
  ])
    .then(async ([businessRes, rdevRes]) => {
      const [businessData, rdevData] = await Promise.all([
        businessRes.ok ? businessRes.json() : Promise.resolve({ opportunities: [] }),
        rdevRes.ok ? rdevRes.json() : Promise.resolve({ solutions: [] }),
      ])
      return {
        business: businessData.opportunities || [],
        rdev: rdevData,
      }
    })
    .finally(() => {
      inFlightDailyOpportunityLoads.delete(date)
    })

  inFlightDailyOpportunityLoads.set(date, request)
  return request
}
