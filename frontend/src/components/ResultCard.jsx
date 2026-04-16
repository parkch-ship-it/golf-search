import { useState, useEffect, useRef } from 'react'

const PLATFORM_STYLE = {
  '티스캐너':    { bg: 'bg-blue-50',   badge: 'bg-blue-100 text-blue-700' },
  '카카오골프':  { bg: 'bg-yellow-50', badge: 'bg-yellow-100 text-yellow-700' },
  '티업앤조이':  { bg: 'bg-purple-50', badge: 'bg-purple-100 text-purple-700' },
  '스마트스코어':{ bg: 'bg-orange-50', badge: 'bg-orange-100 text-orange-700' },
  '골프존카운티':{ bg: 'bg-teal-50',   badge: 'bg-teal-100 text-teal-700' },
}

function getDateFromUrl(bookingUrl) {
  const m = bookingUrl.match(/(?:roundDay|bookingDay|date)=([^&]+)/)
  return m ? m[1] : ''
}

export default function ResultCard({ item, showDistance, distance, timeRange, onPriceLoaded }) {
  const style = PLATFORM_STYLE[item.platform] || { bg: 'bg-gray-50', badge: 'bg-gray-100 text-gray-600' }
  const [expanded, setExpanded] = useState(false)
  const [slots, setSlots] = useState(null)   // null = 미로드, [] = 없음, [...] = 있음
  const [loading, setLoading] = useState(false)
  const [autoMinPrice, setAutoMinPrice] = useState(null)  // 자동 조회된 최저가
  const autoFetchedRef = useRef(false)

  const distanceStr = (showDistance && distance && distance < 9999)
    ? `${Math.round(distance)}km`
    : null

  const canExpand = !!item.club_id

  // price=0이고 club_id가 있으면 마운트 시 자동으로 최저가 조회
  useEffect(() => {
    if (!item.club_id || item.price > 0 || autoFetchedRef.current) return
    autoFetchedRef.current = true

    const date = getDateFromUrl(item.booking_url)
    if (!date) return

    const params = new URLSearchParams({ platform: item.platform, club_id: item.club_id, date })
    fetch(`/api/detail?${params}`)
      .then(r => r.json())
      .then(data => {
        const fetched = data.slots || []
        setSlots(fetched)  // 미리 캐싱 → 나중에 토글 시 재요청 없음
        const prices = fetched.filter(s => s.price > 0).map(s => s.price)
        if (prices.length > 0) {
          const minP = Math.min(...prices)
          setAutoMinPrice(minP)
          if (onPriceLoaded) onPriceLoaded(item.platform, item.course_name, minP)
        }
      })
      .catch(() => {})
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 가격 표시: 자동 조회된 최저가 우선
  const priceDisplay = (() => {
    if (autoMinPrice) {
      const base = item.price_display.split('(')[0].trim()  // "N개 가능" 부분만
      return `${base} (최저 ${autoMinPrice.toLocaleString()}원)`
    }
    return item.price_display || '가격 미정'
  })()

  async function toggleExpand() {
    if (!canExpand) return
    if (!expanded && slots === null) {
      setLoading(true)
      try {
        const date = getDateFromUrl(item.booking_url)
        const params = new URLSearchParams({ platform: item.platform, club_id: item.club_id, date })
        const res = await fetch(`/api/detail?${params}`)
        const data = await res.json()
        setSlots(data.slots || [])
      } catch {
        setSlots([])
      } finally {
        setLoading(false)
      }
    }
    setExpanded(prev => !prev)
  }

  return (
    <div className={`card slide-up ${style.bg}`}>
      {/* 메인 행 */}
      <div className="flex items-center gap-3">
        {/* 시간 */}
        <div className="text-center min-w-[52px]">
          {item.tee_time ? (
            <div className="text-xl font-bold text-[#1a6b3c] leading-tight">{item.tee_time}</div>
          ) : (
            <div className="text-[11px] font-semibold text-gray-400 leading-tight">시간<br/>확인</div>
          )}
          <div className="text-[10px] text-gray-400">{item.holes}홀</div>
        </div>

        {/* 구분선 */}
        <div className="w-px h-10 bg-gray-200 flex-shrink-0" />

        {/* 정보 */}
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-sm text-gray-900 truncate">{item.course_name}</div>
          <div className="flex items-center flex-wrap gap-1 mt-0.5">
            <span className={`platform-badge ${style.badge}`}>{item.platform}</span>
            {item.region && (
              <span className="text-xs text-gray-400">{item.region}</span>
            )}
            {distanceStr && (
              <span className="text-xs text-blue-500 font-medium">📍{distanceStr}</span>
            )}
            {item.caddy_type && (
              <span className="text-xs text-gray-400">{item.caddy_type}</span>
            )}
          </div>
          <div className="text-sm font-bold text-gray-800 mt-0.5">
            {priceDisplay}
          </div>
        </div>

        {/* 우측 버튼 그룹 */}
        <div className="flex flex-col items-center gap-1 flex-shrink-0">
          {/* 예약 버튼 */}
          <button
            onClick={() => window.open(item.booking_url, '_blank', 'noopener,noreferrer')}
            className="bg-[#1a6b3c] text-white text-xs font-bold
                       px-3 py-2 rounded-xl active:scale-95 transition-transform"
          >
            예약
          </button>

          {/* 시간대 펼치기 버튼 */}
          {canExpand && (
            <button
              onClick={toggleExpand}
              className={`flex items-center gap-0.5 text-[11px] font-medium px-2 py-1 rounded-lg
                          transition-all active:scale-95
                          ${expanded
                            ? 'bg-[#1a6b3c] text-white'
                            : 'bg-white text-[#1a6b3c] border border-[#1a6b3c]'
                          }`}
            >
              {loading ? (
                <span className="text-[10px]">…</span>
              ) : (
                <>
                  <span>시간대</span>
                  <svg
                    className={`w-3 h-3 transition-transform ${expanded ? 'rotate-180' : ''}`}
                    fill="none" stroke="currentColor" viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M19 9l-7 7-7-7" />
                  </svg>
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* 펼쳐지는 시간대 목록 */}
      {expanded && (
        <div className="mt-2 pt-2 border-t border-gray-200">
          {loading ? (
            <div className="text-xs text-gray-400 text-center py-2">불러오는 중...</div>
          ) : !slots || slots.length === 0 ? (
            <div className="text-xs text-gray-400 text-center py-2">티타임 정보 없음</div>
          ) : (
            <div className="grid grid-cols-2 gap-1.5">
              {slots.map((s, i) => {
                const from = timeRange?.from || '00:00'
                const to   = timeRange?.to   || '23:59'
                const inRange = !s.time || (s.time >= from && s.time <= to)
                return (
                  <div
                    key={i}
                    className={`flex items-center justify-between rounded-lg px-2 py-1.5
                               border text-xs
                               ${inRange
                                 ? 'bg-white border-gray-100'
                                 : 'bg-gray-50 border-gray-100 opacity-40'
                               }`}
                  >
                    <div className="flex items-center gap-1.5">
                      <span className={`font-bold text-sm w-10 ${inRange ? 'text-[#1a6b3c]' : 'text-gray-400'}`}>
                        {s.time}
                      </span>
                      <span className="text-gray-500 truncate max-w-[70px]">{s.course}</span>
                    </div>
                    <div className="text-right flex-shrink-0">
                      {s.discount && s.orig_price > s.price ? (
                        <div>
                          <span className="line-through text-gray-300 text-[10px] mr-1">
                            {s.orig_price.toLocaleString()}
                          </span>
                          <span className="font-semibold text-red-500">
                            {s.price.toLocaleString()}
                          </span>
                        </div>
                      ) : (
                        <span className="font-semibold text-gray-700">
                          {s.price ? s.price.toLocaleString() : '-'}
                        </span>
                      )}
                      {s.caddy && (
                        <div className="text-gray-400 text-[10px]">{s.caddy}</div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
