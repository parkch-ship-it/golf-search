const PLATFORM_COLORS = {
  '티스캐너':    'bg-blue-100 text-blue-700',
  '카카오골프':  'bg-yellow-100 text-yellow-700',
  '티업앤조이':  'bg-purple-100 text-purple-700',
  '스마트스코어':'bg-orange-100 text-orange-700',
  '골프존카운티':'bg-teal-100 text-teal-700',
  '전체':        'bg-gray-100 text-gray-700',
}

export default function FilterBar({ platforms, active, onPlatform, sortBy, onSort, gpsAvailable }) {
  return (
    <div className="mb-3 space-y-2">
      {/* 플랫폼 필터 */}
      <div className="flex gap-1.5 overflow-x-auto pb-1">
        {platforms.map(p => (
          <button
            key={p}
            onClick={() => onPlatform(p)}
            className={`flex-shrink-0 text-xs px-3 py-1.5 rounded-full font-medium transition-colors
              ${active === p
                ? 'bg-[#1a6b3c] text-white'
                : (PLATFORM_COLORS[p] || 'bg-gray-100 text-gray-600')}`}
          >
            {p}
          </button>
        ))}
      </div>

      {/* 정렬 */}
      <div className="flex gap-2 items-center">
        <span className="text-xs text-gray-400 flex-shrink-0">정렬:</span>
        {[
          { value: 'time',     label: '시간순' },
          { value: 'price',    label: '가격순' },
          { value: 'distance', label: '거리순', disabled: !gpsAvailable },
        ].map(({ value, label, disabled }) => (
          <button
            key={value}
            onClick={() => !disabled && onSort(value)}
            disabled={disabled}
            title={disabled ? 'GPS 권한을 허용하면 사용할 수 있습니다' : ''}
            className={`text-xs px-3 py-1 rounded-full border transition-colors
              ${sortBy === value
                ? 'border-[#1a6b3c] text-[#1a6b3c] font-semibold'
                : disabled
                  ? 'border-gray-100 text-gray-300 cursor-not-allowed'
                  : 'border-gray-200 text-gray-500'}`}
          >
            {label}
            {value === 'distance' && !gpsAvailable && (
              <span className="ml-1 text-gray-300">🔒</span>
            )}
          </button>
        ))}
      </div>
    </div>
  )
}
