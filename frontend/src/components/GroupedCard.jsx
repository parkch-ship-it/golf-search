import { useState, useEffect, useRef } from 'react'

const PLATFORM_STYLE = {
  '티스캐너':    { badge: 'bg-blue-100 text-blue-700',   border: 'border-blue-200' },
  '카카오골프':  { badge: 'bg-yellow-100 text-yellow-700', border: 'border-yellow-200' },
  '티업앤조이':  { badge: 'bg-purple-100 text-purple-700', border: 'border-purple-200' },
  '스마트스코어':{ badge: 'bg-orange-100 text-orange-700', border: 'border-orange-200' },
  '골프존카운티':{ badge: 'bg-teal-100 text-teal-700',   border: 'border-teal-200' },
}

function getDateFromUrl(url) {
  const m = url.match(/(?:roundDay|bookingDay|date)=([^&]+)/)
  return m ? m[1] : ''
}

export default function GroupedCard({ items, showDistance, getDistance, timeRange, onPriceLoaded }) {
  const [expanded, setExpanded] = useState(false)
  const [expandLoading, setExpandLoading] = useState(false)
  // platform → slots[] (undefined=미조회, []=없음)
  const [platformSlots, setPlatformSlots] = useState({})
  // auto-fetch 완료된 플랫폼 목록 (가격 없어도 완료 표시)
  const [autoFetchDone, setAutoFetchDone] = useState(new Set())
  const autoFetchedRef = useRef(new Set())

  const rep = items[0]  // 대표 아이템

  const from = timeRange?.from || '00:00'
  const to   = timeRange?.to   || '23:59'

  // 시간 범위 내 슬롯에서 최저가 계산
  function platformMinFromSlots(platform) {
    const slots = platformSlots[platform]
    if (!slots || slots.length === 0) return null
    const prices = slots
      .filter(s => !s.time || (s.time >= from && s.time <= to))
      .filter(s => s.price > 0)
      .map(s => s.price)
    return prices.length > 0 ? Math.min(...prices) : null
  }

  // 마운트 시: price=0 항목 자동 조회 (가격 표시·정렬용)
  useEffect(() => {
    items.forEach(item => {
      if (!item.club_id || item.price > 0) return
      if (autoFetchedRef.current.has(item.platform)) return
      autoFetchedRef.current.add(item.platform)

      const date = getDateFromUrl(item.booking_url)
      if (!date) return

      const params = new URLSearchParams({ platform: item.platform, club_id: item.club_id, date })
      fetch(`/api/detail?${params}`)
        .then(r => r.json())
        .then(data => {
          const slots = data.slots || []
          setPlatformSlots(prev => ({ ...prev, [item.platform]: slots }))
          const prices = slots
            .filter(s => !s.time || (s.time >= from && s.time <= to))
            .filter(s => s.price > 0)
            .map(s => s.price)
          if (prices.length > 0 && onPriceLoaded) {
            onPriceLoaded(item.platform, item.course_name, Math.min(...prices))
          }
        })
        .catch(() => {
          setPlatformSlots(prev => ({ ...prev, [item.platform]: [] }))
        })
        .finally(() => {
          setAutoFetchDone(prev => new Set([...prev, item.platform]))
        })
    })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleExpand() {
    if (expanded) {
      setExpanded(false)
      return
    }
    // 아직 조회 안 된 플랫폼 한꺼번에 조회
    const toFetch = items.filter(item => item.club_id && platformSlots[item.platform] === undefined)
    if (toFetch.length > 0) {
      setExpandLoading(true)
      await Promise.all(toFetch.map(async item => {
        const date = getDateFromUrl(item.booking_url)
        if (!date) return
        try {
          const params = new URLSearchParams({ platform: item.platform, club_id: item.club_id, date })
          const res = await fetch(`/api/detail?${params}`)
          const data = await res.json()
          setPlatformSlots(prev => ({ ...prev, [item.platform]: data.slots || [] }))
        } catch {
          setPlatformSlots(prev => ({ ...prev, [item.platform]: [] }))
        }
      }))
      setExpandLoading(false)
    }
    setExpanded(true)
  }

  // 그룹 최저가 (시간 범위 적용된 슬롯 우선, 없으면 item.price)
  function groupMinPrice() {
    const prices = []
    items.forEach(item => {
      const slotMin = platformMinFromSlots(item.platform)
      if (slotMin !== null) {
        prices.push(slotMin)
      } else if (platformSlots[item.platform] === undefined && item.price > 0) {
        prices.push(item.price)
      }
    })
    return prices.length > 0 ? Math.min(...prices) : null
  }

  const minPrice = groupMinPrice()
  const canExpand = items.some(item => !!item.club_id)
  const distanceStr = (() => {
    if (!showDistance || !getDistance) return null
    const d = getDistance(rep)
    return d < 9999 ? `${Math.round(d)}km` : null
  })()

  // 정규화된 코스명 (괄호 제거)
  const displayName = rep.course_name.replace(/\s*\([^)]*\)\s*/g, '').trim()

  return (
    <div className="card slide-up bg-white">
      {/* 메인 행 */}
      <div className="flex items-center gap-3">
        {/* 시간/홀 */}
        <div className="text-center min-w-[52px]">
          <div className="text-[11px] font-semibold text-gray-400 leading-tight">시간<br/>확인</div>
          <div className="text-[10px] text-gray-400">{rep.holes || 18}홀</div>
        </div>

        {/* 구분선 */}
        <div className="w-px h-10 bg-gray-200 flex-shrink-0" />

        {/* 정보 */}
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-sm text-gray-900 truncate">{displayName}</div>
          <div className="flex items-center flex-wrap gap-1 mt-0.5">
            {/* 플랫폼 배지 — 클릭 시 해당 플랫폼 예약 페이지 */}
            {items.map(item => {
              const st = PLATFORM_STYLE[item.platform] || { badge: 'bg-gray-100 text-gray-600' }
              return (
                <button
                  key={item.platform}
                  onClick={() => window.open(item.booking_url, '_blank', 'noopener,noreferrer')}
                  className={`platform-badge ${st.badge} active:scale-95 transition-transform cursor-pointer`}
                  title={`${item.platform}에서 예약`}
                >
                  {item.platform}
                </button>
              )
            })}
            {rep.region && (
              <span className="text-xs text-gray-400">{rep.region}</span>
            )}
            {distanceStr && (
              <span className="text-xs text-blue-500 font-medium">📍{distanceStr}</span>
            )}
          </div>
          <div className="text-sm font-bold text-gray-800 mt-0.5">
            {minPrice
              ? `최저 ${minPrice.toLocaleString()}원`
              : items.some(i => i.price === 0 && i.club_id && !autoFetchDone.has(i.platform))
                ? '가격 조회중...'
                : '가격 미정'}
          </div>
        </div>

        {/* 시간대 토글 */}
        {canExpand && (
          <div className="flex-shrink-0">
            <button
              onClick={handleExpand}
              className={`flex items-center gap-0.5 text-[11px] font-medium px-2 py-1 rounded-lg
                          transition-all active:scale-95
                          ${expanded
                            ? 'bg-[#1a6b3c] text-white'
                            : 'bg-white text-[#1a6b3c] border border-[#1a6b3c]'
                          }`}
            >
              {expandLoading ? (
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
          </div>
        )}
      </div>

      {/* 펼쳐지는 플랫폼별 시간대 */}
      {expanded && (
        <div className="mt-2 pt-2 border-t border-gray-200 space-y-3">
          {items.map(item => {
            const st = PLATFORM_STYLE[item.platform] || { badge: 'bg-gray-100 text-gray-600', border: 'border-gray-200' }
            const slots = platformSlots[item.platform]

            return (
              <div key={item.platform}>
                {/* 플랫폼 헤더 + 예약 버튼 */}
                <div className="flex items-center justify-between mb-1.5">
                  <span className={`platform-badge ${st.badge}`}>{item.platform}</span>
                  <button
                    onClick={() => window.open(item.booking_url, '_blank', 'noopener,noreferrer')}
                    className="bg-[#1a6b3c] text-white text-xs font-bold
                               px-3 py-1.5 rounded-xl active:scale-95 transition-transform"
                  >
                    예약
                  </button>
                </div>

                {/* 슬롯 목록 */}
                {slots === undefined ? (
                  <div className="text-xs text-gray-400 text-center py-1">불러오는 중...</div>
                ) : !slots || slots.length === 0 ? (
                  <div className="text-xs text-gray-400 text-center py-1">티타임 정보 없음</div>
                ) : (
                  <div className="grid grid-cols-2 gap-1.5">
                    {slots.filter(s => !s.time || (s.time >= from && s.time <= to)).map((s, i) => {
                      return (
                        <div
                          key={i}
                          className="flex items-center justify-between rounded-lg px-2 py-1.5 border text-xs bg-white border-gray-100"
                        >
                          <div className="flex items-center gap-1.5">
                            <span className="font-bold text-sm w-10 text-[#1a6b3c]">
                              {s.time}
                            </span>
                            <span className="text-gray-500 truncate max-w-[70px]" title={s.course}>{s.course}</span>
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
            )
          })}
        </div>
      )}
    </div>
  )
}
