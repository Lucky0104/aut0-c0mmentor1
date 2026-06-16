import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import {
  ChartBar, ChatCircleDots, CheckSquare, Users, BookOpen,
  TrendUp, FacebookLogo, GearSix, SignOut, CaretDown
} from "@phosphor-icons/react";
import { useState } from "react";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: ChartBar, tid: "nav-dashboard" },
  { to: "/pages", label: "Pages & IG", icon: FacebookLogo, tid: "nav-pages" },
  { to: "/comments", label: "Comments", icon: ChatCircleDots, tid: "nav-comments" },
  { to: "/approvals", label: "Approvals", icon: CheckSquare, tid: "nav-approvals" },
  { to: "/leads", label: "Leads", icon: TrendUp, tid: "nav-leads" },
  { to: "/knowledge", label: "Knowledge Base", icon: BookOpen, tid: "nav-kb" },
  { to: "/team", label: "Team", icon: Users, tid: "nav-team" },
  { to: "/analytics", label: "Analytics", icon: ChartBar, tid: "nav-analytics" },
  { to: "/settings", label: "Settings", icon: GearSix, tid: "nav-settings" },
];

export default function AppShell({ children }) {
  const { me, activeTenant, switchTenant, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex bg-white text-foreground">
      {/* Sidebar */}
      <aside className="w-64 shrink-0 border-r border-border bg-white flex flex-col">
        <div className="p-5 border-b border-border">
          <div className="overline text-muted-foreground">Platform</div>
          <div className="mt-1 text-lg font-black tracking-tight" style={{ fontFamily: "Chivo, sans-serif" }}>
            DASH·AI
          </div>
          <div className="text-xs text-muted-foreground mt-0.5">Comment Intelligence</div>
        </div>

        {/* Workspace switcher */}
        <div className="p-3 border-b border-border relative">
          <button
            data-testid="workspace-switcher-button"
            onClick={() => setOpen((o) => !o)}
            className="w-full flex items-center justify-between border border-border px-3 py-2 hover:border-foreground transition"
          >
            <div className="text-left">
              <div className="overline text-muted-foreground">Workspace</div>
              <div className="text-sm font-semibold truncate">{activeTenant?.business_name || "—"}</div>
            </div>
            <CaretDown size={14} />
          </button>
          {open && (
            <div data-testid="workspace-dropdown" className="absolute z-20 left-3 right-3 mt-1 bg-white border border-border shadow-lg">
              {me?.tenants?.map((t) => (
                <button
                  key={t.id}
                  data-testid={`workspace-option-${t.id}`}
                  onClick={async () => { setOpen(false); await switchTenant(t.id); navigate("/dashboard"); }}
                  className="w-full text-left px-3 py-2 text-sm hover:bg-secondary hover:text-foreground border-b border-border last:border-0"
                >
                  <div className="font-medium">{t.business_name}</div>
                  <div className="overline text-muted-foreground">{t.role}</div>
                </button>
              ))}
            </div>
          )}
        </div>

        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {navItems.map((it) => (
            <NavLink
              key={it.to}
              to={it.to}
              data-testid={it.tid}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 text-sm transition border-l-2 ${
                  isActive
                    ? "border-primary bg-secondary text-foreground font-semibold"
                    : "border-transparent text-muted-foreground hover:text-foreground hover:bg-secondary"
                }`
              }
            >
              <it.icon size={16} weight="bold" />
              <span>{it.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-border p-3 flex items-center gap-3">
          {me?.user?.picture ? (
            <img src={me.user.picture} alt="" className="w-9 h-9 rounded-sm border border-border" />
          ) : (
            <div className="w-9 h-9 bg-secondary border border-border flex items-center justify-center text-xs font-bold">
              {me?.user?.name?.[0]?.toUpperCase() || "U"}
            </div>
          )}
          <div className="flex-1 min-w-0">
            <div className="text-sm font-semibold truncate">{me?.user?.name}</div>
            <div className="text-xs text-muted-foreground truncate">{me?.user?.email}</div>
          </div>
          <button data-testid="logout-button" onClick={logout} className="p-1.5 hover:bg-secondary border border-border" title="Logout">
            <SignOut size={14} />
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 min-w-0 overflow-x-auto">{children}</main>
    </div>
  );
}
