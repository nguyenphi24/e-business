"use client";

import { Alert, Button, Skeleton, Tag } from "antd";
import {
  ArrowRightOutlined,
  AuditOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  DollarOutlined,
  FileProtectOutlined,
  FileTextOutlined,
  ReloadOutlined,
  ShoppingOutlined,
} from "@ant-design/icons";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import AppShell from "@/components/app-shell";
import {
  apiFetch,
  ApiList,
  DashboardData,
  formatMoney,
  getStoredUser,
  hasRole,
  Invoice,
  Kpi,
  PurchaseOrder,
} from "@/lib/api";

const statusLabels: Record<string, string> = {
  DRAFT: "Nháp",
  PENDING_APPROVAL: "Chờ duyệt",
  APPROVED: "Đã duyệt",
  OPEN: "Đang mở",
  SUBMITTED: "Đã gửi",
  PROPOSED: "Đề xuất",
  ISSUED: "Đã phát hành",
  ACKNOWLEDGED: "Đã xác nhận",
  COMPLETED: "Hoàn tất",
  PARTIALLY_PAID: "Trả một phần",
  DELIVERED: "Đã giao",
  PAID: "Đã thanh toán",
};

const actionLabels: Record<string, string> = {
  PR_CREATED: "Tạo mới yêu cầu mua hàng",
  PR_UPDATED: "Cập nhật yêu cầu mua hàng",
  PR_SUBMITTED: "Gửi duyệt yêu cầu mua hàng",
  PR_APPROVED: "Phê duyệt yêu cầu mua hàng",
  PR_REJECTED: "Từ chối yêu cầu mua hàng",
  PR_CANCELLED: "Hủy yêu cầu mua hàng",
  RFQ_CREATED: "Khởi tạo hồ sơ mời báo giá (RFQ)",
  RFQ_PUBLISHED: "Phát hành hồ sơ mời báo giá (RFQ)",
  RFQ_CLOSED: "Đóng nhận báo giá RFQ",
  RFQ_CANCELLED: "Hủy hồ sơ mời báo giá (RFQ)",
  RFQ_WEIGHTS_UPDATED: "Cập nhật trọng số chấm điểm RFQ",
  RFQ_INVITATION_VIEWED: "Nhà cung cấp đã xem lời mời báo giá",
  RFQ_INVITATION_ACCEPTED: "Nhà cung cấp xác nhận tham gia báo giá",
  RFQ_INVITATION_DECLINED: "Nhà cung cấp từ chối lời mời báo giá",
  QUOTATION_CREATED: "Tạo bản nháp báo giá",
  QUOTATION_SUBMITTED: "Nhà cung cấp gửi báo giá chính thức",
  QUOTATION_SIGN_REQUESTED: "Khởi tạo yêu cầu ký số báo giá",
  QUOTATION_SIGNED: "Ký số báo giá thành công",
  SELECTION_PROPOSED: "Đề xuất lựa chọn nhà cung cấp",
  SELECTION_APPROVED: "Phê duyệt lựa chọn nhà cung cấp",
  SELECTION_REJECTED: "Từ chối đề xuất chọn nhà cung cấp",
  PO_GENERATED: "Tạo đơn đặt hàng (PO) từ báo giá",
  PO_ISSUED: "Phát hành đơn đặt hàng (PO)",
  PO_ACKNOWLEDGED: "Nhà cung cấp xác nhận đơn hàng (PO)",
  PO_DECLINED: "Nhà cung cấp từ chối đơn hàng (PO)",
  PO_DELIVERED: "Ghi nhận giao nhận hàng hóa",
  PO_COMPLETED: "Nghiệm thu & hoàn tất đơn đặt hàng (PO)",
  PO_CANCELLED: "Hủy đơn đặt hàng (PO)",
  PO_EVALUATED: "Đánh giá chất lượng nhà cung cấp",
  INVOICE_ISSUED: "Nhà cung cấp phát hành hóa đơn",
  INVOICE_CANCELLED: "Hủy hóa đơn",
  EINVOICE_REQUESTED: "Gửi phát hành hóa đơn điện tử",
  EINVOICE_ISSUED: "Cơ quan thuế cấp mã hóa đơn điện tử",
  PAYMENT_INITIATED: "Khởi tạo giao dịch thanh toán",
  PAYMENT_SUCCEEDED: "Thanh toán hóa đơn thành công (IPN)",
  PAYMENT_FAILED: "Giao dịch thanh toán thất bại",
};

const entityTypeLabels: Record<string, string> = {
  PurchaseRequest: "Yêu cầu mua hàng",
  RFQ: "Hồ sơ RFQ",
  Quotation: "Báo giá",
  SupplierSelection: "Lựa chọn NCC",
  PurchaseOrder: "Đơn đặt hàng (PO)",
  Invoice: "Hóa đơn",
  Payment: "Thanh toán",
  SupplierEvaluation: "Đánh giá NCC",
};

const kpiLabels: Array<[string, string, string]> = [
  ["approval_lead_time_hours", "Thời gian duyệt yêu cầu (PR)", "blue"],
  ["rfq_response_time_hours", "Thời gian phản hồi báo giá (RFQ)", "pink"],
  ["quote_participation_rate", "Tỷ lệ nhà cung cấp báo giá", "gold"],
  ["procurement_cycle_time_days", "Chu kỳ mua sắm (PR → PO)", "blue"],
  ["on_time_delivery_rate", "Tỷ lệ giao hàng đúng hạn", "pink"],
  ["estimated_savings", "Tiết kiệm so với ngân sách", "gold"],
];

function formatKpi(kpi: Kpi) {
  if (kpi.value === null || kpi.value === undefined) return "—";
  if (kpi.unit === "ratio") return `${(Number(kpi.value) * 100).toFixed(0)}%`;
  if (kpi.unit === "hours") return `${kpi.value} giờ`;
  if (kpi.unit === "days") return `${kpi.value} ngày`;
  if (kpi.unit === "currency")
    return (
      formatMoney(kpi.value) +
      (kpi.rate !== null && kpi.rate !== undefined ? ` (${(kpi.rate * 100).toFixed(1)}%)` : "")
    );
  return String(kpi.value);
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function displayAction(action: string) {
  if (actionLabels[action]) return actionLabels[action];
  return action
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/^./, (char) => char.toUpperCase());
}

function displayEntityType(entityType: string) {
  return entityTypeLabels[entityType] ?? entityType;
}

function displayPendingLabel(label: string) {
  return label.replace("Purchase Request", "Yêu cầu mua hàng");
}

function pendingActionPath(type: string): string {
  if (type.startsWith("PR_")) return "/purchase-requests";
  if (type.startsWith("RFQ_") || type.startsWith("SELECTION_")) return "/rfqs";
  if (type === "INVOICE_PAYMENT") return "/invoices";
  return "/purchase-orders";
}

function sumValues(record?: Record<string, number>): number {
  if (!record) return 0;
  return Object.values(record).reduce((acc, v) => acc + (Number(v) || 0), 0);
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardData | null>(null);
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [dashboardRes, ordersRes, invoicesRes] = await Promise.all([
        apiFetch<DashboardData>("/dashboard"),
        apiFetch<ApiList<PurchaseOrder> | PurchaseOrder[]>("/purchase-orders").catch(() => [] as PurchaseOrder[]),
        apiFetch<ApiList<Invoice> | Invoice[]>("/invoices").catch(() => [] as Invoice[]),
      ]);
      setData(dashboardRes);
      setOrders(Array.isArray(ordersRes) ? ordersRes : ordersRes.results ?? []);
      setInvoices(Array.isArray(invoicesRes) ? invoicesRes : invoicesRes.results ?? []);
    } catch (err) {
      if (getStoredUser() === null) navigate("/login", { replace: true });
      else setError(err instanceof Error ? err.message : "Không tải được dữ liệu tổng quan.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (getStoredUser() === null) navigate("/login", { replace: true });
    else void load();
  }, [navigate]);

  const user = getStoredUser();
  const isSupplier = hasRole(user, "SUPPLIER");

  // --- TÍNH TOÁN 100% TỪ DỮ LIỆU THỰC TẾ ---
  const prCounts = data?.counts.purchase_requests ?? {};
  const rfqCounts = data?.counts.rfqs ?? {};
  const poCounts = data?.counts.purchase_orders ?? {};
  const invCounts = data?.counts.invoices ?? {};

  const totalPRs = sumValues(prCounts);
  const totalRFQs = sumValues(rfqCounts);
  const totalPOs = sumValues(poCounts);

  const issuedInvoices = invCounts.ISSUED ?? 0;
  const partialInvoices = invCounts.PARTIALLY_PAID ?? 0;
  const paidInvoices = invCounts.PAID ?? 0;
  const openInvoices = issuedInvoices + partialInvoices;
  const totalInvoices = openInvoices + paidInvoices;

  const completedPOs = (poCounts.DELIVERED ?? 0) + (poCounts.COMPLETED ?? 0);
  const inProgressPOs = (poCounts.ISSUED ?? 0) + (poCounts.ACKNOWLEDGED ?? 0) + (poCounts.PARTIALLY_DELIVERED ?? 0);

  // Số liệu tài chính thực tế từ danh sách PO và Hóa đơn hợp lệ
  const validOrders = orders.filter((o) => !["DRAFT", "CANCELLED", "DECLINED"].includes(o.status));
  const totalPoAmount = validOrders.reduce((sum, o) => sum + (Number(o.total) || 0), 0);

  const validInvoices = invoices.filter((inv) => inv.status !== "CANCELLED");
  const totalInvoicedAmount = validInvoices.reduce((sum, inv) => sum + (Number(inv.total) || 0), 0);
  const totalPaidAmount = validInvoices.reduce((sum, inv) => sum + (Number(inv.paid_amount) || 0), 0);
  const openBalanceAmount = Number(data?.receivables?.open_balance ?? 0);

  // Tỷ lệ đã thanh toán thực tế theo giá trị tiền (paid_amount / total)
  const exactPaidPercent =
    totalInvoicedAmount > 0
      ? Math.round((totalPaidAmount / totalInvoicedAmount) * 100)
      : totalInvoices > 0
        ? Math.round((paidInvoices / totalInvoices) * 100)
        : 0;

  const donutR = 62;
  const donutC = 2 * Math.PI * donutR;
  const donutBlueLen = (Math.max(0, Math.min(100, exactPaidPercent)) / 100) * donutC;

  // Ngân sách & Tiết kiệm thực tế từ KPI
  const savingsKpi = data?.kpis?.estimated_savings;
  const savingsAmount =
    savingsKpi?.value !== null && savingsKpi?.value !== undefined ? Number(savingsKpi.value) : null;
  const savingsRatePct =
    savingsKpi?.rate !== null && savingsKpi?.rate !== undefined
      ? Number((savingsKpi.rate * 100).toFixed(1))
      : null;
  const estimatedBudgetAmount =
    savingsAmount !== null && totalPoAmount > 0 ? totalPoAmount + savingsAmount : null;

  // Chuẩn hóa chiều rộng thanh so sánh tài chính
  const maxFinancialVal = Math.max(
    estimatedBudgetAmount ?? 0,
    totalPoAmount,
    totalInvoicedAmount,
    totalPaidAmount,
    openBalanceAmount,
    1
  );

  const financialBars = [
    ...(estimatedBudgetAmount !== null && !isSupplier
      ? [
          {
            label: "Ngân sách dự kiến (PR đã duyệt)",
            value: estimatedBudgetAmount,
            color: "#94A3B8",
            note: `${savingsKpi?.n ?? 0} đơn đối chiếu`,
          },
        ]
      : []),
    {
      label: "Tổng giá trị đặt hàng (PO chưa VAT)",
      value: totalPoAmount,
      color: "#3A64F6",
      note: `${validOrders.length} đơn hàng hợp lệ`,
    },
    {
      label: "Tổng giá trị hóa đơn (gồm VAT 10%)",
      value: totalInvoicedAmount,
      color: "#254EDB",
      note: `${validInvoices.length} hóa đơn phát hành`,
    },
    {
      label: isSupplier ? "Đã thu tiền (qua cổng IPN)" : "Đã thanh toán (qua cổng IPN)",
      value: totalPaidAmount,
      color: "#6085FA",
      note: `${exactPaidPercent}% tổng giá trị hóa đơn`,
    },
    {
      label: isSupplier ? "Công nợ phải thu còn lại" : "Công nợ còn phải trả",
      value: openBalanceAmount,
      color: "#64748B",
      note: `${openInvoices} hóa đơn chưa tất toán`,
    },
  ];

  const pipelineSteps = [
    ...(!isSupplier
      ? [
          {
            title: "Yêu cầu mua hàng (PR)",
            total: totalPRs,
            path: "/purchase-requests",
            icon: <FileTextOutlined />,
            details: [
              { label: "Đã duyệt", count: prCounts.APPROVED ?? 0 },
              { label: "Chờ duyệt", count: prCounts.PENDING_APPROVAL ?? 0 },
              { label: "Nháp", count: prCounts.DRAFT ?? 0 },
            ],
          },
        ]
      : []),
    {
      title: "Mời báo giá (RFQ)",
      total: totalRFQs,
      path: "/rfqs",
      icon: <AuditOutlined />,
      details: [
        { label: "Đang mở", count: rfqCounts.OPEN ?? 0 },
        { label: "Đã đóng", count: rfqCounts.CLOSED ?? 0 },
        { label: "Đã chọn NCC", count: rfqCounts.AWARDED ?? 0 },
      ],
    },
    {
      title: "Đơn đặt hàng (PO)",
      total: totalPOs,
      path: "/purchase-orders",
      icon: <ShoppingOutlined />,
      details: [
        { label: "Hoàn tất", count: poCounts.COMPLETED ?? 0 },
        { label: "Đã giao", count: poCounts.DELIVERED ?? 0 },
        { label: "Đang xử lý", count: inProgressPOs },
      ],
    },
    {
      title: "Hóa đơn & Thanh toán",
      total: totalInvoices,
      path: "/invoices",
      icon: <FileProtectOutlined />,
      details: [
        { label: "Đã tất toán", count: paidInvoices },
        { label: "Trả một phần", count: partialInvoices },
        { label: "Chờ thanh toán", count: issuedInvoices },
      ],
    },
  ];

  return (
    <AppShell>
      <div className="fin-subbar">
        <div>
          <p className="eyebrow" style={{ marginBottom: 2 }}>
            Tổng quan thời gian thực
          </p>
          <span className="fin-updated-at">
            Số liệu được tổng hợp trực tiếp từ hệ thống lúc{" "}
            {data ? formatTime(data.generated_at) : "—"}
          </span>
        </div>
        <Button icon={<ReloadOutlined />} onClick={() => void load()}>
          Làm mới dữ liệu
        </Button>
      </div>

      {error && <Alert message={error} type="error" showIcon style={{ marginBottom: 20 }} />}

      {loading && !data ? (
        <Skeleton active paragraph={{ rows: 10 }} />
      ) : (
        data && (
          <>
            {/* HÀNG 1: 4 THẺ CHỈ SỐ TÀI CHÍNH & VẬN HÀNH CỐT LÕI (100% DỮ LIỆU THẬT) */}
            <div className="fin-bento-top">
              {/* Thẻ 1: Công nợ mở */}
              <div className="fin-hero-card fin-hero-blue" onClick={() => navigate("/invoices")}>
                <div className="fin-hero-top">
                  <span className="fin-badge-icon fin-badge-white">
                    <DollarOutlined />
                  </span>
                  <span className="fin-period-tag fin-period-light">
                    {data.receivables.overdue_count > 0
                      ? `${data.receivables.overdue_count} hóa đơn quá hạn`
                      : `${openInvoices} hóa đơn đang mở`}
                  </span>
                </div>
                <div>
                  <div className="fin-hero-label">
                    {isSupplier ? "Công nợ phải thu còn lại" : "Số dư công nợ còn phải trả"}
                  </div>
                  <div className="fin-hero-value">{formatMoney(data.receivables.open_balance)}</div>
                </div>
                <div className="fin-hero-footer fin-hero-footer-light">
                  <div className="fin-progress-meta">
                    <span>Đã thanh toán: {formatMoney(totalPaidAmount)}</span>
                    <strong>{exactPaidPercent}%</strong>
                  </div>
                  <div className="fin-progress-track light">
                    <div
                      className="fin-progress-fill light"
                      style={{ width: `${Math.max(0, Math.min(100, exactPaidPercent))}%` }}
                    />
                  </div>
                </div>
              </div>

              {/* Thẻ 2: Giá trị & Tiến độ Đơn đặt hàng (PO) */}
              <div className="fin-hero-card fin-hero-white" onClick={() => navigate("/purchase-orders")}>
                <div className="fin-hero-top">
                  <span className="fin-badge-icon fin-badge-soft">
                    <ShoppingOutlined />
                  </span>
                  <span className="fin-period-tag">{totalPOs} đơn đặt hàng</span>
                </div>
                <div>
                  <div className="fin-hero-label">Tổng giá trị đơn hàng (PO)</div>
                  <div className="fin-hero-value">{formatMoney(totalPoAmount)}</div>
                </div>
                <div className="fin-hero-footer">
                  <span className="fin-footer-stat">
                    <strong>{completedPOs}</strong> đã giao/hoàn tất · <strong>{inProgressPOs}</strong> đang thực hiện
                  </span>
                </div>
              </div>

              {/* Thẻ 3: Tiết kiệm ngân sách (Buyer) hoặc Hồ sơ RFQ (Supplier) */}
              <div
                className="fin-hero-card fin-hero-white"
                onClick={() => navigate(isSupplier ? "/rfqs" : "/purchase-requests")}
              >
                <div className="fin-hero-top">
                  <span className="fin-badge-icon fin-badge-soft">
                    <AuditOutlined />
                  </span>
                  <span className="fin-period-tag">
                    {!isSupplier && savingsRatePct !== null
                      ? `Tiết kiệm ${savingsRatePct}%`
                      : `${totalRFQs} hồ sơ RFQ`}
                  </span>
                </div>
                <div>
                  <div className="fin-hero-label">
                    {isSupplier ? "Hồ sơ mời báo giá (RFQ)" : "Tiết kiệm so với ngân sách"}
                  </div>
                  <div className="fin-hero-value">
                    {!isSupplier
                      ? savingsAmount !== null
                        ? formatMoney(savingsAmount)
                        : "—"
                      : `${rfqCounts.OPEN ?? 0} đang mở / ${totalRFQs} RFQ`}
                  </div>
                </div>
                <div className="fin-hero-footer">
                  <span className="fin-footer-stat">
                    {!isSupplier
                      ? estimatedBudgetAmount !== null
                        ? `Ngân sách PR: ${formatMoney(estimatedBudgetAmount)} (${savingsKpi?.n ?? 0} đơn)`
                        : "So sánh giữa ngân sách PR và tổng PO"
                      : `${data.counts.quotations?.SUBMITTED ?? 0} báo giá đã gửi · ${rfqCounts.AWARDED ?? 0} trúng thầu`}
                  </span>
                </div>
              </div>

              {/* Thẻ 4: Việc cần xử lý ngay */}
              <div
                className="fin-hero-card fin-hero-white"
                onClick={() => {
                  const first = data.pending_actions[0];
                  if (first) navigate(pendingActionPath(first.type));
                }}
              >
                <div className="fin-hero-top">
                  <span className="fin-badge-icon fin-badge-soft">
                    <ClockCircleOutlined />
                  </span>
                  <span className="fin-period-tag">
                    {data.pending_count > 0 ? "Cần xử lý" : "Đã xử lý hết"}
                  </span>
                </div>
                <div>
                  <div className="fin-hero-label">Công việc đang chờ bạn xử lý</div>
                  <div className="fin-hero-value">{data.pending_count} công việc</div>
                </div>
                <div className="fin-hero-footer">
                  <span className="fin-footer-stat">
                    {!isSupplier
                      ? `${prCounts.PENDING_APPROVAL ?? 0} PR chờ duyệt · ${rfqCounts.OPEN ?? 0} RFQ mở · ${openInvoices} HĐ chờ trả`
                      : `${rfqCounts.OPEN ?? 0} RFQ đang mở · ${poCounts.ISSUED ?? 0} PO chờ xác nhận`}
                  </span>
                </div>
              </div>
            </div>

            {/* HÀNG 2: ĐỐI CHIẾU TÀI CHÍNH & TIẾN ĐỘ QUY TRÌNH + TỶ LỆ THANH TOÁN THỰC TẾ */}
            <div className="fin-bento-mid-2col">
              {/* Cột trái: Đối chiếu Ngân sách - PO - Hóa đơn - Thanh toán & Trạng thái chứng từ */}
              <div className="fin-card">
                <div className="fin-card-head">
                  <div>
                    <h3>Đối chiếu giá trị Mua sắm &amp; Thanh toán thực tế</h3>
                    <span>Tổng hợp trực tiếp từ các Yêu cầu mua hàng, Đơn hàng (PO) và Hóa đơn hiện hành</span>
                  </div>
                </div>

                <div className="fin-bars-list">
                  {financialBars.map((bar) => {
                    const widthPct =
                      bar.value > 0 ? Math.max(4, Math.round((bar.value / maxFinancialVal) * 100)) : 0;
                    return (
                      <div className="fin-bar-row" key={bar.label}>
                        <div className="fin-bar-row-head">
                          <span className="fin-bar-row-label">{bar.label}</span>
                          <span className="fin-bar-row-val">
                            <strong>{formatMoney(bar.value)}</strong>
                            <small>{bar.note}</small>
                          </span>
                        </div>
                        <div className="fin-bar-row-track">
                          <div
                            className="fin-bar-row-fill"
                            style={{ width: `${widthPct}%`, background: bar.color }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>

                <div className="fin-pipeline-head">
                  <h4>Số lượng chứng từ theo quy trình</h4>
                </div>
                <div className="fin-pipeline-grid">
                  {pipelineSteps.map((step) => (
                    <div
                      key={step.title}
                      className="fin-pipeline-box"
                      onClick={() => navigate(step.path)}
                    >
                      <div className="fin-pipeline-top">
                        <span className="fin-mini-icon blue">{step.icon}</span>
                        <div>
                          <span>{step.title}</span>
                          <strong>{step.total} chứng từ</strong>
                        </div>
                      </div>
                      <div className="fin-pipeline-tags">
                        {step.details.map((d) => (
                          <span key={d.label} className="fin-pipeline-pill">
                            {d.label}: <strong>{d.count}</strong>
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Cột phải: Tỷ lệ thanh toán hóa đơn thực tế (Donut Chart chính xác) */}
              <div className="fin-card fin-payments-donut-card">
                <div className="fin-card-head">
                  <div>
                    <h3>Tỷ lệ thanh toán hóa đơn</h3>
                    <span>Tính theo số tiền thực tế đã đối soát qua IPN</span>
                  </div>
                </div>

                <div className="fin-donut-stage">
                  <svg width="164" height="164" viewBox="0 0 168 168">
                    <circle
                      cx="84"
                      cy="84"
                      r={donutR}
                      fill="none"
                      stroke="#E9EDF5"
                      strokeWidth="18"
                    />
                    {exactPaidPercent > 0 && (
                      <circle
                        cx="84"
                        cy="84"
                        r={donutR}
                        fill="none"
                        stroke="#3A64F6"
                        strokeWidth="18"
                        strokeDasharray={`${donutBlueLen} ${donutC}`}
                        strokeLinecap="butt"
                        transform="rotate(-90 84 84)"
                      />
                    )}
                  </svg>
                  <div className="fin-donut-center">
                    <strong>{exactPaidPercent}%</strong>
                    <span>Đã thanh toán</span>
                  </div>
                </div>

                <div className="fin-donut-breakdown">
                  <div className="fin-donut-row">
                    <span>
                      <i className="fin-dot fin-dot-blue" /> Đã thanh toán ({exactPaidPercent}%)
                    </span>
                    <strong>{formatMoney(totalPaidAmount)}</strong>
                  </div>
                  <div className="fin-donut-row">
                    <span>
                      <i className="fin-dot fin-dot-slate" /> Còn phải trả ({totalInvoicedAmount > 0 ? 100 - exactPaidPercent : 0}%)
                    </span>
                    <strong>{formatMoney(openBalanceAmount)}</strong>
                  </div>
                  <div className="fin-donut-row total">
                    <span>Tổng hóa đơn (gồm VAT)</span>
                    <strong>{formatMoney(totalInvoicedAmount)}</strong>
                  </div>
                </div>

                <div className="fin-donut-status-summary">
                  <span>Đã tất toán: <strong>{paidInvoices}</strong></span>
                  <span>·</span>
                  <span>Trả một phần: <strong>{partialInvoices}</strong></span>
                  <span>·</span>
                  <span>Chờ trả: <strong>{issuedInvoices}</strong></span>
                </div>
              </div>
            </div>

            {/* HÀNG 3: 6 CHỈ SỐ HIỆU QUẢ MUA SẮM (KPI THỰC TẾ TỪ BACKEND) */}
            {data.kpis && (
              <section className="panel" style={{ marginBottom: 22 }}>
                <div className="panel-heading">
                  <h2>Chỉ số hiệu quả mua sắm (KPI thực tế)</h2>
                  <span>Tính tự động từ dữ liệu hệ thống · n là số lượng mẫu thực tế</span>
                </div>
                <div className="kpi-grid">
                  {kpiLabels.map(([key, label]) => {
                    const kpi = data.kpis?.[key];
                    return kpi ? (
                      <div className="kpi-card" key={key} title={kpi.definition}>
                        <div className="stat-label">{label}</div>
                        <div className="stat-value">{formatKpi(kpi)}</div>
                        <div className="kpi-note">
                          Cỡ mẫu: n = {kpi.n} · {kpi.definition}
                        </div>
                      </div>
                    ) : null;
                  })}
                </div>
              </section>
            )}

            {/* HÀNG 4: CÔNG VIỆC CẦN XỬ LÝ & NHẬT KÝ HOẠT ĐỘNG */}
            <div className="content-grid">
              <div>
                <section className="panel">
                  <div className="panel-heading">
                    <h2>Nhật ký hoạt động gần đây</h2>
                    <span>{data.recent_activity.length} sự kiện mới nhất</span>
                  </div>
                  <div className="activity-list">
                    {data.recent_activity.length === 0 ? (
                      <div className="empty-state">Chưa có hoạt động nào được ghi nhận.</div>
                    ) : (
                      data.recent_activity.map((item) => (
                        <div className="activity-item" key={item.id}>
                          <div className="activity-icon">
                            <CheckCircleOutlined />
                          </div>
                          <div className="item-main">
                            <strong>{displayAction(item.action)}</strong>
                            <span>
                              {displayEntityType(item.entity_type)} · Mã: {item.entity_id.slice(0, 8)}
                              {item.actor ? ` · Thực hiện bởi: ${item.actor.full_name}` : ""}
                            </span>
                          </div>
                          <div className="item-time">{formatTime(item.occurred_at)}</div>
                        </div>
                      ))
                    )}
                  </div>
                </section>
              </div>
              <div>
                <section className="panel">
                  <div className="panel-heading">
                    <h2>Công việc cần xử lý</h2>
                    <span>{data.pending_count} việc</span>
                  </div>
                  <div className="pending-list">
                    {data.pending_actions.length === 0 ? (
                      <div className="empty-state">Không có công việc tồn đọng.</div>
                    ) : (
                      data.pending_actions.map((item) => (
                        <button
                          type="button"
                          className="pending-item pending-item-btn"
                          key={`${item.type}-${item.id}`}
                          onClick={() => navigate(pendingActionPath(item.type))}
                        >
                          <div className="activity-icon pending-icon">
                            <ClockCircleOutlined />
                          </div>
                          <div className="item-main">
                            <strong>{displayPendingLabel(item.label)}</strong>
                            <span>{item.number}</span>
                          </div>
                          <Tag style={{ margin: 0 }}>
                            {statusLabels[item.status] ?? item.status}
                          </Tag>
                          <ArrowRightOutlined style={{ color: "#7C8498", fontSize: 12 }} />
                        </button>
                      ))
                    )}
                  </div>
                </section>
              </div>
            </div>
          </>
        )
      )}
    </AppShell>
  );
}
