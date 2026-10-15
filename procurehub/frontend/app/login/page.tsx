"use client";

import { Form, Input, Button, Alert } from "antd";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { login } from "@/lib/api";

export default function LoginPage() {
  const navigate = useNavigate();
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

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="brand-mark"><i className="brand-dot" />ProcureHub</div>
        <h1 className="auth-title">Mua sắm rõ ràng hơn.</h1>
        <p className="auth-subtitle">Workspace Source-to-Pay cho bên mua, nhà cung cấp và kế toán.</p>
        {error && <Alert message={error} type="error" showIcon style={{ marginBottom: 18 }} />}
        <Form layout="vertical" onFinish={submit} requiredMark={false}>
          <Form.Item label="Email" name="email" rules={[{ required: true, type: "email", message: "Nhập email hợp lệ." }]}>
            <Input size="large" placeholder="you@company.com" />
          </Form.Item>
          <Form.Item label="Mật khẩu" name="password" rules={[{ required: true, message: "Nhập mật khẩu." }]}>
            <Input.Password size="large" placeholder="••••••••" />
          </Form.Item>
          <Button block htmlType="submit" loading={loading} size="large" type="primary">Đăng nhập</Button>
        </Form>
        <div className="demo-hint">Mật khẩu demo: `Demo@2026`<br />Buyer: `buyer@vnptmedia.demo` · Manager: `manager@vnptmedia.demo`<br />Finance: `finance@vnptmedia.demo` · Supplier: `sales@techvision.demo`, `sales@digitalsupply.demo`</div>
      </div>
    </div>
  );
}
