import GroupedCard from './GroupedCard'

export default function ResultList({ groups, showDistance, getDistance, timeRange, onPriceLoaded }) {
  if (!groups || groups.length === 0) return null

  return (
    <div className="space-y-2 mt-2">
      {groups.map((items, i) => (
        <GroupedCard
          key={`${items.map(r => r.platform).join('+')}::${items[0].course_name}::${i}`}
          items={items}
          showDistance={showDistance}
          getDistance={getDistance}
          timeRange={timeRange}
          onPriceLoaded={onPriceLoaded}
        />
      ))}
    </div>
  )
}
