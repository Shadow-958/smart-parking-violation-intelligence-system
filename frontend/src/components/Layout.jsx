import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", staffOnly: false },
  { to: "/submit", label: "Submit Complaint", staffOnly: false },
  { to: "/complaints", label: "Complaints", staffOnly: false },
  { to: "/map", label: "Map View", staffOnly: false },
  { to: "/hotspots", label: "Hotspot Analysis", staffOnly: false },
  { to: "/predictions", label: "AI Predictions", staffOnly: false },
  { to: "/reports", label: "Reports", staffOnly: true },
];

export default function Layout() {
  const { currentUser, isStaff, logout } = useAuth();

  return (
    <div className="flex min-h-screen">
      <aside className="flex w-60 shrink-0 flex-col bg-asphalt text-paper">
        <div className="border-b border-white/10 px-5 py-6">
          <div className="font-display text-lg leading-tight tracking-wide">
            Parking
            <br />
            Violation
            <br />
            Intelligence
          </div>
        </div>

        <nav className="flex-1 px-2 py-4">
          {NAV_ITEMS.filter((item) => !item.staffOnly || isStaff).map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `block px-3 py-2 font-display text-sm uppercase tracking-wide ${
                  isActive ? "bg-curb-yellow text-asphalt-dark" : "text-paper/80 hover:bg-white/10"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-white/10 px-5 py-4 text-sm">
          <div className="font-mono text-xs text-paper/50">Signed in as</div>
          <div className="truncate">{currentUser?.username}</div>
          <div className="font-mono text-xs uppercase text-paper/50">{currentUser?.role}</div>
          <button
            onClick={logout}
            className="mt-3 w-full border border-white/20 py-1.5 text-xs uppercase tracking-wide text-paper/80 hover:bg-white/10"
          >
            Log out
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
