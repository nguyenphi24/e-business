"use client";

import dayjs from "dayjs";
import { Alert, Button, DatePicker, Drawer, Form, Input, InputNumber, Modal, Select, Space, Table, Tag, Tooltip, Typography, message } from "antd";
import { AuditOutlined, CheckOutlined, ClockCircleOutlined, CloseOutlined, DeleteOutlined, ExportOutlined, PlusOutlined, ReloadOutlined, SafetyCertificateOutlined, SendOutlined, TrophyOutlined } from "@ant-design/icons";
import { useEffect, useState } from "react";

import AppShell from "@/components/app-shell";
import { ApiError, ApiList, apiFetch, Comparison, formatMoney, getStoredUser, PurchaseOrder, PurchaseRequest, Quotation, QuotationSignature, RFQ, RFQCreateInput, ScoreResult, ScoringWeights, SupplierRelationship, SupplierSelection } from "@/lib/api";

const labels: Record<string, string> = { DRAFT: "Nháp", OPEN: "Đang mở", CLOSED: "Đã đóng", AWARDED: "Đã chọn", CANCELLED: "Đã hủy", SUBMITTED: "Đã gửi", PROPOSED: "Đề xuất", APPROVED: "Đã duyệt", REJECTED: "Từ chối" };
const invitationLabels: Record<string, { text: string; color: string }> = {
  INVITED: { text: "Chưa xem", color: "default" },
  VIEWED: { text: "Đã xem", color: "blue" },
  ACCEPTED: { text: "Xác nhận tham gia", color: "cyan" },
  QUOTED: { text: "Đã gửi báo giá", color: "green" },
  DECLINED: { text: "Từ chối", color: "red" },
  EXPIRED: { text: "Hết hạn", color: "default" },
};

type QuotationFormValues = { lines: Array<{ rfq_line_id: number; offered_quantity: number; unit_price?: number }>; delivery_days?: number; payment_terms?: string; payment_term_days?: number };
type RFQFormValues = { request_id: string; title: string; instructions?: string; deadline: dayjs.Dayjs; supplier_company_ids: string[]; weights: ScoringWeights };

const DEFAULT_WEIGHTS: ScoringWeights = { price: 45, delivery: 25, rating: 20, payment_terms: 10 };
const criteria: Array<{ key: keyof ScoringWeights; label: string }> = [
  { key: "price", label: "Giá" },
  { key: "delivery", label: "Giao hàng" },
  { key: "rating", label: "Uy tín NCC" },
  { key: "payment_terms", label: "Điều khoản" },
];

function WeightInputs({ prefix }: { prefix: string[] }) {
  return <div className="weights-row">{criteria.map((item) => <Form.Item key={item.key} name={[...prefix, item.key]} label={`${item.label} (%)`} rules={[{ required: true, message: "Nhập trọng số." }]}><InputNumber min={0} max={100} precision={0} style={{ width: "100%" }} /></Form.Item>)}</div>;
}

const signatureLabels: Record<QuotationSignature["state"], { text: string; color: string }> = {
  UNSIGNED: { text: "Chưa ký", color: "default" },
  PENDING: { text: "Chờ ký (OTP)", color: "processing" },
  VALID: { text: "Chữ ký hợp lệ", color: "green" },
  INVALID: { text: "Chữ ký KHÔNG hợp lệ", color: "red" },
  REJECTED: { text: "Từ chối ký", color: "orange" },
  FAILED: { text: "Ký thất bại", color: "red" },
  UNVERIFIABLE: { text: "Chưa xác minh được", color: "gold" },
};

function SignatureTag({ signature }: { signature: QuotationSignature }) {
  const label = signatureLabels[signature.state];
  const details = [
    signature.signer && `Người ký: ${signature.signer} (MST ${signature.signer_tax_code})`,
    signature.certificate_serial && `Chứng thư: ${signature.certificate_serial}`,
    signature.signed_at && `Ký lúc: ${new Date(signature.signed_at).toLocaleString("vi-VN")}`,
    signature.reason,
  ].filter(Boolean).join(" · ");
  return <Tooltip title={details || undefined}><Tag icon={signature.state === "VALID" ? <SafetyCertificateOutlined /> : undefined} color={label.color}>{label.text}</Tag></Tooltip>;
}

function weightsTotal(weights?: Partial<ScoringWeights>) {
  return criteria.reduce((sum, item) => sum + Number(weights?.[item.key] ?? 0), 0);
}
type DecisionFormValues = { reason: string };

export default function RFQsPage() {
  const [rfqs, setRfqs] = useState<RFQ[]>([]);
  const [requests, setRequests] = useState<PurchaseRequest[]>([]);
  const [suppliers, setSuppliers] = useState<SupplierRelationship[]>([]);
  const [selected, setSelected] = useState<RFQ | null>(null);
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [quotation, setQuotation] = useState<Quotation | null>(null);
  const [selection, setSelection] = useState<SupplierSelection | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [decisionOpen, setDecisionOpen] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [form] = Form.useForm<QuotationFormValues>();
  const [rfqForm] = Form.useForm<RFQFormValues>();
  const [selectionForm] = Form.useForm<{ quotation_id: string; rationale: string }>();
  const [decisionForm] = Form.useForm<DecisionFormValues>();
  const [weightsForm] = Form.useForm<{ weights: ScoringWeights }>();
  const [declineOpen, setDeclineOpen] = useState(false);
  const [declineForm] = Form.useForm<{ reason: string }>();
  const user = getStoredUser();
  const supplierView = user?.roles.includes("SUPPLIER") ?? false;
  const canPropose = user?.roles.some((role) => ["BUYER", "COMPANY_ADMIN", "SYSTEM_ADMIN"].includes(role)) ?? false;
  const canApprove = user?.roles.some((role) => ["MANAGER", "SYSTEM_ADMIN"].includes(role)) ?? false;

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const result = await apiFetch<ApiList<RFQ> | RFQ[]>("/rfqs");
      setRfqs(Array.isArray(result) ? result : result.results ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tải được RFQ.");
    } finally {
      setLoading(false);
    }
  }

  async function loadCreateOptions() {
    if (!canPropose) return;
    try {
      const [requestResult, supplierResult] = await Promise.all([
        apiFetch<ApiList<PurchaseRequest> | PurchaseRequest[]>("/purchase-requests"),
        apiFetch<{ results: SupplierRelationship[] }>("/suppliers"),
      ]);
      const requestItems = Array.isArray(requestResult) ? requestResult : requestResult.results ?? [];
      setRequests(requestItems.filter((request) => request.status === "APPROVED"));
      setSuppliers(supplierResult.results ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tải được dữ liệu tạo RFQ.");
    }
  }

  useEffect(() => {
    void load();
    void loadCreateOptions();
  }, []);

  async function createRFQ(values: RFQFormValues) {
    const payload: RFQCreateInput = {
      request_id: values.request_id,
      title: values.title,
      instructions: values.instructions ?? "",
      deadline: values.deadline.toISOString(),
      supplier_company_ids: values.supplier_company_ids,
      scoring_weights: values.weights,
    };
    if (weightsTotal(values.weights) !== 100) {
      setError("Tổng trọng số chấm điểm phải bằng 100.");
      return;
    }
    try {
      await apiFetch("/rfqs", { method: "POST", body: JSON.stringify(payload) });
      setCreateOpen(false);
      rfqForm.resetFields();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tạo được RFQ.");
    }
  }

  async function transitionRFQ(rfq: RFQ, action: "publish" | "close" | "cancel") {
    setActionLoading(`${action}-${rfq.id}`);
    try {
      const updated = await apiFetch<RFQ>(`/rfqs/${rfq.id}/${action}`, { method: "POST", body: JSON.stringify({}) });
      if (selected?.id === rfq.id) setSelected(updated);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không cập nhật được RFQ.");
    } finally {
      setActionLoading(null);
    }
  }

  async function openRFQ(rfq: RFQ) {
    if (supplierView) {
      // Lấy chi tiết để hệ thống ghi nhận "đã xem" và trả trạng thái lời mời mới nhất.
      try { rfq = await apiFetch<RFQ>(`/rfqs/${rfq.id}`); } catch { /* dùng dữ liệu danh sách */ }
    }
    setSelected(rfq);
    setComparison(null);
    setQuotation(null);
    setSelection(null);
    selectionForm.resetFields();
    weightsForm.setFieldsValue({ weights: rfq.scoring_weights ?? DEFAULT_WEIGHTS });
    if (!supplierView && ["CLOSED", "AWARDED"].includes(rfq.status)) {
      try {
        setComparison(await apiFetch<Comparison>(`/rfqs/${rfq.id}/comparison`));
        const result = await apiFetch<ApiList<SupplierSelection> | SupplierSelection[]>("/selections");
        const selections = Array.isArray(result) ? result : result.results ?? [];
        setSelection(selections.find((item) => item.rfq === rfq.id) ?? null);
      } catch {
        setError("Chưa có dữ liệu so sánh cho RFQ này.");
      }
    }
    if (supplierView) {
      try {
        const existing = await apiFetch<Quotation>(`/rfqs/${rfq.id}/quotation`);
        setQuotation(existing);
        form.setFieldsValue({ delivery_days: existing.delivery_days ?? undefined, payment_terms: existing.payment_terms, payment_term_days: existing.payment_term_days ?? undefined, lines: existing.lines.map((line) => ({ rfq_line_id: line.rfq_line.id, offered_quantity: Number(line.offered_quantity), unit_price: line.unit_price ? Number(line.unit_price) : undefined })) });
      } catch (err) {
        if (!(err instanceof ApiError) || err.status !== 404) setError("Không tải được báo giá.");
        if (rfq.status === "OPEN") form.setFieldsValue({ lines: rfq.lines.map((line) => ({ rfq_line_id: line.id, offered_quantity: Number(line.quantity) })) });
      }
    }
  }

  async function saveWeights(values: { weights: ScoringWeights }) {
    if (!selected) return;
    if (weightsTotal(values.weights) !== 100) {
      setError("Tổng trọng số chấm điểm phải bằng 100.");
      return;
    }
    try {
      const updated = await apiFetch<RFQ>(`/rfqs/${selected.id}/scoring-weights`, { method: "POST", body: JSON.stringify({ scoring_weights: values.weights }) });
      setSelected(updated);
      if (["CLOSED", "AWARDED"].includes(updated.status)) setComparison(await apiFetch<Comparison>(`/rfqs/${updated.id}/comparison`));
      message.success("Đã cập nhật trọng số");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không cập nhật được trọng số.");
    }
  }

  async function proposeSelection(values: { quotation_id: string; rationale: string }) {
    if (!selected) return;
    try {
      const created = await apiFetch<SupplierSelection>(`/rfqs/${selected.id}/selection`, { method: "POST", body: JSON.stringify(values) });
      setSelection(created);
      selectionForm.resetFields();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không đề xuất được nhà cung cấp.");
    }
  }

  async function decideSelection(values: DecisionFormValues) {
    if (!selection) return;
    const action = decisionOpen ? "reject" : "approve";
    setActionLoading(`${action}-${selection.id}`);
    try {
      const updated = await apiFetch<SupplierSelection>(`/selections/${selection.id}/${action}`, { method: "POST", body: JSON.stringify({ reason: values.reason ?? "" }) });
      setSelection(updated);
      setDecisionOpen(false);
      decisionForm.resetFields();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không xử lý được lựa chọn nhà cung cấp.");
    } finally {
      setActionLoading(null);
    }
  }

  async function generatePO() {
    if (!selection) return;
    try {
      const order = await apiFetch<PurchaseOrder>("/purchase-orders/generate", { method: "POST", headers: { "Idempotency-Key": crypto.randomUUID() }, body: JSON.stringify({ selection_id: selection.id }) });
      message.success(`Đã tạo ${order.number}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tạo được Purchase Order.");
    }
  }

  async function submitQuotation(values: QuotationFormValues) {
    if (!selected) return;
    try {
      const current = quotation ?? await apiFetch<Quotation>(`/rfqs/${selected.id}/quotation`, { method: "POST", body: JSON.stringify(values) });
      if (!quotation) setQuotation(current);
      setQuotation(await apiFetch<Quotation>(`/quotations/${current.id}/submit`, { method: "POST", body: JSON.stringify({}) }));
      message.success("Đã gửi báo giá. Bạn có thể ký số báo giá ngay bên dưới.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không gửi được báo giá.");
    }
  }

  async function respondInvitation(accept: boolean, reason = "") {
    if (!selected) return;
    setActionLoading(accept ? "accept" : "decline");
    try {
      const updated = await apiFetch<RFQ>(`/rfqs/${selected.id}/${accept ? "accept-invitation" : "decline-invitation"}`, { method: "POST", body: JSON.stringify({ reason }) });
      setSelected(updated);
      setDeclineOpen(false);
      declineForm.resetFields();
      if (accept) {
        form.setFieldsValue({ lines: updated.lines.map((line) => ({ rfq_line_id: line.id, offered_quantity: Number(line.quantity) })) });
        message.success("Đã xác nhận tham gia. Bạn có thể nhập báo giá.");
      }
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không gửi được phản hồi lời mời.");
    } finally {
      setActionLoading(null);
    }
  }

  async function reloadQuotation() {
    if (!selected) return;
    try { setQuotation(await apiFetch<Quotation>(`/rfqs/${selected.id}/quotation`)); }
    catch { setError("Không tải được báo giá."); }
  }

  async function signQuotation() {
    if (!quotation) return;
    // Mở tab trước khi gọi API để trình duyệt không chặn popup.
    const signWindow = window.open("about:blank", "_blank");
    setActionLoading("sign");
    try {
      const result = await apiFetch<{ sign_url: string }>(`/quotations/${quotation.id}/sign`, { method: "POST", body: JSON.stringify({}) });
      if (signWindow) signWindow.location.href = result.sign_url; else window.open(result.sign_url, "_blank");
      await reloadQuotation();
    } catch (err) {
      signWindow?.close();
      setError(err instanceof Error ? err.message : "Không tạo được yêu cầu ký số.");
    } finally {
      setActionLoading(null);
    }
  }

  const submittedQuotation = supplierView && quotation && quotation.status !== "DRAFT" ? quotation : null;
  const myInvitation = supplierView ? selected?.invitations[0] : undefined;
  const awaitingResponse = Boolean(myInvitation && ["INVITED", "VIEWED"].includes(myInvitation.status) && !quotation);
  const openRfqCount = rfqs.filter((item) => item.status === "OPEN").length;
  const closedRfqCount = rfqs.filter((item) => item.status === "CLOSED").length;
  const awardedRfqCount = rfqs.filter((item) => item.status === "AWARDED").length;

  return <AppShell>
    <div className="topbar"><div><p className="eyebrow">Đấu thầu &amp; Báo giá</p><h1 className="page-title">Yêu cầu báo giá (RFQ)</h1><p className="page-subtitle">{supplierView ? "Xem và phản hồi các hồ sơ mời báo giá từ doanh nghiệp mua." : "Khởi tạo hồ sơ mời báo giá, chấm điểm tự động và lựa chọn nhà cung cấp."}</p></div><Space wrap>{canPropose && <Button type="primary" icon={<PlusOutlined />} onClick={() => { rfqForm.resetFields(); setCreateOpen(true); }}>Tạo RFQ mới</Button>}<Button icon={<ReloadOutlined />} onClick={() => { void load(); void loadCreateOptions(); }}>Làm mới</Button></Space></div>
    <div className="fin-page-stats">
      <div className="fin-mini-stat"><div className="fin-mini-icon blue"><AuditOutlined /></div><div className="fin-mini-meta"><span>Tổng số RFQ</span><strong>{rfqs.length}</strong></div></div>
      <div className="fin-mini-stat"><div className="fin-mini-icon pink"><SendOutlined /></div><div className="fin-mini-meta"><span>Đang mở báo giá</span><strong>{openRfqCount}</strong></div></div>
      <div className="fin-mini-stat"><div className="fin-mini-icon gold"><ClockCircleOutlined /></div><div className="fin-mini-meta"><span>Đã đóng chờ chọn</span><strong>{closedRfqCount}</strong></div></div>
      <div className="fin-mini-stat"><div className="fin-mini-icon green"><TrophyOutlined /></div><div className="fin-mini-meta"><span>Đã chọn nhà cung cấp</span><strong>{awardedRfqCount}</strong></div></div>
    </div>
    {error && <Alert message={error} type="error" showIcon closable onClose={() => setError(null)} style={{ marginBottom: 20 }} />}
    <div className="panel"><Table loading={loading} dataSource={rfqs} rowKey="id" pagination={{ pageSize: 10 }} onRow={(record) => ({ onClick: () => void openRFQ(record), style: { cursor: "pointer" } })} columns={[
      { title: "Mã RFQ", dataIndex: "number", key: "number" },
      { title: "Tiêu đề mời báo giá", dataIndex: "title", key: "title" },
      { title: "Hạn nộp báo giá", dataIndex: "deadline", key: "deadline", render: (value: string) => new Date(value).toLocaleString("vi-VN") },
      ...(supplierView ? [{ title: "Lời mời", key: "invitation", render: (_: unknown, record: RFQ) => { const status = record.invitations[0]?.status; const label = status ? invitationLabels[status] : undefined; return label ? <Tag color={label.color}>{label.text}</Tag> : "—"; } }] : []),
      { title: "Trạng thái", dataIndex: "status", key: "status", render: (value: string) => <Tag color={value === "OPEN" ? "blue" : value === "AWARDED" ? "green" : value === "CANCELLED" ? "red" : "default"}>{labels[value] ?? value}</Tag> },
      { title: "Thao tác", key: "action", render: (_, record) => <Space size="small" wrap>
        <Button type="link" onClick={(event) => { event.stopPropagation(); void openRFQ(record); }}>Chi tiết</Button>
        {canPropose && record.status === "DRAFT" && <Button size="small" type="primary" icon={<SendOutlined />} loading={actionLoading === `publish-${record.id}`} onClick={(event) => { event.stopPropagation(); void transitionRFQ(record, "publish"); }}>Phát hành</Button>}
        {canPropose && record.status === "DRAFT" && <Button size="small" danger icon={<DeleteOutlined />} loading={actionLoading === `cancel-${record.id}`} onClick={(event) => { event.stopPropagation(); void transitionRFQ(record, "cancel"); }}>Hủy</Button>}
        {canPropose && record.status === "OPEN" && <Button size="small" icon={<CloseOutlined />} loading={actionLoading === `close-${record.id}`} onClick={(event) => { event.stopPropagation(); void transitionRFQ(record, "close"); }}>Đóng</Button>}
      </Space> },
    ]} /></div>
    <Drawer title={selected ? `${selected.number} · ${selected.title}` : "Chi tiết RFQ"} width="min(780px, 100vw)" open={Boolean(selected)} onClose={() => setSelected(null)}>
      {selected && <><p className="page-subtitle">Hạn phản hồi báo giá: {new Date(selected.deadline).toLocaleString("vi-VN")}</p>
        {!supplierView && selected.invitations.length > 0 && <Table style={{ marginBottom: 16 }} size="small" pagination={false} rowKey="id" dataSource={selected.invitations} columns={[
          { title: "Nhà cung cấp được mời", render: (_, item) => item.supplier.legal_name },
          { title: "Phản hồi", dataIndex: "status", render: (value: string, item) => { const label = invitationLabels[value] ?? { text: value, color: "default" }; return <><Tag color={label.color}>{label.text}</Tag>{item.decline_reason && <Typography.Text type="secondary" style={{ display: "block", marginTop: 4 }}>Lý do: {item.decline_reason}</Typography.Text>}</>; } },
          { title: "Thời điểm", render: (_, item) => item.responded_at || item.viewed_at ? new Date((item.responded_at || item.viewed_at) as string).toLocaleString("vi-VN") : "—" },
        ]} />}<Table size="small" pagination={false} rowKey="id" dataSource={selected.lines} columns={[{ title: "Hạng mục hàng hóa", dataIndex: "description" }, { title: "Số lượng", dataIndex: "quantity" }, { title: "ĐVT", dataIndex: "unit" }]} />
        {submittedQuotation && <div className="panel" style={{ marginTop: 24 }}>
          <div className="panel-heading"><h2>Báo giá đã gửi (lần {submittedQuotation.revision})</h2><Tag>{labels[submittedQuotation.status] ?? submittedQuotation.status}</Tag></div>
          <p>Tổng giá trị: <strong>{formatMoney(submittedQuotation.total)}</strong> (chưa VAT) · Giao hàng: {submittedQuotation.delivery_days ?? "—"} ngày · Trả chậm: {submittedQuotation.payment_term_days ?? "—"} ngày</p>
          <Space wrap>
            <span>Chữ ký số:</span><SignatureTag signature={submittedQuotation.signature} />
            {submittedQuotation.status === "SUBMITTED" && ["UNSIGNED", "REJECTED", "FAILED"].includes(submittedQuotation.signature.state) && <Button type="primary" icon={<SafetyCertificateOutlined />} loading={actionLoading === "sign"} onClick={() => void signQuotation()}>Ký số báo giá</Button>}
            {submittedQuotation.signature.state === "PENDING" && submittedQuotation.signature.sign_url && <Button icon={<ExportOutlined />} href={submittedQuotation.signature.sign_url} target="_blank">Mở trang ký số (OTP)</Button>}
            <Button icon={<ReloadOutlined />} onClick={() => void reloadQuotation()}>Làm mới</Button>
          </Space>
          <p className="formula-note">Ký số qua dịch vụ ký từ xa giả lập: hệ thống ký mã băm SHA-256 của nội dung báo giá. Nếu dữ liệu bị sửa sau khi ký, bên mua sẽ thấy cảnh báo chữ ký không hợp lệ.</p>
        </div>}
        {myInvitation && selected.status === "OPEN" && awaitingResponse && <Alert style={{ marginTop: 24 }} type="info" showIcon message="Bạn nhận được lời mời báo giá cho hồ sơ RFQ này" description="Xác nhận tham gia để nhập đơn giá chào thầu, hoặc từ chối kèm lý do. Bên mua sẽ nhận được thông báo ngay lập tức." action={<Space direction="vertical">
          <Button type="primary" icon={<CheckOutlined />} loading={actionLoading === "accept"} onClick={() => void respondInvitation(true)}>Xác nhận tham gia</Button>
          <Button danger icon={<CloseOutlined />} onClick={() => { declineForm.resetFields(); setDeclineOpen(true); }}>Từ chối tham gia</Button>
        </Space>} />}
        {myInvitation?.status === "DECLINED" && <Alert style={{ marginTop: 24 }} type="warning" showIcon message="Bạn đã từ chối lời mời báo giá này" description={myInvitation.decline_reason} />}
        {supplierView && selected.status === "OPEN" && !submittedQuotation && !awaitingResponse && myInvitation?.status !== "DECLINED" && <Form form={form} layout="vertical" onFinish={submitQuotation} style={{ marginTop: 24 }}><Form.List name="lines">{(fields) => fields.map((field) => <div className="rfq-quote-row" key={field.key}><Form.Item {...field} name={[field.name, "rfq_line_id"]} hidden><Input /></Form.Item><Form.Item {...field} name={[field.name, "offered_quantity"]} label="Số lượng chào" rules={[{ required: true }]}><InputNumber min={0} style={{ width: "100%" }} /></Form.Item><Form.Item {...field} name={[field.name, "unit_price"]} label="Đơn giá (VND)" rules={[{ required: true }]}><InputNumber min={0} style={{ width: "100%" }} /></Form.Item></div>)}</Form.List><Form.Item name="delivery_days" label="Thời gian giao hàng (ngày)"><InputNumber min={0} style={{ width: "100%" }} /></Form.Item><Form.Item name="payment_term_days" label="Số ngày trả chậm đề nghị (ví dụ: 30 ngày)"><InputNumber min={0} max={365} precision={0} style={{ width: "100%" }} placeholder="30" /></Form.Item><Form.Item name="payment_terms" label="Điều khoản thanh toán"><Input placeholder="Ví dụ: Chuyển khoản trong vòng 30 ngày sau nghiệm thu" /></Form.Item><Alert type="info" showIcon style={{ marginBottom: 12 }} message="Đơn giá chưa bao gồm thuế GTGT (VAT). Bên mua sẽ không thấy báo giá khi đang ở trạng thái nháp." /><Button type="primary" htmlType="submit" icon={<SendOutlined />}>Gửi báo giá chính thức</Button></Form>}
        {!supplierView && canPropose && ["DRAFT", "OPEN", "CLOSED"].includes(selected.status) && <Form form={weightsForm} layout="vertical" onFinish={saveWeights} style={{ marginTop: 24 }}><h3>Trọng số chấm điểm báo giá</h3><WeightInputs prefix={["weights"]} /><Button htmlType="submit">Lưu trọng số</Button></Form>}
        {!supplierView && comparison && <div style={{ marginTop: 24 }}><h3>So sánh các báo giá đã nộp</h3><Table size="small" pagination={false} scroll={{ x: "max-content" }} rowKey="id" dataSource={comparison.quotations} columns={[{ title: "Nhà cung cấp", render: (_, item) => item.supplier.legal_name }, { title: "Tổng tiền (chưa VAT)", dataIndex: "total", render: (value: string) => formatMoney(value) }, { title: "Giao hàng", dataIndex: "delivery_days", render: (value: number | null) => value !== null ? `${value} ngày` : "—" }, { title: "Hạn công nợ", dataIndex: "payment_term_days", render: (value: number | null) => value !== null ? `${value} ngày` : "—" }, { title: "Chữ ký số", render: (_, item) => <SignatureTag signature={item.signature} /> }, { title: "Trạng thái", dataIndex: "status", render: (value: string) => <Tag>{labels[value] ?? value}</Tag> }]} />
          <h3 style={{ marginTop: 20 }}>Bảng xếp hạng điểm tự động</h3>
          <Table<ScoreResult> size="small" pagination={false} scroll={{ x: "max-content" }} rowKey="quotation_id" dataSource={comparison.scoring.results} columns={[
            { title: "Hạng", dataIndex: "rank", width: 60 },
            { title: "Nhà cung cấp", render: (_, item) => item.supplier.legal_name },
            ...criteria.map((criterion) => ({ title: `${criterion.label} (${comparison.scoring.weights[criterion.key]}%)`, render: (_: unknown, item: ScoreResult) => criterion.key === "rating" && !item.rating_available ? <span title="Chưa có đánh giá, dùng mức trung lập 3/5">{item.components.rating}*</span> : item.components[criterion.key] })),
            { title: "Tổng điểm", dataIndex: "total_score", render: (value: string) => <strong>{value}</strong> },
          ]} />
          <p className="formula-note">{comparison.scoring.formula}. * Nhà cung cấp chưa có lịch sử đánh giá. Điểm số dùng để hỗ trợ ra quyết định; Trưởng phòng là người phê duyệt cuối cùng.</p>
          {selection && <Alert style={{ marginTop: 16 }} type={selection.status === "APPROVED" ? "success" : selection.status === "REJECTED" ? "error" : "info"} message={`Trạng thái lựa chọn: ${labels[selection.status] ?? selection.status}`} description={selection.rationale} action={<Space>{canApprove && selection.status === "PROPOSED" && <><Button size="small" type="primary" icon={<CheckOutlined />} onClick={() => { decisionForm.resetFields(); setDecisionOpen(false); void decideSelection({ reason: "" }); }}>Phê duyệt</Button><Button size="small" danger icon={<CloseOutlined />} onClick={() => { decisionForm.resetFields(); setDecisionOpen(true); }}>Từ chối</Button></>}{canPropose && selection.status === "APPROVED" && <Button size="small" type="primary" onClick={() => void generatePO()}>Tạo đơn hàng (PO)</Button>}</Space>} />}
          {canPropose && selected.status === "CLOSED" && (!selection || selection.status === "REJECTED") && <Form form={selectionForm} layout="vertical" onFinish={proposeSelection} style={{ marginTop: 18 }}><Form.Item name="quotation_id" label="Báo giá đề xuất trúng thầu" rules={[{ required: true, message: "Chọn báo giá." }]}><Select placeholder="Chọn báo giá nhà cung cấp" options={comparison.quotations.filter((item) => item.status === "SUBMITTED").map((item) => ({ value: item.id, label: `${item.supplier.legal_name} · ${Number(item.total).toLocaleString("vi-VN")} ₫` }))} /></Form.Item><Form.Item name="rationale" label="Lý do đề xuất lựa chọn" rules={[{ required: true, message: "Nhập lý do lựa chọn." }]}><Input.TextArea rows={3} placeholder="Nêu cơ sở lựa chọn (điểm tổng hợp cao nhất, thời gian giao hàng nhanh, chữ ký số hợp lệ...)" /></Form.Item><Button type="primary" htmlType="submit">Đề xuất chọn nhà cung cấp</Button></Form>}
        </div>}
      </>}
    </Drawer>
    <Modal title="Tạo hồ sơ mời báo giá (RFQ)" open={createOpen} footer={null} onCancel={() => setCreateOpen(false)} destroyOnHidden>
      <Form form={rfqForm} layout="vertical" onFinish={createRFQ} initialValues={{ weights: DEFAULT_WEIGHTS }}>
        <Form.Item name="request_id" label="Yêu cầu mua hàng đã phê duyệt" rules={[{ required: true, message: "Chọn yêu cầu mua hàng." }]}><Select placeholder="Chọn yêu cầu mua hàng đã duyệt" options={requests.map((request) => ({ value: request.id, label: `${request.number} · ${request.purpose}` }))} /></Form.Item>
        <Form.Item name="title" label="Tiêu đề hồ sơ mời báo giá" rules={[{ required: true, message: "Nhập tiêu đề RFQ." }]}><Input placeholder="Ví dụ: Mời báo giá cung cấp thiết bị phòng họp" /></Form.Item>
        <Form.Item name="deadline" label="Thời hạn nộp báo giá" rules={[{ required: true, message: "Chọn thời hạn nộp báo giá." }]}><DatePicker showTime placeholder="Chọn ngày và giờ đóng thầu" style={{ width: "100%" }} disabledDate={(date) => date.isBefore(dayjs(), "day")} /></Form.Item>
        <Form.Item name="supplier_company_ids" label="Danh sách nhà cung cấp được mời" rules={[{ required: true, message: "Chọn ít nhất hai nhà cung cấp." }]}><Select mode="multiple" placeholder="Chọn các nhà cung cấp trong danh bạ" options={suppliers.map((item) => ({ value: item.supplier_company.id, label: `${item.supplier_company.legal_name} · ${item.supplier_company.category}` }))} /></Form.Item>
        <Form.Item name="instructions" label="Hướng dẫn & Yêu cầu báo giá"><Input.TextArea rows={3} placeholder="Ví dụ: Báo giá chưa bao gồm thuế VAT 10%, yêu cầu ký số xác thực..." /></Form.Item>
        <p className="page-subtitle" style={{ marginBottom: 10 }}>Cấu hình trọng số chấm điểm tự động (Tổng = 100%)</p>
        <WeightInputs prefix={["weights"]} />
        <Button block size="large" type="primary" htmlType="submit">Tạo hồ sơ RFQ</Button>
      </Form>
    </Modal>
    <Modal title="Từ chối lời mời báo giá" open={declineOpen} footer={null} onCancel={() => setDeclineOpen(false)} destroyOnHidden>
      <Form form={declineForm} layout="vertical" onFinish={(values) => void respondInvitation(false, values.reason)}><Form.Item name="reason" label="Lý do từ chối" rules={[{ required: true, message: "Nhập lý do để bên mua nắm được." }]}><Input.TextArea rows={3} placeholder="Ví dụ: Tạm hết tồn kho, không đáp ứng kịp tiến độ giao hàng..." /></Form.Item><Button block size="large" danger type="primary" htmlType="submit" loading={actionLoading === "decline"}>Xác nhận từ chối</Button></Form>
    </Modal>
    <Modal title="Từ chối đề xuất chọn nhà cung cấp" open={decisionOpen} footer={null} onCancel={() => setDecisionOpen(false)} destroyOnHidden>
      <Form form={decisionForm} layout="vertical" onFinish={decideSelection}><Form.Item name="reason" label="Lý do từ chối" rules={[{ required: true, message: "Nhập lý do từ chối." }]}><Input.TextArea rows={4} /></Form.Item><Button block size="large" danger type="primary" htmlType="submit" loading={Boolean(actionLoading)}>Xác nhận từ chối</Button></Form>
    </Modal>
  </AppShell>;
}
