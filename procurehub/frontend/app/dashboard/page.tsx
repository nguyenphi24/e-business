"use client";

import { Alert, Button, Skeleton, Tag } from "antd";
import { CheckCircleOutlined, ClockCircleOutlined, FileSearchOutlined, ReloadOutlined } from "@ant-design/icons";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import AppShell from "@/components/app-shell";
import { apiFetch, DashboardData, formatMoney, getStoredUser, hasRole, Kpi } from "@/lib/api";

const statusLabels: Record<string, string> = {
  DRAFT: "Nháp", PENDING_APPROVAL: "Chờ duyệt", APPROVED: "Đã duyệt", OPEN: "Đang mở", SUBMITTED: "Đã gửi",
  PROPOSED: "Đề xuất", ISSUED: "Đã phát hành", ACKNOWLEDGED: "Đã xác nhận", COMPLETED: "Hoàn tất",
  PARTIALLY_PAID: "Trả một phần", DELIVERED: "Đã giao",
};

const kpiLabels: Array<[string, string]> = [
  ["approval_lead_time_hours", "Thời gian duyệt PR"],
  ["rfq_response_time_hours", "Thời gian phản hồi RFQ"],
  ["quote_participation_rate", "Tỷ lệ NCC báo giá"],
  ["procurement_cycle_time_days", "Chu trình PR → PO"],
  ["on_time_delivery_rate", "Giao đúng hạn"],
  ["estimated_savings", "Tiết kiệm so với ngân sách"],
];

function formatKpi(kpi: Kpi) {
  if (kpi.value === null) return "—";
  if (kpi.unit === "ratio") return `${(Number(kpi.value) * 100).toFixed(0)}%`;
  if (kpi.unit === "hours") return `${kpi.value} giờ`;
  if (kpi.unit === "days") return `${kpi.value} ngày`;
  if (kpi.unit === "currency") return formatMoney(kpi.value) + (kpi.rate !== null && kpi.rate !== undefined ? ` (${(kpi.rate * 100).toFixed(1)}%)` : "");
  return String(kpi.value);
}

function formatTime(value: string) { return new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)); }
function displayAction(action: string) { return action.replaceAll("_", " ").toLowerCase().replace(/^./, (char) => char.toUpperCase()); }

export default function DashboardPage() {
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setError(null);
    try { setData(await apiFetch<DashboardData>("/dashboard")); }
    catch (err) { if (getStoredUser() === null) navigate("/login", { replace: true }); else setError(err instanceof Error ? err.message : "Không tải được dashboard."); }
    finally { setLoading(false); }
  }

  useEffect(() => { if (getStoredUser() === null) navigate("/login", { replace: true }); else void load(); }, [navigate]);

  const user = getStoredUser();
  const invoiceCards: Array<[string, number | string]> = [
    ["Hóa đơn chờ trả", (data?.counts.invoices?.ISSUED ?? 0) + (data?.counts.invoices?.PARTIALLY_PAID ?? 0)],
    ["Hóa đơn quá hạn", data?.receivables?.overdue_count ?? 0],
    ["Công nợ còn lại", formatMoney(data?.receivables?.open_balance)],
  ];
  const cards: Array<[string, number | string]> = hasRole(user, "FINANCE") ? [
    ...invoiceCards,
    ["Hóa đơn đã trả", data?.counts.invoices?.PAID ?? 0],
    ["PO hoàn tất", data?.counts.purchase_orders?.COMPLETED ?? 0],
  ] : hasRole(user, "SUPPLIER") ? [
    ["RFQ đang mở", data?.counts.rfqs?.OPEN ?? 0],
    ["PO chờ xác nhận", data?.counts.purchase_orders?.ISSUED ?? 0],
    ["PO đã giao", (data?.counts.purchase_orders?.DELIVERED ?? 0) + (data?.counts.purchase_orders?.COMPLETED ?? 0)],
    ...invoiceCards.slice(0, 1),
    ["Phải thu còn lại", formatMoney(data?.receivables?.open_balance)],
  ] : [
    ["PR nháp", data?.counts.purchase_requests?.DRAFT ?? 0],
    ["PR chờ duyệt", data?.counts.purchase_requests?.PENDING_APPROVAL ?? 0],
    ["RFQ đang mở", data?.counts.rfqs?.OPEN ?? 0],
    ["PO đã phát hành", data?.counts.purchase_orders?.ISSUED ?? 0],
    ["PO hoàn tất", data?.counts.purchase_orders?.COMPLETED ?? 0],
  ];

  return <AppShell>
    <div className="topbar">
      <div><p className="eyebrow">ProcureHub workspace</p><h1 className="page-title">Tổng quan</h1><p className="page-subtitle">Theo dõi việc cần xử lý trong chuỗi Source-to-Pay (thanh toán ở chế độ sandbox).</p></div>
      <Button icon={<ReloadOutlined />} onClick={() => void load()}>Làm mới</Button>
    </div>
    {error && <Alert message={error} type="error" showIcon style={{ marginBottom: 20 }} />}
    {loading && !data ? <Skeleton active paragraph={{ rows: 8 }} /> : data && <>
      <div className="stats-grid">{cards.map(([label, value]) => <div className="stat-card" key={label}><div className="stat-label">{label}</div><div className={`stat-value ${typeof value === "string" ? "compact" : ""}`}>{value}</div></div>)}</div>
      {data.kpis && <section className="panel" style={{ marginBottom: 22 }}><div className="panel-heading"><h2>KPI mua sắm</h2><span>Trung vị; n = cỡ mẫu. Số liệu demo là dữ liệu seed.</span></div><div className="kpi-grid">
        {kpiLabels.map(([key, label]) => { const kpi = data.kpis?.[key]; return kpi ? <div className="kpi-card" key={key} title={kpi.definition}><div className="stat-label">{label}</div><div className="stat-value">{formatKpi(kpi)}</div><div className="kpi-note">n = {kpi.n} · {kpi.definition}</div></div> : null; })}
      </div></section>}
      <div className="content-grid">
        <div>
          <section className="panel"><div className="panel-heading"><h2>Hoạt động gần đây</h2><span>20 sự kiện mới nhất</span></div><div className="activity-list">
            {data.recent_activity.length === 0 ? <div className="empty-state">Chưa có hoạt động.</div> : data.recent_activity.map((item) => <div className="activity-item" key={item.id}><div className="activity-icon"><CheckCircleOutlined /></div><div className="item-main"><strong>{displayAction(item.action)}</strong><span>{item.entity_type} · {item.entity_id.slice(0, 8)}…</span></div><div className="item-time">{formatTime(item.occurred_at)}</div></div>)}
          </div></section>
        </div>
        <div>
          <section className="panel"><div className="panel-heading"><h2>Việc cần xử lý</h2><span>{data.pending_count} việc</span></div><div className="pending-list">
            {data.pending_actions.length === 0 ? <div className="empty-state">Không có việc tồn đọng.</div> : data.pending_actions.map((item) => <div className="pending-item" key={`${item.type}-${item.id}`}><div className="activity-icon"><ClockCircleOutlined /></div><div className="item-main"><strong>{item.label}</strong><span>{item.number}</span></div><Tag color={item.status === "PENDING_APPROVAL" || item.status === "PROPOSED" ? "orange" : "blue"}>{statusLabels[item.status] ?? item.status}</Tag></div>)}
          </div></section>
          <section className="panel"><div className="panel-heading"><h2>Lối tắt</h2></div><Button block icon={<FileSearchOutlined />} onClick={() => navigate("/purchase-requests")}>Xem Purchase Requests</Button></section>
        </div>
      </div>
    </>}
  </AppShell>;
}
