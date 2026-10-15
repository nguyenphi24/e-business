"use client";

import { Alert, Button, Form, Input, InputNumber, Modal, Rate, Space, Table, Tag, message } from "antd";
import { CheckOutlined, CloseOutlined, FileDoneOutlined, ReloadOutlined, StarOutlined, StopOutlined } from "@ant-design/icons";
import { useEffect, useState } from "react";

import AppShell from "@/components/app-shell";
import { ApiList, apiFetch, formatMoney, getStoredUser, hasRole, Invoice, PurchaseOrder } from "@/lib/api";

const labels: Record<string, string> = { DRAFT: "Nháp", ISSUED: "Đã phát hành", ACKNOWLEDGED: "Đã xác nhận", DECLINED: "Từ chối", PARTIALLY_DELIVERED: "Giao một phần", DELIVERED: "Đã giao", COMPLETED: "Hoàn tất", CANCELLED: "Đã hủy" };

type DeclineFormValues = { reason: string };
type EvaluationFormValues = { quality_score: number; delivery_score: number; comment?: string };
const invoiceLabels: Record<string, string> = { ISSUED: "Chờ thanh toán", PARTIALLY_PAID: "Đã trả một phần", PAID: "Đã thanh toán" };

export default function PurchaseOrdersPage() {
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deliveryOrder, setDeliveryOrder] = useState<PurchaseOrder | null>(null);
  const [declineOrder, setDeclineOrder] = useState<PurchaseOrder | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [deliveryForm] = Form.useForm();
  const [declineForm] = Form.useForm<DeclineFormValues>();
  const [evaluationOrder, setEvaluationOrder] = useState<PurchaseOrder | null>(null);
  const [evaluationForm] = Form.useForm<EvaluationFormValues>();
  const user = getStoredUser();
  const supplierView = user?.roles.includes("SUPPLIER") ?? false;
  const canCancel = hasRole(user, "BUYER", "MANAGER", "COMPANY_ADMIN", "SYSTEM_ADMIN");
  const canOperate = hasRole(user, "BUYER", "COMPANY_ADMIN", "SYSTEM_ADMIN");
  const canEvaluate = hasRole(user, "BUYER", "MANAGER", "COMPANY_ADMIN");

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const result = await apiFetch<ApiList<PurchaseOrder> | PurchaseOrder[]>("/purchase-orders");
      setOrders(Array.isArray(result) ? result : result.results ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tải được Purchase Order.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function transition(order: PurchaseOrder, action: "issue" | "acknowledge" | "complete" | "cancel") {
    setActionLoading(`${action}-${order.id}`);
    try {
      await apiFetch(`/purchase-orders/${order.id}/${action}`, { method: "POST", body: JSON.stringify({}) });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không cập nhật được trạng thái PO.");
    } finally {
      setActionLoading(null);
    }
  }

  function openDelivery(order: PurchaseOrder) {
    setDeliveryOrder(order);
    deliveryForm.setFieldsValue({ lines: order.lines.map((line) => ({ po_line_id: line.id })) });
  }

  async function submitDelivery(values: { lines: Array<{ po_line_id: number; delivered_quantity?: number }> }) {
    if (!deliveryOrder) return;
    const lines = values.lines.filter((line) => Number(line.delivered_quantity) > 0).map((line) => ({ po_line_id: line.po_line_id, delivered_quantity: line.delivered_quantity }));
    if (!lines.length) {
      setError("Nhập ít nhất một số lượng giao hàng lớn hơn 0.");
      return;
    }
    try {
      await apiFetch(`/purchase-orders/${deliveryOrder.id}/deliveries`, { method: "POST", body: JSON.stringify({ lines }) });
      setDeliveryOrder(null);
      deliveryForm.resetFields();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không ghi nhận được giao hàng.");
    }
  }

  async function issueInvoice(order: PurchaseOrder) {
    setActionLoading(`invoice-${order.id}`);
    try {
      const invoice = await apiFetch<Invoice>(`/purchase-orders/${order.id}/invoice`, { method: "POST", body: JSON.stringify({}) });
      message.success(`Đã lập ${invoice.number}, hạn thanh toán ${new Date(invoice.due_date).toLocaleDateString("vi-VN")}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không lập được hóa đơn.");
    } finally {
      setActionLoading(null);
    }
  }

  async function submitEvaluation(values: EvaluationFormValues) {
    if (!evaluationOrder) return;
    try {
      await apiFetch(`/purchase-orders/${evaluationOrder.id}/evaluation`, { method: "POST", body: JSON.stringify(values) });
      setEvaluationOrder(null);
      evaluationForm.resetFields();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không lưu được đánh giá.");
    }
  }

  async function decline(values: DeclineFormValues) {
    if (!declineOrder) return;
    setActionLoading(`decline-${declineOrder.id}`);
    try {
      await apiFetch(`/purchase-orders/${declineOrder.id}/decline`, { method: "POST", body: JSON.stringify(values) });
      setDeclineOrder(null);
      declineForm.resetFields();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không từ chối được Purchase Order.");
    } finally {
      setActionLoading(null);
    }
  }

  return <AppShell>
    <div className="topbar"><div><p className="eyebrow">Order management</p><h1 className="page-title">Purchase Orders</h1><p className="page-subtitle">Theo dõi phát hành, xác nhận, giao hàng, hóa đơn và đánh giá nhà cung cấp.</p></div><Button icon={<ReloadOutlined />} onClick={() => void load()}>Làm mới</Button></div>
    {error && <Alert message={error} type="error" showIcon closable onClose={() => setError(null)} style={{ marginBottom: 20 }} />}
    <div className="panel"><Table loading={loading} dataSource={orders} rowKey="id" pagination={{ pageSize: 10 }} expandable={{ expandedRowRender: (order) => <Table size="small" pagination={false} rowKey="id" dataSource={order.lines} columns={[{ title: "Hạng mục", dataIndex: "description" }, { title: "SL", dataIndex: "quantity" }, { title: "Đã giao", dataIndex: "delivered_quantity" }, { title: "Đơn giá", dataIndex: "unit_price", render: (value: string) => `${Number(value).toLocaleString("vi-VN")} ₫` }]} /> }} columns={[
      { title: "Mã PO", dataIndex: "number" },
      { title: "Nhà cung cấp", render: (_, item) => item.supplier.legal_name },
      { title: "Tổng", dataIndex: "total", render: (value: string) => formatMoney(value) },
      { title: "Công nợ", dataIndex: "payment_term_days", render: (value: number) => `Net ${value}` },
      { title: "Hóa đơn", key: "invoice", render: (_, order) => order.invoice ? <Tag color={order.invoice.status === "PAID" ? "green" : order.invoice.is_overdue ? "red" : "gold"}>{order.invoice.number} · {invoiceLabels[order.invoice.status] ?? order.invoice.status}</Tag> : "—" },
      { title: "Trạng thái", dataIndex: "status", render: (value: string) => <Tag color={value === "COMPLETED" ? "green" : value === "DECLINED" || value === "CANCELLED" ? "red" : "blue"}>{labels[value] ?? value}</Tag> },
      { title: "Thao tác", key: "actions", render: (_, order) => <Space size="small" wrap>
        {supplierView && ["DELIVERED", "COMPLETED"].includes(order.status) && !order.invoice && <Button type="link" icon={<FileDoneOutlined />} loading={actionLoading === `invoice-${order.id}`} onClick={() => void issueInvoice(order)}>Lập hóa đơn</Button>}
        {canEvaluate && order.status === "COMPLETED" && !order.evaluation && <Button type="link" icon={<StarOutlined />} onClick={() => { evaluationForm.resetFields(); setEvaluationOrder(order); }}>Đánh giá NCC</Button>}
        {order.evaluation && <Tag color="purple">Đánh giá {((order.evaluation.quality_score + order.evaluation.delivery_score) / 2).toFixed(1)}/5</Tag>}
        {canOperate && order.status === "DRAFT" && <Button type="link" loading={actionLoading === `issue-${order.id}`} onClick={() => void transition(order, "issue")}>Phát hành</Button>}
        {supplierView && order.status === "ISSUED" && <Button type="link" icon={<CheckOutlined />} loading={actionLoading === `acknowledge-${order.id}`} onClick={() => void transition(order, "acknowledge")}>Xác nhận</Button>}
        {supplierView && order.status === "ISSUED" && <Button type="link" danger icon={<CloseOutlined />} onClick={() => { declineForm.resetFields(); setDeclineOrder(order); }}>Từ chối</Button>}
        {canOperate && ["ISSUED", "ACKNOWLEDGED", "PARTIALLY_DELIVERED"].includes(order.status) && <Button type="link" onClick={() => openDelivery(order)}>Ghi nhận giao hàng</Button>}
        {canOperate && order.status === "DELIVERED" && <Button type="link" loading={actionLoading === `complete-${order.id}`} onClick={() => void transition(order, "complete")}>Hoàn tất</Button>}
        {canCancel && ["DRAFT", "ISSUED", "ACKNOWLEDGED"].includes(order.status) && <Button type="link" danger icon={<StopOutlined />} loading={actionLoading === `cancel-${order.id}`} onClick={() => void transition(order, "cancel")}>Hủy PO</Button>}
      </Space> },
    ]} /></div>
    <Modal title={deliveryOrder ? `Ghi nhận giao hàng · ${deliveryOrder.number}` : "Ghi nhận giao hàng"} open={Boolean(deliveryOrder)} footer={null} onCancel={() => setDeliveryOrder(null)} destroyOnHidden>
      <Form form={deliveryForm} layout="vertical" onFinish={submitDelivery}><Form.List name="lines">{(fields) => fields.map((field) => { const line = deliveryOrder?.lines[field.name]; return <div className="delivery-row" key={field.key}><Form.Item {...field} name={[field.name, "po_line_id"]} hidden><InputNumber /></Form.Item><div className="delivery-line-label">{line?.description} · đã giao {line?.delivered_quantity}/{line?.quantity} {line?.unit}</div><Form.Item {...field} name={[field.name, "delivered_quantity"]} label="Giao thêm"><InputNumber min={0} /></Form.Item></div>; })}</Form.List><Button block htmlType="submit" type="primary">Lưu giao hàng</Button></Form>
    </Modal>
    <Modal title={evaluationOrder ? `Đánh giá nhà cung cấp · ${evaluationOrder.number}` : "Đánh giá nhà cung cấp"} open={Boolean(evaluationOrder)} footer={null} onCancel={() => setEvaluationOrder(null)} destroyOnHidden>
      <Form form={evaluationForm} layout="vertical" onFinish={submitEvaluation}>
        <p>{evaluationOrder?.supplier.legal_name} — điểm này dùng làm tiêu chí uy tín khi chấm báo giá ở các RFQ sau.</p>
        <Form.Item name="quality_score" label="Chất lượng" rules={[{ required: true, message: "Chọn điểm chất lượng." }]}><Rate /></Form.Item>
        <Form.Item name="delivery_score" label="Giao hàng" rules={[{ required: true, message: "Chọn điểm giao hàng." }]}><Rate /></Form.Item>
        <Form.Item name="comment" label="Nhận xét"><Input.TextArea rows={3} /></Form.Item>
        <Button block htmlType="submit" type="primary">Lưu đánh giá</Button>
      </Form>
    </Modal>
    <Modal title={declineOrder ? `Từ chối PO · ${declineOrder.number}` : "Từ chối PO"} open={Boolean(declineOrder)} footer={null} onCancel={() => setDeclineOrder(null)} destroyOnHidden>
      <Form form={declineForm} layout="vertical" onFinish={decline}><Form.Item name="reason" label="Lý do từ chối" rules={[{ required: true, message: "Nhập lý do từ chối." }]}><Input.TextArea rows={4} /></Form.Item><Button block danger type="primary" htmlType="submit" loading={Boolean(actionLoading)}>Xác nhận từ chối</Button></Form>
    </Modal>
  </AppShell>;
}
