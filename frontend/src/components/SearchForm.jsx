import { useState } from 'react'

const HOURS = Array.from({ length: 19 }, (_, i) => {
  const h = i + 4  // 04 ~ 22
  return String(h).padStart(2, '0') + ':00'
})

function HourSelect({ value, onChange }) {
  return (
    <select
      className="input-field"
      value={value}
      onChange={e => onChange(e.target.value)}
    >
      {HOURS.map(h => (
        <option key={h} value={h}>{h}</option>
      ))}
    </select>
  )
}

const REGIONS = [
  '서울', '경기', '인천', '강원',
  '충북', '충남', '대전',
  '전북', '전남', '광주',
  '경북', '경남', '대구',
  '부산', '울산', '제주',
]

function todayStr() {
  return new Date().toISOString().slice(0, 10)
}

export default function SearchForm({ onSearch, loading }) {
  const [date, setDate] = useState(todayStr())
  const [selectedRegions, setSelectedRegions] = useState([])  // 빈 배열 = 전체
  const [players, setPlayers] = useState(4)
  const [timeFrom, setTimeFrom] = useState('06:00')
  const [timeTo, setTimeTo] = useState('18:00')
  const [expanded, setExpanded] = useState(false)

  function toggleRegion(r) {
    setSelectedRegions(prev =>
      prev.includes(r) ? prev.filter(x => x !== r) : [...prev, r]
    )
  }

  function clearRegions() {
    setSelectedRegions([])
  }

  function handleSubmit(e) {
    e.preventDefault()
    onSearch({
      date,
      regions: selectedRegions,
      players,
      time_from: timeFrom,
      time_to: timeTo,
    })
  }

  const visibleRegions = expanded ? REGIONS : REGIONS.slice(0, 8)
  const isAll = selectedRegions.length === 0

  return (
    <form onSubmit={handleSubmit} className="card mt-4">
      {/* 날짜 */}
      <div className="mb-3">
        <label className="text-xs font-semibold text-gray-500 block mb-1">날짜</label>
        <input
          type="date"
          className="input-field"
          value={date}
          min={todayStr()}
          onChange={e => setDate(e.target.value)}
          required
        />
      </div>

      {/* 지역 다중 선택 */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1">
          <label className="text-xs font-semibold text-gray-500">
            지역
            {selectedRegions.length > 0 && (
              <span className="ml-1.5 text-[#1a6b3c] font-bold">{selectedRegions.length}개 선택</span>
            )}
          </label>
          {selectedRegions.length > 0 && (
            <button
              type="button"
              onClick={clearRegions}
              className="text-xs text-gray-400 underline"
            >
              전체 해제
            </button>
          )}
        </div>

        <div className="flex flex-wrap gap-1.5">
          {/* 전체 버튼 */}
          <button
            type="button"
            onClick={clearRegions}
            className={`text-xs px-3 py-1.5 rounded-full border transition-colors
              ${isAll
                ? 'bg-[#1a6b3c] text-white border-[#1a6b3c]'
                : 'bg-white text-gray-600 border-gray-200'}`}
          >
            전체
          </button>

          {visibleRegions.map(r => {
            const selected = selectedRegions.includes(r)
            return (
              <button
                key={r}
                type="button"
                onClick={() => toggleRegion(r)}
                className={`text-xs px-3 py-1.5 rounded-full border transition-colors
                  ${selected
                    ? 'bg-[#1a6b3c] text-white border-[#1a6b3c]'
                    : 'bg-white text-gray-600 border-gray-200'}`}
              >
                {selected && <span className="mr-0.5">✓</span>}
                {r}
              </button>
            )
          })}

          <button
            type="button"
            onClick={() => setExpanded(v => !v)}
            className="text-xs px-3 py-1.5 rounded-full border border-dashed border-gray-300 text-gray-400"
          >
            {expanded ? '접기 ▲' : '더보기 ▼'}
          </button>
        </div>

        {/* 선택된 지역 요약 */}
        {selectedRegions.length > 0 && (
          <div className="mt-1.5 text-xs text-[#1a6b3c] bg-green-50 rounded-lg px-3 py-1.5">
            선택: {selectedRegions.join(' · ')}
          </div>
        )}
      </div>

      {/* 인원 */}
      <div className="mb-3">
        <label className="text-xs font-semibold text-gray-500 block mb-1">인원</label>
        <div className="flex gap-2">
          {[2, 3, 4].map(n => (
            <button
              key={n}
              type="button"
              onClick={() => setPlayers(n)}
              className={`flex-1 py-2 rounded-xl border text-sm font-medium transition-colors
                ${players === n
                  ? 'bg-[#1a6b3c] text-white border-[#1a6b3c]'
                  : 'bg-white text-gray-600 border-gray-200'}`}
            >
              {n}인
            </button>
          ))}
        </div>
      </div>

      {/* 시간대 */}
      <div className="mb-4">
        <label className="text-xs font-semibold text-gray-500 block mb-1">
          시간대&nbsp;
          <span className="font-normal text-gray-400">{timeFrom} ~ {timeTo}</span>
        </label>
        <div className="flex gap-2 items-center">
          <HourSelect value={timeFrom} onChange={setTimeFrom} />
          <span className="text-gray-400 flex-shrink-0">~</span>
          <HourSelect value={timeTo} onChange={setTimeTo} />
        </div>
      </div>

      <button type="submit" className="btn-primary w-full" disabled={loading}>
        {loading ? '검색 중...' : '티타임 검색'}
      </button>
    </form>
  )
}
