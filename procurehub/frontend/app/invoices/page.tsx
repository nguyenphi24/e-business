"use client";

import { Alert, Button, Form, InputNumber, Modal, Space, Switch, Table, Tag, Tooltip } from "antd";
import { AlertOutlined, CheckCircleOutlined, CheckOutlined, CloseOutlined, DollarOutlined, ExportOutlined, FileProtectOutlined, ReloadOutlined, StopOutlined } from "@ant-design/icons";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import AppShell from "@/components/app-shell";
import { ApiList, apiFetch, formatMoney, getStoredUser, hasRole, Invoice, Payment } from "@/lib/api";

const labels: Record<string, string> = { ISSUED: "Chờ thanh toán", PARTIALLY_PAID: "Đã trả một phần", PAID: "Đã thanh toán", CANCELLED: "Đã hủy" };
const paymentLabels: Record<Payment["status"], string> = { PENDING: "Chờ cổng xác nhận", SUCCEEDED: "Thành công", FAILED: "Thất bại" };
const einvoiceLabels: Record<Invoice["einvoice"]["status"], { text: string; color: string }> = {
  NOT_SENT: { text: "Chưa phát hành", color: "default" },
  PENDING_TAX_CODE: { text: "Chờ CQT cấp mã", color: "processing" },
  ISSUED: { text: "Đã có mã CQT", color: "green" },
  FAILED: { text: "Lỗi phát hành", color: "red" },
};

function statusColor(invoice: Invoice) {
  if (invoice.status === "PAID") return "green";
  if (invoice.status === "CANCELLED") return "default";
  return invoice.is_overdue ? "red" : "gold";
}

export default function InvoicesPage() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [overdueOnly, setOverdueOnly] = useState(false);
  const [paying, setPaying] = useState<Invoice | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [paymentForm] = Form.useForm<{ amount: number }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const [returned, setReturned] = useState<string | null>(null);
  const user = getStoredUser();
  const isFinance = hasRole(user, "FINANCE");
  const isSupplier = hasRole(user, "SUPPLIER");

  async function load(overdue = overdueOnly) {
    setLoading(true);
    setError(null);
    try {
      const result = await apiFetch<ApiList<Invoice> | Invoice[]>(`/invoices${overdue ? "?overdue=true" : ""}`);
      setInvoices(Array.isArray(result) ? result : result.results ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tải được hóa đơn.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // Quay về từ cổng thanh toán: kết quả chính thức đến qua IPN, nên tải lại sau vài giây.
    const status = searchParams.get("status");
    if (searchParams.get("payment")) {
      setReturned(status);
      setSearchParams({}, { replace: true });
      const timer = window.setTimeout(() => void load(), 2000);
      return () => window.clearTimeout(timer);
    }
    return undefined;
  }, []);

  useEffect(() => {
    if (!invoices.some((inv) => inv.einvoice.status === "PENDING_TAX_CODE")) return undefined;
    const timer = window.setTimeout(() => void load(), 2500);
    return () => window.clearTimeout(timer);
  }, [invoices]);

  function openPayment(invoice: Invoice) {
    setPaying(invoice);
    paymentForm.setFieldsValue({ amount: Number(invoice.balance) });
  }

  async function createPayment(values: { amount: number }) {
    if (!paying) return;
    setActionLoading("create");
    try {
      const result = await apiFetch<{ payment: Payment }>(`/invoices/${paying.id}/payments`, {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify({ amount: values.amount.toFixed(2) }),
      });
      setPaying(null);
      if (result.payment.checkout_url) {
        window.location.assign(result.payment.checkout_url);  // chuyển sang trang của cổng thanh toán
        return;
      }
      if (result.payment.status === "FAILED") setError(result.payment.failure_reason || "Không tạo được giao dịch ở cổng thanh toán.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tạo được lệnh thanh toán.");
    } finally {
      setActionLoading(null);
    }
  }

  async function simulate(payment: Payment, outcome: "SUCCEEDED" | "FAILED") {
    setActionLoading(`${outcome}-${payment.id}`);
    try {
      await apiFetch(`/payments/${payment.id}/simulate`, { method: "POST", body: JSON.stringify({ outcome }) });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không mô phỏng được thanh toán.");
    } finally {
      setActionLoading(null);
    }
  }

  async function sendEInvoice(invoice: Invoice) {
    setActionLoading(`einvoice-${invoice.id}`);
    try {
      await apiFetch(`/invoices/${invoice.id}/einvoice`, { method: "POST", body: JSON.stringify({}) });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không phát hành được hóa đơn điện tử.");
    } finally {
      setActionLoading(null);
    }
  }

  async function cancel(invoice: Invoice) {
    setActionLoading(`cancel-${invoice.id}`);
    try {
      await apiFetch(`/invoices/${invoice.id}/cancel`, { method: "POST", body: JSON.stringify({}) });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không hủy được hóa đơn.");
    } finally {
      setActionLoading(null);
    }
  }

  const paymentColumns = [
    { title: "Mã tham chiếu", dataIndex: "external_ref" },
    { title: "Số tiền", dataIndex: "amount", render: (value: string) => formatMoney(value) },
    { title: "Trạng thái", dataIndex: "status", render: (value: Payment["status"]) => <Tag color={value === "SUCCEEDED" ? "green" : value === "FAILED" ? "red" : "blue"}>{paymentLabels[value]}</Tag> },
    { title: "Thời điểm", render: (_: unknown, payment: Payment) => new Date(payment.settled_at ?? payment.created_at).toLocaleString("vi-VN") },
    { title: "Cổng thanh toán", render: (_: unknown, payment: Payment) => payment.status === "PENDING" && payment.checkout_url ? (isFinance ? <Button size="small" type="link" icon={<ExportOutlined />} href={payment.checkout_url}>Mở cổng thanh toán</Button> : "Đang chờ tại cổng") : isFinance && payment.status === "PENDING" ? <Space size="small">
      <Button size="small" type="primary" icon={<CheckOutlined />} loading={actionLoading === `SUCCEEDED-${payment.id}`} onClick={() => void simulate(payment, "SUCCEEDED")}>Thành công</Button>
      <Button size="small" danger icon={<CloseOutlined />} loading={actionLoading === `FAILED-${payment.id}`} onClick={() => void simulate(payment, "FAILED")}>Thất bại</Button>
    </Space> : payment.failure_reason || "—" },
  ];

  const totalOutstanding = invoices.reduce((sum, inv) => sum + Number(inv.balance ?? 0), 0);
  const taxIssuedCount = invoices.filter((inv) => inv.einvoice.status === "ISSUED").length;
  const overdueCount = invoices.filter((inv) => inv.is_overdue).length;

  return <AppShell>
    <div className="topbar">
      <div><p className="eyebrow">Đối soát &amp; Thanh toán</p><h1 className="page-title">Hóa đơn &amp; Thanh toán</h1><p className="page-subtitle">{isSupplier ? "Quản lý hóa đơn đã phát hành cho bên mua, cấp mã CQT và theo dõi tiền về." : "Theo dõi công nợ phải trả theo hạn trả chậm, tra cứu HĐĐT và thực hiện thanh toán."}</p></div>
      <Space wrap><span>Chỉ hiện quá hạn</span><Switch checked={overdueOnly} onChange={(checked) => { setOverdueOnly(checked); void load(checked); }} /><Button icon={<ReloadOutlined />} onClick={() => void load()}>Làm mới</Button></Space>
    </div>
    <div className="fin-page-stats">
      <div className="fin-mini-stat"><div className="fin-mini-icon blue"><FileProtectOutlined /></div><div className="fin-mini-meta"><span>Tổng hóa đơn</span><strong>{invoices.length}</strong></div></div>
      <div className="fin-mini-stat"><div className="fin-mini-icon pink"><DollarOutlined /></div><div className="fin-mini-meta"><span>Còn phải thanh toán</span><strong>{formatMoney(String(totalOutstanding))}</strong></div></div>
      <div className="fin-mini-stat"><div className="fin-mini-icon green"><CheckCircleOutlined /></div><div className="fin-mini-meta"><span>Đã cấp mã CQT</span><strong>{taxIssuedCount}</strong></div></div>
      <div className="fin-mini-stat"><div className="fin-mini-icon gold"><AlertOutlined /></div><div className="fin-mini-meta"><span>Hóa đơn quá hạn</span><strong>{overdueCount}</strong></div></div>
    </div>
    <Alert type="warning" showIcon style={{ marginBottom: 20 }} message="Môi trường mô phỏng Thanh toán & Hóa đơn điện tử" description="Cổng thanh toán, hóa đơn điện tử và mã cơ quan thuế được vận hành trên dịch vụ giả lập (sandbox-service): không phát sinh giao dịch tiền thật. Số dư công nợ tự động cập nhật khi hệ thống nhận bản tin đối soát IPN có chữ ký số từ cổng thanh toán." />
    {returned && <Alert type={returned === "SUCCEEDED" ? "success" : "info"} showIcon closable onClose={() => setReturned(null)} style={{ marginBottom: 20 }} message={returned === "SUCCEEDED" ? "Cổng thanh toán xác nhận giao dịch thành công" : "Đã quay lại từ cổng thanh toán"} description="Số dư hóa đơn được tự động gạch nợ khi ProcureHub nhận thông báo IPN hợp lệ từ cổng thanh toán." />}
    {error && <Alert message={error} type="error" showIcon closable onClose={() => setError(null)} style={{ marginBottom: 20 }} />}
    <div className="panel"><Table<Invoice> loading={loading} dataSource={invoices} rowKey="id" pagination={{ pageSize: 10 }} scroll={{ x: "max-content" }}
      expandable={{ expandedRowRender: (invoice) => invoice.payments.length ? <Table<Payment> size="small" pagination={false} rowKey="id" dataSource={invoice.payments} columns={paymentColumns} /> : <span>Chưa có lịch sử giao dịch thanh toán.</span> }}
      columns={[
        { title: "Số hóa đơn", dataIndex: "number" },
        { title: "Mã đơn PO", render: (_, invoice) => invoice.purchase_order.number },
        { title: isSupplier ? "Bên mua" : "Nhà cung cấp", render: (_, invoice) => isSupplier ? invoice.buyer.legal_name : invoice.supplier.legal_name },
        { title: "Tổng tiền (gồm VAT)", render: (_, invoice) => <Tooltip title={`Trước thuế ${formatMoney(invoice.subtotal)} + VAT ${Number(invoice.vat_rate)}% (${formatMoney(invoice.vat_amount)})`}><span>{formatMoney(invoice.total)}</span></Tooltip> },
        { title: "Còn phải trả", dataIndex: "balance", render: (value: string) => formatMoney(value) },
        { title: "Hạn thanh toán", render: (_, invoice) => <span>{new Date(invoice.due_date).toLocaleDateString("vi-VN")} ({invoice.payment_term_days} ngày)</span> },
        { title: "Trạng thái", render: (_, invoice) => <Space size={4} wrap><Tag color={statusColor(invoice)}>{labels[invoice.status] ?? invoice.status}</Tag>{invoice.is_overdue && <Tag color="red">Quá hạn</Tag>}</Space> },
        { title: "Hóa đơn điện tử", render: (_, invoice) => {
          const einvoice = invoice.einvoice;
          const label = einvoiceLabels[einvoice.status];
          return <Space direction="vertical" size={2}>
            <Tooltip title={einvoice.error || einvoice.tax_code || undefined}><Tag color={label.color}>{label.text}</Tag></Tooltip>
            {einvoice.number !== null && <span className="kpi-note">{einvoice.symbol} · số {String(einvoice.number).padStart(7, "0")}</span>}
            {einvoice.lookup_url && <a href={einvoice.lookup_url} target="_blank" rel="noreferrer">Tra cứu HĐĐT <ExportOutlined /></a>}
            {isSupplier && invoice.status !== "CANCELLED" && einvoice.status !== "ISSUED" && <Button size="small" icon={einvoice.status === "PENDING_TAX_CODE" ? <ReloadOutlined /> : <FileProtectOutlined />} loading={actionLoading === `einvoice-${invoice.id}`} onClick={() => void sendEInvoice(invoice)}>{einvoice.status === "PENDING_TAX_CODE" ? "Làm mới" : einvoice.status === "FAILED" ? "Phát hành lại" : "Phát hành HĐĐT"}</Button>}
          </Space>;
        } },
        { title: "Thao tác", key: "actions", render: (_, invoice) => <Space size="small" wrap>
          {isFinance && ["ISSUED", "PARTIALLY_PAID"].includes(invoice.status) && <Button size="small" type="primary" icon={<DollarOutlined />} onClick={() => openPayment(invoice)}>Thanh toán</Button>}
          {isSupplier && invoice.status === "ISSUED" && invoice.payments.every((payment) => payment.status === "FAILED") && <Button size="small" danger icon={<StopOutlined />} loading={actionLoading === `cancel-${invoice.id}`} onClick={() => void cancel(invoice)}>Hủy</Button>}
        </Space> },
      ]} /></div>
    <Modal title={paying ? `Tạo lệnh thanh toán · ${paying.number}` : "Tạo lệnh thanh toán"} open={Boolean(paying)} footer={null} onCancel={() => setPaying(null)} destroyOnHidden>
      {paying && <Form form={paymentForm} layout="vertical" onFinish={createPayment}>
        <p>Tổng giá trị hóa đơn: <strong>{formatMoney(paying.total)}</strong> (Trước thuế {formatMoney(paying.subtotal)} + VAT {Number(paying.vat_rate)}%). Số dư còn phải trả: <strong>{formatMoney(paying.balance)}</strong>. Bạn có thể thanh toán từng đợt hoặc tất toán toàn bộ.</p>
        <Space style={{ marginBottom: 12 }}>
          <Button size="small" onClick={() => paymentForm.setFieldsValue({ amount: Math.round(Number(paying.balance) * 0.3) })}>Tạm ứng 30%</Button>
          <Button size="small" onClick={() => paymentForm.setFieldsValue({ amount: Number(paying.balance) })}>Tất toán 100%</Button>
        </Space>
        <Form.Item name="amount" label="Số tiền thanh toán (VND)" rules={[{ required: true, message: "Nhập số tiền thanh toán." }]}><InputNumber min={1} max={Number(paying.balance)} style={{ width: "100%" }} /></Form.Item>
        <Button block size="large" type="primary" htmlType="submit" loading={actionLoading === "create"}>Chuyển tới cổng thanh toán</Button>
      </Form>}
    </Modal>
  </AppShell>;
}
