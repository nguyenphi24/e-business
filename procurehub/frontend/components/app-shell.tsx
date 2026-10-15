import { Link, useLocation, useNavigate } from "react-router-dom";
import { AppstoreOutlined, AuditOutlined, FileTextOutlined, LogoutOutlined, ShoppingCartOutlined, SwapOutlined } from "@ant-design/icons";

import NotificationBell from "@/components/notification-bell";
import { getStoredUser, hasRole, logout } from "@/lib/api";

// Menu theo vai trò chỉ để dễ dùng; backend vẫn kiểm tra quyền.
const links = [
  { href: "/dashboard", label: "Tổng quan", icon: <AppstoreOutlined />, roles: [] as string[] },
  { href: "/purchase-requests", label: "Purchase Requests", icon: <FileTextOutlined />, roles: ["BUYER", "MANAGER", "COMPANY_ADMIN", "SYSTEM_ADMIN"] },
  { href: "/rfqs", label: "RFQ & báo giá", icon: <SwapOutlined />, roles: ["BUYER", "MANAGER", "SUPPLIER", "COMPANY_ADMIN", "SYSTEM_ADMIN"] },
  { href: "/purchase-orders", label: "Purchase Orders", icon: <ShoppingCartOutlined />, roles: ["BUYER", "MANAGER", "SUPPLIER", "FINANCE", "COMPANY_ADMIN", "SYSTEM_ADMIN"] },
  { href: "/invoices", label: "Hóa đơn & thanh toán", icon: <AuditOutlined />, roles: ["BUYER", "MANAGER", "SUPPLIER", "FINANCE", "COMPANY_ADMIN", "SYSTEM_ADMIN"] },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const user = getStoredUser();

  function handleLogout() {
    void logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <Link className="brand-mark" to="/dashboard"><i className="brand-dot" /><span>ProcureHub</span></Link>
        <div className="sidebar-label">Workspace</div>
        {links.filter((link) => link.roles.length === 0 || hasRole(user, ...link.roles)).map((link) => (
          <Link className={`sidebar-link ${pathname === link.href ? "active" : ""}`} to={link.href} key={link.href} title={link.label}>
            {link.icon}<span>{link.label}</span>
          </Link>
        ))}
        <div className="sidebar-label">Hệ thống</div>
        {user && <NotificationBell />}
        <button className="sidebar-link" onClick={handleLogout} type="button" title="Đăng xuất"><LogoutOutlined /><span>Đăng xuất</span></button>
        <div className="sidebar-spacer" />
        <div className="sidebar-user">
          <strong>{user?.full_name ?? "ProcureHub user"}</strong>
          <span>{user?.roles?.join(" · ") ?? ""}</span>
        </div>
      </aside>
      <main className="app-main">{children}</main>
    </div>
  );
}
