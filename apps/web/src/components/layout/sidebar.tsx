import { Link, useLocation } from '@tanstack/react-router'
import { useActiveWorkspace } from '../../features/workspaces/hooks/use-active-workspace'

const NAV_ITEMS = [
  { to: '/chat', label: 'Chat', icon: '💬' },
  { to: '/visualization-data', label: 'Visualization Data', icon: '📊' },
  { to: '/source-data', label: 'Source Data', icon: '📁' },
]

export function Sidebar() {
  const location = useLocation()
  const { activeWorkspace } = useActiveWorkspace()

  return (
    <aside className="flex flex-col w-56 bg-[#F4F2FA] border-r border-[#E5E2F0] min-h-screen">
      {/* Brand */}
      <div className="px-5 py-6 border-b border-[#E5E2F0]">
        <h1 className="text-lg font-semibold text-[#151826] tracking-tight">Company Intelligence</h1>
      </div>

      {/* Active Workspace Indicator */}
      {activeWorkspace && (
        <div className="px-4 py-3 border-b border-[#E5E2F0]">
          <span className="text-xs font-medium text-[#626A7C] uppercase tracking-wider">Workspace</span>
          <p className="text-sm font-semibold text-[#151826] mt-0.5">{activeWorkspace.name}</p>
        </div>
      )}

      {/* Nav */}
      <nav className="flex-1 px-3 py-4">
        <ul className="space-y-1">
          {NAV_ITEMS.map((item) => {
            const isActive = location.pathname === item.to
            return (
              <li key={item.to}>
                <Link
                  to={item.to}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive ? 'bg-[#4F46E5] text-white' : 'text-[#626A7C] hover:bg-[#E4E1EE] hover:text-[#151826]'
                  }`}
                >
                  <span>{item.icon}</span>
                  {item.label}
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>

      {/* Secondary items */}
      <div className="px-3 py-4 border-t border-[#E5E2F0]">
        <ul className="space-y-1">
          <li>
            <button
              type="button"
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-[#626A7C] hover:bg-[#E4E1EE] hover:text-[#151826] transition-colors"
            >
              <span>❓</span> Help
            </button>
          </li>
          <li>
            <button
              type="button"
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-[#626A7C] hover:bg-[#E4E1EE] hover:text-[#151826] transition-colors"
            >
              <span>⚙️</span> Settings
            </button>
          </li>
        </ul>
      </div>
    </aside>
  )
}
