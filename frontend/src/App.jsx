import { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import SearchForm from './components/SearchForm'
import ResultList from './components/ResultList'
import FilterBar from './components/FilterBar'
import Header from './components/Header'

// 코스명 정규화 (괄호 제거 → 플랫폼 간 동일 코스 묶기)
function normalizeName(name) {
  return name.replace(/\s*\([^)]*\)\s*/g, '').trim()
}

// 각 지역의 중심 좌표 (위도, 경도)
const REGION_COORDS = {
  '서울': [37.5665, 126.9780],
  '경기': [37.4138, 127.5183],
  '인천': [37.4563, 126.7052],
  '강원': [37.8228, 128.1555],
  '충북': [36.6424, 127.4890],
  '충남': [36.5184, 126.8000],
  '대전': [36.3504, 127.3845],
  '전북': [35.7175, 127.1530],
  '전남': [34.8679, 126.9910],
  '광주': [35.1595, 126.8526],
  '경북': [36.4919, 128.8889],
  '경남': [35.4606, 128.2132],
  '대구': [35.8714, 128.6014],
  '부산': [35.1796, 129.0756],
  '울산': [35.5384, 129.3114],
  '제주': [33.4996, 126.5312],
}

function haversine(lat1, lon1, lat2, lon2) {
  const R = 6371
  const dLat = (lat2 - lat1) * Math.PI / 180
  const dLon = (lon2 - lon1) * Math.PI / 180
  const a = Math.sin(dLat / 2) ** 2
    + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLon / 2) ** 2
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

export default function App() {
  const [results, setResults] = useState([])
  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const [filterPlatform, setFilterPlatform] = useState('전체')
  const [sortBy, setSortBy] = useState('time')
  const [userLocation, setUserLocation] = useState(null)
  const [searchTimeRange, setSearchTimeRange] = useState({ from: '06:00', to: '18:00' })
  // 카드에서 자동 조회된 최저가 오버라이드 (가격순 정렬용)
  const [priceOverrides, setPriceOverrides] = useState({})

  const platforms = [...new Set(results.map(r => r.platform))]

  // GPS 위치 요청
  useEffect(() => {
    if (!navigator.geolocation) return
    navigator.geolocation.getCurrentPosition(
      pos => setUserLocation({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
      () => setUserLocation(null),
      { timeout: 8000 }
    )
  }, [])

  function getDistance(item) {
    if (!userLocation) return 99999
    const coords = REGION_COORDS[item.region]
    if (!coords) return 99999
    return haversine(userLocation.lat, userLocation.lon, coords[0], coords[1])
  }

  // 카드가 자동 조회한 최저가를 받아 정렬에 반영
  const handlePriceLoaded = useCallback((platform, courseName, minPrice) => {
    const key = `${platform}::${courseName}`
    setPriceOverrides(prev => ({ ...prev, [key]: minPrice }))
  }, [])

  // 정렬용 실제 가격: 자동 조회값 우선, 없으면 item.price, 0이면 정렬 후미
  function effectivePrice(item) {
    const override = priceOverrides[`${item.platform}::${item.course_name}`]
    if (override) return override
    return item.price > 0 ? item.price : 999999999
  }

  // 플랫폼 필터 적용
  const filtered = results.filter(r => filterPlatform === '전체' || r.platform === filterPlatform)

  // 정규화된 코스명으로 그룹화 (플랫폼당 1개만 유지 — 슬롯 많은 것 우선)
  const groupMap = {}
  filtered.forEach(r => {
    const key = normalizeName(r.course_name)
    if (!groupMap[key]) groupMap[key] = {}
    const existing = groupMap[key][r.platform]
    if (!existing) {
      groupMap[key][r.platform] = r
    } else {
      // 같은 플랫폼 중복 시 슬롯 수 더 많은 것 유지
      const existingCnt = parseInt(existing.price_display) || 0
      const newCnt = parseInt(r.price_display) || 0
      if (newCnt > existingCnt) groupMap[key][r.platform] = r
    }
  })
  // { key: { platform: item } } → [ [item, ...], ... ]
  const flatGroups = Object.values(groupMap).map(byPlatform => Object.values(byPlatform))

  // 그룹별 정렬
  const groupedResults = flatGroups.sort((ga, gb) => {
    if (sortBy === 'time') {
      const ta = [...ga.map(r => r.tee_time || '99:99')].sort()[0]
      const tb = [...gb.map(r => r.tee_time || '99:99')].sort()[0]
      return ta.localeCompare(tb)
    }
    if (sortBy === 'price') {
      const pa = Math.min(...ga.map(r => effectivePrice(r)))
      const pb = Math.min(...gb.map(r => effectivePrice(r)))
      return pa - pb
    }
    if (sortBy === 'distance') return getDistance(ga[0]) - getDistance(gb[0])
    return 0
  })

  async function handleSearch(params) {
    setLoading(true)
    setSearched(false)
    setResults([])
    setErrors({})
    setFilterPlatform('전체')
    setPriceOverrides({})  // 새 검색 시 이전 오버라이드 초기화
    setSearchTimeRange({ from: params.time_from || '06:00', to: params.time_to || '18:00' })
    try {
      const { data } = await axios.post('/api/search', params)
      setResults(data.results || [])
      setErrors(data.errors || {})
    } catch (e) {
      setErrors({ 네트워크: '서버에 연결할 수 없습니다. run.bat으로 백엔드를 실행해주세요.' })
    } finally {
      setLoading(false)
      setSearched(true)
    }
  }

  return (
    <div className="min-h-screen bg-[#f4f6f4]">
      <Header />

      <main className="max-w-lg mx-auto px-4 pb-8 pt-2">
        <SearchForm onSearch={handleSearch} loading={loading} />

        {searched && (
          <div className="mt-4 slide-up">
            {/* 요약 */}
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm text-gray-500">
                {groupedResults.length > 0
                  ? <><span className="font-bold text-[#1a6b3c]">{groupedResults.length}개</span> 골프장</>
                  : '검색 결과가 없습니다'}
              </span>
              <div className="flex items-center gap-2">
                {userLocation && (
                  <span className="text-xs text-green-600">📍 위치 확인됨</span>
                )}
                {Object.keys(errors).length > 0 && (
                  <span className="text-xs text-red-400">
                    {Object.keys(errors).length}개 오류
                  </span>
                )}
              </div>
            </div>

            {/* 필터바 */}
            {results.length > 0 && (
              <FilterBar
                platforms={['전체', ...platforms]}
                active={filterPlatform}
                onPlatform={setFilterPlatform}
                sortBy={sortBy}
                onSort={setSortBy}
                gpsAvailable={!!userLocation}
              />
            )}


            {/* 오류 메시지 */}
            {Object.entries(errors).map(([name, msg]) => (
              <div key={name} className="mt-2 text-xs text-red-500 bg-red-50 rounded-xl px-4 py-2">
                <span className="font-semibold">{name}</span>: {msg}
              </div>
            ))}

            {/* 결과 목록 */}
            <ResultList
              groups={groupedResults}
              showDistance={sortBy === 'distance'}
              getDistance={getDistance}
              timeRange={searchTimeRange}
              onPriceLoaded={handlePriceLoaded}
            />
          </div>
        )}

        {loading && (
          <div className="mt-8 flex flex-col items-center gap-3">
            <div className="w-10 h-10 border-4 border-[#1a6b3c] border-t-transparent rounded-full spinner" />
            <p className="text-sm text-gray-500">플랫폼별 티타임을 불러오는 중...</p>
          </div>
        )}
      </main>
    </div>
  )
}
