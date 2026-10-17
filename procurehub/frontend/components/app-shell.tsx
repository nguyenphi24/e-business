import { Input, Popover, Tag } from "antd";
import {
  AuditOutlined,
  CreditCardOutlined,
  DownOutlined,
  FileTextOutlined,
  HomeFilled,
  LogoutOutlined,
  SearchOutlined,
  ShoppingOutlined,
} from "@ant-design/icons";
import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import NotificationBell from "@/components/notification-bell";
import { getStoredUser, hasRole, logout } from "@/lib/api";

export const roleLabels: Record<string, string> = {
  BUYER: "Chuyên viên mua hàng",
  MANAGER: "Trưởng phòng phê duyệt",
  FINANCE: "Kế toán thanh toán",
  SUPPLIER: "Nhà cung cấp",
  COMPANY_ADMIN: "Quản trị doanh nghiệp",
  SYSTEM_ADMIN: "Quản trị hệ thống",
};

// Menu theo vai trò chỉ để dễ dùng; backend vẫn kiểm tra quyền.
const links = [
  { href: "/dashboard", label: "Tổng quan", sub: "Bảng điều khiển & KPI", icon: <HomeFilled />, roles: [] as string[] },
  {
    href: "/purchase-requests",
    label: "Yêu cầu mua hàng",
    sub: "Tạo & duyệt đề nghị mua sắm",
    icon: <FileTextOutlined />,
    roles: ["BUYER", "MANAGER", "COMPANY_ADMIN", "SYSTEM_ADMIN"],
  },
  {
    href: "/rfqs",
    label: "Mời báo giá (RFQ)",
    sub: "Mời thầu, chấm điểm & ký số",
    icon: <AuditOutlined />,
    roles: ["BUYER", "MANAGER", "SUPPLIER", "COMPANY_ADMIN", "SYSTEM_ADMIN"],
  },
  {
    href: "/purchase-orders",
    label: "Đơn đặt hàng (PO)",
    sub: "Phát hành đơn & giao nhận",
    icon: <ShoppingOutlined />,
    roles: ["BUYER", "MANAGER", "SUPPLIER", "FINANCE", "COMPANY_ADMIN", "SYSTEM_ADMIN"],
  },
  {
    href: "/invoices",
    label: "Hóa đơn & Thanh toán",
    sub: "HĐĐT, mã CQT & thanh toán",
    icon: <CreditCardOutlined />,
    roles: ["BUYER", "MANAGER", "SUPPLIER", "FINANCE", "COMPANY_ADMIN", "SYSTEM_ADMIN"],
  },
];

export function CloverLogo() {
  return (
    <span className="fin-logo-circle" aria-hidden="true">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="5.5" r="3.2" fill="#FFFFFF" />
        <circle cx="12" cy="18.5" r="3.2" fill="#FFFFFF" />
        <circle cx="5.5" cy="12" r="3.2" fill="#FFFFFF" />
        <circle cx="18.5" cy="12" r="3.2" fill="#FFFFFF" />
      </svg>
    </span>
  );
}

function getInitials(name?: string) {
  if (!name) return "PH";
  const cleanName = name.replace(/\(.*?\)/g, "").trim();
  const parts = cleanName.split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "PH";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

function formatDisplayName(name?: string) {
  if (!name) return "Người dùng ProcureHub";
  return name.replace(/\s*\(.*?\)\s*/g, "").trim() || name;
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const user = getStoredUser();
  const [query, setQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);

  const visibleLinks = links.filter((link) => link.roles.length === 0 || hasRole(user, ...link.roles));
  const filteredLinks = visibleLinks.filter(
    (item) =>
      item.label.toLowerCase().includes(query.toLowerCase()) ||
      item.sub.toLowerCase().includes(query.toLowerCase())
  );

  function handleLogout() {
    void logout();
    navigate("/login", { replace: true });
  }

  const searchPopover = (
    <div className="fin-search-popover">
      <Input
        prefix={<SearchOutlined style={{ color: "#7C8498" }} />}
        placeholder="Tìm nhanh phân hệ (Yêu cầu, RFQ, Đơn hàng, Hóa đơn)..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        allowClear
      />
      <div className="fin-search-results">
        {filteredLinks.map((item) => (
          <button
            key={item.href}
            type="button"
            className="fin-search-item"
            onClick={() => {
              setSearchOpen(false);
              navigate(item.href);
            }}
          >
            <span className="fin-search-item-icon">{item.icon}</span>
            <span className="fin-search-item-text">
              <strong>{item.label}</strong>
              <small>{item.sub}</small>
            </span>
          </button>
        ))}
      </div>
    </div>
  );

  const profilePopover = (
    <div className="fin-profile-popover">
      <div className="fin-profile-head">
        <div className="fin-avatar fin-avatar-lg">{getInitials(user?.full_name)}</div>
        <div className="fin-profile-head-info">
          <strong>{user?.full_name ?? "Người dùng ProcureHub"}</strong>
          <span>{user?.email ?? ""}</span>
        </div>
      </div>
      <div className="fin-profile-meta">
        <div className="fin-profile-meta-row">
          <small>Đơn vị / Doanh nghiệp</small>
          <strong>{user?.company?.legal_name ?? "Quản trị hệ thống"}</strong>
        </div>
        <div className="fin-profile-meta-row">
          <small>Vai trò trên hệ thống</small>
          <div className="fin-role-tags">
            {(user?.roles ?? []).map((role) => (
              <Tag key={role} color="blue" style={{ margin: 0 }}>
                {roleLabels[role] ?? role}
              </Tag>
            ))}
          </div>
        </div>
      </div>
      <button type="button" className="fin-logout-btn" onClick={handleLogout}>
        <LogoutOutlined /> Đăng xuất tài khoản
      </button>
    </div>
  );

  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <Link className="brand-mark" to="/dashboard" title="ProcureHub — Mua sắm & Tài chính B2B">
          <CloverLogo />
          <div className="brand-text">
            <strong>ProcureHub</strong>
            <span>Mua sắm &amp; Tài chính</span>
          </div>
        </Link>

        <nav className="sidebar-nav" aria-label="Điều hướng chính">
          {visibleLinks.map((link) => {
            const active = pathname === link.href;
            return (
              <Link
                className={`sidebar-link ${active ? "active" : ""}`}
                to={link.href}
                key={link.href}
                title={link.label}
              >
                <span className="sidebar-icon-box">{link.icon}</span>
                <span className="sidebar-link-text">{link.label}</span>
              </Link>
            );
          })}
        </nav>

      </aside>

      <main className="app-main">
        <header className="fin-header">
          <div className="fin-greeting-wrap">
            <div className="fin-greeting">
              <span className="fin-hi">Xin chào,</span>{" "}
              <strong className="fin-user-name">{formatDisplayName(user?.full_name)}</strong>
            </div>
            <p className="fin-greeting-sub">
              Theo dõi tiến độ yêu cầu mua sắm, báo giá nhà cung cấp, đơn đặt hàng và đối soát thanh toán của đơn vị bạn.
            </p>
          </div>

          <div className="fin-header-actions">
            <Popover
              content={searchPopover}
              trigger="click"
              placement="bottomRight"
              open={searchOpen}
              onOpenChange={setSearchOpen}
            >
              <button className="fin-icon-btn" type="button" title="Tìm kiếm nhanh phân hệ" aria-label="Tìm kiếm">
                <SearchOutlined style={{ fontSize: 17, color: "#14172C" }} />
              </button>
            </Popover>

            {user && <NotificationBell variant="header" />}

            <Popover content={profilePopover} trigger="click" placement="bottomRight">
              <button className="fin-profile-trigger" type="button" title="Thông tin tài khoản & Đăng xuất">
                <span className="fin-avatar">{getInitials(user?.full_name)}</span>
                <span className="fin-profile-name">{formatDisplayName(user?.full_name)}</span>
                <DownOutlined className="fin-profile-chevron" />
              </button>
            </Popover>
          </div>
        </header>

        {children}
      </main>
    </div>
  );
}
