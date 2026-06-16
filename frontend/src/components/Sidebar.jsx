import { LayoutGrid, FileText, Upload, BarChart2, Settings } from 'lucide-react'

const navItems = [
  { id: 'dash', icon: LayoutGrid, label: 'Dashboard' },
  { id: 'cases', icon: FileText, label: 'Case Detail', badge: true },
  { id: 'upload', icon: Upload, label: 'New Case' },
  { id: 'reports', icon: BarChart2, label: 'Reports' },
]

export default function Sidebar({ activeView, onNavigate }) {
  return (
    <nav className="w-[54px] bg-sheet border-r border-border flex flex-col items-center py-3 shrink-0">
      {/* Logo */}
      <div
        className="w-[30px] h-[30px] rounded-[7px] flex items-center justify-center text-white font-bold text-[11px] tracking-tighter mb-[22px] shrink-0 bg-indigo shadow-[0_2px_8px_rgba(79,70,229,0.22)] hover:shadow-[0_4px_12px_rgba(79,70,229,0.35)] transition-shadow duration-200 cursor-default"
      >
        Cx
      </div>

      {/* Nav group */}
      <div className="flex flex-col gap-[1px] w-full px-[7px] flex-1">
        {navItems.map(({ id, icon: Icon, label, badge }) => {
          const isActive = activeView === id
          return (
            <button
              key={id}
              onClick={() => onNavigate(id)}
              className={`w-10 h-10 rounded-lg flex items-center justify-center cursor-pointer border relative group
                transition-all duration-200 ease-in-out
                ${isActive
                  ? 'bg-[#EEF2FF] text-indigo border-[#C7D2FE] shadow-sm'
                  : 'text-text-silent border-transparent hover:bg-raised hover:text-text-dim active:scale-95'
                }`}
            >
              <Icon size={16} strokeWidth={1.8} />
              {badge && !isActive && (
                <span className="absolute top-[6px] right-[6px] w-[6px] h-[6px] rounded-full bg-alarm border border-sheet animate-pulse" />
              )}
              {/* Tooltip */}
              <span className="absolute left-[calc(100%+10px)] top-1/2 -translate-y-1/2 bg-sheet border border-border-strong
                shadow-[0_2px_8px_rgba(0,0,0,0.08)] text-text-secondary text-data-sm font-medium
                px-[9px] py-1 rounded-[5px] whitespace-nowrap pointer-events-none
                opacity-0 group-hover:opacity-100 transition-opacity duration-150 z-50">
                {label}
              </span>
            </button>
          )
        })}
      </div>

      {/* Settings at bottom */}
      <div className="px-[7px] pb-1">
        <button className="w-10 h-10 rounded-lg flex items-center justify-center cursor-pointer
          text-text-silent border border-transparent hover:bg-raised hover:text-text-dim
          transition-all duration-200 relative group active:scale-95">
          <Settings size={16} strokeWidth={1.8} />
          <span className="absolute left-[calc(100%+10px)] top-1/2 -translate-y-1/2 bg-sheet border border-border-strong
            shadow-[0_2px_8px_rgba(0,0,0,0.08)] text-text-secondary text-data-sm font-medium
            px-[9px] py-1 rounded-[5px] whitespace-nowrap pointer-events-none
            opacity-0 group-hover:opacity-100 transition-opacity duration-150 z-50">
            Settings
          </span>
        </button>
      </div>
    </nav>
  )
}
