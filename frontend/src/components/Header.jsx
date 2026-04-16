export default function Header() {
  return (
    <header className="bg-[#1a6b3c] text-white px-4 py-4 shadow-md sticky top-0 z-50">
      <div className="max-w-lg mx-auto flex items-center gap-2">
        <span className="text-2xl">⛳</span>
        <div>
          <h1 className="font-bold text-lg leading-tight">골프 통합예약 검색</h1>
          <p className="text-green-200 text-xs">티스캐너 · 카카오골프 · 티업앤조이 외</p>
        </div>
      </div>
    </header>
  )
}
