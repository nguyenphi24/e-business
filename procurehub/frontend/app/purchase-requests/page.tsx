"use client";

import dayjs from "dayjs";
import { Alert, Button, DatePicker, Form, Input, InputNumber, Modal, Space, Table, Tag } from "antd";
import { CheckOutlined, CloseOutlined, EditOutlined, PlusOutlined, ReloadOutlined, SendOutlined, StopOutlined } from "@ant-design/icons";
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
      setError(err instanceof Error ? err.message : "Không lưu được Purchase Request.");
    }
  }

  async function transition(request: PurchaseRequest, action: "submit" | "cancel") {
    setActionLoading(`${action}-${request.id}`);
    try {
      await apiFetch(`/purchase-requests/${request.id}/${action}`, { method: "POST", body: JSON.stringify({}) });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không cập nhật được Purchase Request.");
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

  return <AppShell>
    <div className="topbar">
      <div><p className="eyebrow">Source-to-Order</p><h1 className="page-title">Purchase Requests</h1><p className="page-subtitle">Tạo, gửi và phê duyệt yêu cầu mua hàng trong công ty.</p></div>
      <Space wrap><Button icon={<ReloadOutlined />} onClick={() => void load()}>Làm mới</Button><Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>Tạo yêu cầu</Button></Space>
    </div>
    {error && <Alert message={error} type="error" showIcon closable onClose={() => setError(null)} style={{ marginBottom: 20 }} />}
    <div className="panel"><Table loading={loading} dataSource={items} rowKey="id" pagination={{ pageSize: 10 }} columns={[
      { title: "Mã yêu cầu", dataIndex: "number", key: "number" },
      { title: "Mục đích", dataIndex: "purpose", key: "purpose" },
      { title: "Cần trước", dataIndex: "needed_by", key: "needed_by" },
      { title: "Ngân sách ước tính", dataIndex: "estimated_budget", key: "estimated_budget", render: (value: string | null) => formatMoney(value) },
      { title: "Người yêu cầu", key: "requester", render: (_, item) => item.requester.full_name },
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
    <Modal title={editing ? `Sửa yêu cầu · ${editing.number}` : "Tạo Purchase Request"} open={open} footer={null} onCancel={() => setOpen(false)} destroyOnHidden>
      <Form form={form} layout="vertical" onFinish={submit}>
        <Form.Item label="Mục đích" name="purpose" rules={[{ required: true, message: "Nhập mục đích." }]}><Input placeholder="Ví dụ: Thiết bị phòng họp" /></Form.Item>
        <Form.Item label="Cần trước ngày" name="needed_by" rules={[{ required: true, message: "Chọn ngày cần hàng." }]}><DatePicker style={{ width: "100%" }} /></Form.Item>
        <Form.Item label="Ngân sách ước tính (VND, không bắt buộc)" name="estimated_budget" extra="Dùng làm giá tham chiếu cho KPI tiết kiệm."><InputNumber min={0} step={1000000} style={{ width: "100%" }} /></Form.Item>
        <Form.Item label="Mô tả hàng hóa" name="description" rules={[{ required: true, message: "Nhập mô tả." }]}><Input placeholder="Ví dụ: Màn hình 24 inch" /></Form.Item>
        <Space.Compact block className="pr-inline-fields"><Form.Item label="Số lượng" name="quantity" rules={[{ required: true, message: "Nhập số lượng." }]} style={{ width: "50%" }}><InputNumber min={0.001} style={{ width: "100%" }} /></Form.Item><Form.Item label="Đơn vị" name="unit" rules={[{ required: true, message: "Nhập đơn vị." }]} style={{ width: "50%" }}><Input placeholder="cái" /></Form.Item></Space.Compact>
        <Button block htmlType="submit" type="primary">{editing ? "Lưu thay đổi" : "Tạo yêu cầu"}</Button>
      </Form>
    </Modal>
    <Modal title={decision?.action === "approve" ? "Duyệt Purchase Request" : "Từ chối Purchase Request"} open={Boolean(decision)} footer={null} onCancel={() => setDecision(null)} destroyOnHidden>
      <Form form={decisionForm} layout="vertical" onFinish={decide}>
        <p>{decision?.request.number} · {decision?.request.purpose}</p>
        <Form.Item label={decision?.action === "approve" ? "Ghi chú (không bắt buộc)" : "Lý do từ chối"} name="reason" rules={decision?.action === "reject" ? [{ required: true, message: "Nhập lý do từ chối." }] : undefined}><Input.TextArea rows={4} /></Form.Item>
        <Button block htmlType="submit" type="primary" danger={decision?.action === "reject"} loading={Boolean(actionLoading)}>{decision?.action === "approve" ? "Xác nhận duyệt" : "Xác nhận từ chối"}</Button>
      </Form>
    </Modal>
  </AppShell>;
}
