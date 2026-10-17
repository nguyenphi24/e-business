"use client";

import { Form, Input, Button, Alert } from "antd";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { CloverLogo } from "@/components/app-shell";
import { login } from "@/lib/api";

const DEMO_ACCOUNTS = [
  { label: "Chuyên viên mua hàng", email: "buyer@vnptmedia.demo", dot: "fin-dot-blue" },
  { label: "Trưởng phòng phê duyệt", email: "manager@vnptmedia.demo", dot: "fin-dot-pink" },
  { label: "Kế toán thanh toán", email: "finance@vnptmedia.demo", dot: "fin-dot-gold" },
  { label: "NCC TechVision", email: "sales@techvision.demo", dot: "fin-dot-blue" },
  { label: "NCC Digital Supply", email: "sales@digitalsupply.demo", dot: "fin-dot-pink" },
];

export default function LoginPage() {
  const navigate = useNavigate();
  const [form] = Form.useForm<{ email: string; password: string }>();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(values: { email: string; password: string }) {
    setLoading(true);
    setError(null);
    try {
      await login(values.email, values.password);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Đăng nhập thất bại.");
    } finally {
      setLoading(false);
    }
  }

  function fillDemoAccount(email: string) {
    form.setFieldsValue({ email, password: "Demo@2026" });
    setError(null);
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="brand-mark">
          <CloverLogo />
          <div className="brand-text">
            <strong>ProcureHub</strong>
            <span>Mua sắm &amp; Tài chính B2B</span>
          </div>
        </div>
        <h1 className="auth-title">Mua sắm minh bạch hơn.</h1>
        <p className="auth-subtitle">
          Hệ thống quản lý mua sắm và thanh toán điện tử B2B dành cho bên mua, nhà cung cấp và bộ phận tài chính — kế toán.
        </p>
        {error && <Alert message={error} type="error" showIcon style={{ marginBottom: 18 }} />}
        <Form form={form} layout="vertical" onFinish={submit} requiredMark={false}>
          <Form.Item
            label="Email doanh nghiệp"
            name="email"
            rules={[{ required: true, type: "email", message: "Nhập email hợp lệ." }]}
          >
            <Input size="large" placeholder="ten.ban@doanhnghiep.vn" />
          </Form.Item>
          <Form.Item
            label="Mật khẩu"
            name="password"
            rules={[{ required: true, message: "Nhập mật khẩu." }]}
          >
            <Input.Password size="large" placeholder="••••••••" />
          </Form.Item>
          <Button block htmlType="submit" loading={loading} size="large" type="primary">
            Đăng nhập hệ thống
          </Button>
        </Form>
        <div className="demo-hint">
          <div className="demo-accounts-title">Chọn nhanh tài khoản mẫu (Mật khẩu: Demo@2026)</div>
          <div className="demo-accounts-grid">
            {DEMO_ACCOUNTS.map((acc) => (
              <button
                key={acc.email}
                type="button"
                className="demo-account-chip"
                onClick={() => fillDemoAccount(acc.email)}
              >
                <i className={`fin-dot ${acc.dot}`} />
                {acc.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
