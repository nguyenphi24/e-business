"use client";

import { Alert, Button, Form, InputNumber, Modal, Space, Switch, Table, Tag, Tooltip } from "antd";
import { CheckOutlined, CloseOutlined, DollarOutlined, ExportOutlined, FileProtectOutlined, ReloadOutlined, StopOutlined } from "@ant-design/icons";
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

  return <AppShell>
    <div className="topbar">
      <div><p className="eyebrow">Invoice-to-Pay</p><h1 className="page-title">Hóa đơn & thanh toán</h1><p className="page-subtitle">{isSupplier ? "Hóa đơn đã lập cho bên mua và tình trạng thanh toán." : "Theo dõi công nợ theo điều khoản Net N và ghi nhận thanh toán."}</p></div>
      <Space wrap><span>Chỉ quá hạn</span><Switch checked={overdueOnly} onChange={(checked) => { setOverdueOnly(checked); void load(checked); }} /><Button icon={<ReloadOutlined />} onClick={() => void load()}>Làm mới</Button></Space>
    </div>
    <Alert type="warning" showIcon style={{ marginBottom: 20 }} message="Thanh toán Sandbox/Demo" description="Cổng thanh toán, hóa đơn điện tử và mã cơ quan thuế đều là giả lập (sandbox-service): không chuyển tiền thật, không có giá trị pháp lý. Số dư chỉ thay đổi khi backend nhận sự kiện có chữ ký từ cổng (IPN)." />
    {returned && <Alert type={returned === "SUCCEEDED" ? "success" : "info"} showIcon closable onClose={() => setReturned(null)} style={{ marginBottom: 20 }} message={returned === "SUCCEEDED" ? "Cổng thanh toán báo giao dịch thành công" : "Đã quay lại từ cổng thanh toán"} description="Số dư hóa đơn chỉ cập nhật khi ProcureHub nhận IPN có chữ ký từ cổng." />}
    {error && <Alert message={error} type="error" showIcon closable onClose={() => setError(null)} style={{ marginBottom: 20 }} />}
    <div className="panel"><Table<Invoice> loading={loading} dataSource={invoices} rowKey="id" pagination={{ pageSize: 10 }} scroll={{ x: "max-content" }}
      expandable={{ expandedRowRender: (invoice) => invoice.payments.length ? <Table<Payment> size="small" pagination={false} rowKey="id" dataSource={invoice.payments} columns={paymentColumns} /> : <span>Chưa có lệnh thanh toán.</span> }}
      columns={[
        { title: "Số hóa đơn", dataIndex: "number" },
        { title: "PO", render: (_, invoice) => invoice.purchase_order.number },
        { title: isSupplier ? "Bên mua" : "Nhà cung cấp", render: (_, invoice) => isSupplier ? invoice.buyer.legal_name : invoice.supplier.legal_name },
        { title: "Tổng (gồm VAT)", render: (_, invoice) => <Tooltip title={`Trước thuế ${formatMoney(invoice.subtotal)} + VAT ${Number(invoice.vat_rate)}% ${formatMoney(invoice.vat_amount)}`}><span>{formatMoney(invoice.total)}</span></Tooltip> },
        { title: "Còn phải trả", dataIndex: "balance", render: (value: string) => formatMoney(value) },
        { title: "Hạn trả", render: (_, invoice) => <span>{new Date(invoice.due_date).toLocaleDateString("vi-VN")} · Net {invoice.payment_term_days}</span> },
        { title: "Trạng thái", render: (_, invoice) => <Space size={4} wrap><Tag color={statusColor(invoice)}>{labels[invoice.status] ?? invoice.status}</Tag>{invoice.is_overdue && <Tag color="red">Quá hạn</Tag>}</Space> },
        { title: "Hóa đơn điện tử", render: (_, invoice) => {
          const einvoice = invoice.einvoice;
          const label = einvoiceLabels[einvoice.status];
          return <Space direction="vertical" size={2}>
            <Tooltip title={einvoice.error || einvoice.tax_code || undefined}><Tag color={label.color}>{label.text}</Tag></Tooltip>
            {einvoice.number !== null && <span className="kpi-note">{einvoice.symbol} · số {String(einvoice.number).padStart(7, "0")}</span>}
            {einvoice.lookup_url && <a href={einvoice.lookup_url} target="_blank" rel="noreferrer">Tra cứu <ExportOutlined /></a>}
            {isSupplier && invoice.status !== "CANCELLED" && einvoice.status !== "ISSUED" && <Button size="small" icon={einvoice.status === "PENDING_TAX_CODE" ? <ReloadOutlined /> : <FileProtectOutlined />} loading={actionLoading === `einvoice-${invoice.id}`} onClick={() => void sendEInvoice(invoice)}>{einvoice.status === "PENDING_TAX_CODE" ? "Làm mới" : einvoice.status === "FAILED" ? "Phát hành lại" : "Phát hành HĐĐT"}</Button>}
          </Space>;
        } },
        { title: "Thao tác", key: "actions", render: (_, invoice) => <Space size="small" wrap>
          {isFinance && ["ISSUED", "PARTIALLY_PAID"].includes(invoice.status) && <Button size="small" type="primary" icon={<DollarOutlined />} onClick={() => openPayment(invoice)}>Thanh toán</Button>}
          {isSupplier && invoice.status === "ISSUED" && invoice.payments.every((payment) => payment.status === "FAILED") && <Button size="small" danger icon={<StopOutlined />} loading={actionLoading === `cancel-${invoice.id}`} onClick={() => void cancel(invoice)}>Hủy</Button>}
        </Space> },
      ]} /></div>
    <Modal title={paying ? `Lệnh thanh toán sandbox · ${paying.number}` : "Lệnh thanh toán"} open={Boolean(paying)} footer={null} onCancel={() => setPaying(null)} destroyOnHidden>
      {paying && <Form form={paymentForm} layout="vertical" onFinish={createPayment}>
        <p>Tổng hóa đơn {formatMoney(paying.total)} (trước thuế {formatMoney(paying.subtotal)} + VAT {Number(paying.vat_rate)}%). Còn phải trả: <strong>{formatMoney(paying.balance)}</strong>. Có thể trả nhiều lần; tổng các lệnh đang chờ không vượt số dư.</p>
        <Space style={{ marginBottom: 12 }}>
          <Button size="small" onClick={() => paymentForm.setFieldsValue({ amount: Math.round(Number(paying.balance) * 0.3) })}>30%</Button>
          <Button size="small" onClick={() => paymentForm.setFieldsValue({ amount: Number(paying.balance) })}>Toàn bộ</Button>
        </Space>
        <Form.Item name="amount" label="Số tiền (VND)" rules={[{ required: true, message: "Nhập số tiền." }]}><InputNumber min={1} max={Number(paying.balance)} style={{ width: "100%" }} /></Form.Item>
        <Button block type="primary" htmlType="submit" loading={actionLoading === "create"}>Tiếp tục tới cổng thanh toán</Button>
      </Form>}
    </Modal>
  </AppShell>;
}
