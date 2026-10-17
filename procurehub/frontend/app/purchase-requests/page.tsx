"use client";

import dayjs from "dayjs";
import { Alert, Button, DatePicker, Form, Input, InputNumber, Modal, Space, Table, Tag } from "antd";
import { CheckCircleOutlined, CheckOutlined, ClockCircleOutlined, CloseOutlined, EditOutlined, FileTextOutlined, PlusOutlined, ReloadOutlined, SendOutlined, StopOutlined, WalletOutlined } from "@ant-design/icons";
import { useEffect, useState } from "react";

import AppShell from "@/components/app-shell";
import { apiFetch, ApiList, formatMoney, getStoredUser, PurchaseRequest, PurchaseRequestInput } from "@/lib/api";

const labels: Record<string, string> = {
  DRAFT: "Nháp",
  PENDING_APPROVAL: "Chờ duyệt",
  APPROVED: "Đã duyệt",
  REJECTED: "Từ chối",
  CANCELLED: "Đã hủy",
};

type RequestFormValues = {
  purpose: string;
  needed_by: dayjs.Dayjs;
  estimated_budget?: number;
  description: string;
  quantity: number;
  unit: string;
};

type DecisionFormValues = { reason?: string };

export default function PurchaseRequestsPage() {
  const [items, setItems] = useState<PurchaseRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<PurchaseRequest | null>(null);
  const [decision, setDecision] = useState<{ request: PurchaseRequest; action: "approve" | "reject" } | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [form] = Form.useForm<RequestFormValues>();
  const [decisionForm] = Form.useForm<DecisionFormValues>();
  const user = getStoredUser();
  const canApprove = user?.roles.some((role) => ["MANAGER", "SYSTEM_ADMIN"].includes(role)) ?? false;

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const result = await apiFetch<ApiList<PurchaseRequest> | PurchaseRequest[]>("/purchase-requests");
      setItems(Array.isArray(result) ? result : result.results ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tải được dữ liệu.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (getStoredUser()) void load();
    else setError("Vui lòng đăng nhập để tiếp tục.");
  }, []);

  function openCreate() {
    setEditing(null);
    form.resetFields();
    setOpen(true);
  }

  function openEdit(request: PurchaseRequest) {
    setEditing(request);
    form.setFieldsValue({
      purpose: request.purpose,
      needed_by: dayjs(request.needed_by),
      estimated_budget: request.estimated_budget ? Number(request.estimated_budget) : undefined,
      description: request.lines[0]?.description ?? "",
      quantity: Number(request.lines[0]?.quantity ?? 1),
      unit: request.lines[0]?.unit ?? "cái",
    });
    setOpen(true);
  }

  async function submit(values: RequestFormValues) {
    const payload: PurchaseRequestInput = {
      purpose: values.purpose,
      needed_by: values.needed_by.format("YYYY-MM-DD"),
      currency: "VND",
      estimated_budget: values.estimated_budget !== undefined && values.estimated_budget !== null ? String(values.estimated_budget) : null,
      lines: [{ description: values.description, quantity: String(values.quantity), unit: values.unit }],
    };
    try {
      if (editing) await apiFetch(`/purchase-requests/${editing.id}`, { method: "PATCH", body: JSON.stringify(payload) });
      else await apiFetch("/purchase-requests", { method: "POST", body: JSON.stringify(payload) });
      setOpen(false);
      form.resetFields();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không lưu được yêu cầu mua hàng.");
    }
  }

  async function transition(request: PurchaseRequest, action: "submit" | "cancel") {
    setActionLoading(`${action}-${request.id}`);
    try {
      await apiFetch(`/purchase-requests/${request.id}/${action}`, { method: "POST", body: JSON.stringify({}) });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không cập nhật được yêu cầu mua hàng.");
    } finally {
      setActionLoading(null);
    }
  }

  function openDecision(request: PurchaseRequest, action: "approve" | "reject") {
    decisionForm.resetFields();
    setDecision({ request, action });
  }

  async function decide(values: DecisionFormValues) {
    if (!decision) return;
    setActionLoading(`${decision.action}-${decision.request.id}`);
    try {
      await apiFetch(`/purchase-requests/${decision.request.id}/${decision.action}`, {
        method: "POST",
        body: JSON.stringify({ reason: values.reason ?? "" }),
      });
      setDecision(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không xử lý được phê duyệt.");
    } finally {
      setActionLoading(null);
    }
  }

  const pendingCount = items.filter((item) => item.status === "PENDING_APPROVAL").length;
  const approvedCount = items.filter((item) => item.status === "APPROVED").length;
  const totalBudget = items.reduce((sum, item) => sum + Number(item.estimated_budget ?? 0), 0);

  return <AppShell>
    <div className="topbar">
      <div><p className="eyebrow">Quy trình mua sắm</p><h1 className="page-title">Yêu cầu mua hàng</h1><p className="page-subtitle">Tạo, gửi duyệt và phê duyệt các đề nghị mua sắm nội bộ trong doanh nghiệp.</p></div>
      <Space wrap><Button icon={<ReloadOutlined />} onClick={() => void load()}>Làm mới</Button><Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>Tạo yêu cầu</Button></Space>
    </div>
    <div className="fin-page-stats">
      <div className="fin-mini-stat"><div className="fin-mini-icon blue"><FileTextOutlined /></div><div className="fin-mini-meta"><span>Tổng yêu cầu</span><strong>{items.length}</strong></div></div>
      <div className="fin-mini-stat"><div className="fin-mini-icon pink"><ClockCircleOutlined /></div><div className="fin-mini-meta"><span>Chờ phê duyệt</span><strong>{pendingCount}</strong></div></div>
      <div className="fin-mini-stat"><div className="fin-mini-icon green"><CheckCircleOutlined /></div><div className="fin-mini-meta"><span>Đã phê duyệt</span><strong>{approvedCount}</strong></div></div>
      <div className="fin-mini-stat"><div className="fin-mini-icon gold"><WalletOutlined /></div><div className="fin-mini-meta"><span>Tổng ngân sách dự kiến</span><strong>{formatMoney(String(totalBudget))}</strong></div></div>
    </div>
    {error && <Alert message={error} type="error" showIcon closable onClose={() => setError(null)} style={{ marginBottom: 20 }} />}
    <div className="panel"><Table loading={loading} dataSource={items} rowKey="id" pagination={{ pageSize: 10 }} columns={[
      { title: "Mã yêu cầu", dataIndex: "number", key: "number" },
      { title: "Mục đích mua sắm", dataIndex: "purpose", key: "purpose" },
      { title: "Cần trước ngày", dataIndex: "needed_by", key: "needed_by" },
      { title: "Ngân sách ước tính", dataIndex: "estimated_budget", key: "estimated_budget", render: (value: string | null) => formatMoney(value) },
      { title: "Người đề nghị", key: "requester", render: (_, item) => item.requester.full_name },
      { title: "Trạng thái", dataIndex: "status", key: "status", render: (status: string) => <Tag color={status === "APPROVED" ? "green" : status === "REJECTED" ? "red" : status === "PENDING_APPROVAL" ? "orange" : "blue"}>{labels[status] ?? status}</Tag> },
      { title: "Thao tác", key: "actions", render: (_, request) => {
        const owner = request.requester.id === user?.id;
        const busy = actionLoading?.endsWith(request.id) ?? false;
        return <Space size="small" wrap>
          {owner && ["DRAFT", "REJECTED"].includes(request.status) && <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(request)}>Sửa</Button>}
          {owner && ["DRAFT", "REJECTED"].includes(request.status) && <Button size="small" type="primary" icon={<SendOutlined />} loading={busy} onClick={() => void transition(request, "submit")}>Gửi duyệt</Button>}
          {owner && ["DRAFT", "REJECTED"].includes(request.status) && <Button size="small" danger icon={<StopOutlined />} loading={busy} onClick={() => void transition(request, "cancel")}>Hủy</Button>}
          {canApprove && request.status === "PENDING_APPROVAL" && <Button size="small" type="primary" icon={<CheckOutlined />} loading={busy} onClick={() => openDecision(request, "approve")}>Duyệt</Button>}
          {canApprove && request.status === "PENDING_APPROVAL" && <Button size="small" danger icon={<CloseOutlined />} loading={busy} onClick={() => openDecision(request, "reject")}>Từ chối</Button>}
        </Space>;
      }},
    ]} /></div>
    <Modal title={editing ? `Chỉnh sửa yêu cầu · ${editing.number}` : "Tạo yêu cầu mua hàng mới"} open={open} footer={null} onCancel={() => setOpen(false)} destroyOnHidden>
      <Form form={form} layout="vertical" onFinish={submit}>
        <Form.Item label="Mục đích mua sắm" name="purpose" rules={[{ required: true, message: "Nhập mục đích mua sắm." }]}><Input placeholder="Ví dụ: Trang bị thiết bị phòng họp tầng 5" /></Form.Item>
        <Form.Item label="Cần trước ngày" name="needed_by" rules={[{ required: true, message: "Chọn ngày cần hàng." }]}><DatePicker placeholder="Chọn ngày cần nhận hàng" style={{ width: "100%" }} /></Form.Item>
        <Form.Item label="Ngân sách ước tính (VND, không bắt buộc)" name="estimated_budget" extra="Dùng làm mức giá tham chiếu để tính chỉ số KPI tiết kiệm ngân sách."><InputNumber min={0} step={1000000} placeholder="Ví dụ: 150000000" style={{ width: "100%" }} /></Form.Item>
        <Form.Item label="Mô tả hàng hóa / dịch vụ" name="description" rules={[{ required: true, message: "Nhập mô tả hàng hóa." }]}><Input placeholder="Ví dụ: Màn hình tương tác 24 inch" /></Form.Item>
        <div className="pr-inline-fields">
          <Form.Item label="Số lượng" name="quantity" rules={[{ required: true, message: "Nhập số lượng." }]}><InputNumber min={0.001} placeholder="10" style={{ width: "100%" }} /></Form.Item>
          <Form.Item label="Đơn vị tính" name="unit" rules={[{ required: true, message: "Nhập đơn vị tính." }]}><Input placeholder="Ví dụ: cái, bộ, chiếc" /></Form.Item>
        </div>
        <Button block htmlType="submit" size="large" type="primary">{editing ? "Lưu thay đổi" : "Tạo yêu cầu mua hàng"}</Button>
      </Form>
    </Modal>
    <Modal title={decision?.action === "approve" ? "Phê duyệt yêu cầu mua hàng" : "Từ chối yêu cầu mua hàng"} open={Boolean(decision)} footer={null} onCancel={() => setDecision(null)} destroyOnHidden>
      <Form form={decisionForm} layout="vertical" onFinish={decide}>
        <p>{decision?.request.number} · {decision?.request.purpose}</p>
        <Form.Item label={decision?.action === "approve" ? "Ghi chú phê duyệt (không bắt buộc)" : "Lý do từ chối"} name="reason" rules={decision?.action === "reject" ? [{ required: true, message: "Nhập lý do từ chối." }] : undefined}><Input.TextArea rows={4} placeholder={decision?.action === "approve" ? "Nhập ghi chú nếu có..." : "Nêu rõ lý do từ chối để người đề nghị điều chỉnh..."} /></Form.Item>
        <Button block htmlType="submit" size="large" type="primary" danger={decision?.action === "reject"} loading={Boolean(actionLoading)}>{decision?.action === "approve" ? "Xác nhận phê duyệt" : "Xác nhận từ chối"}</Button>
      </Form>
    </Modal>
  </AppShell>;
}
