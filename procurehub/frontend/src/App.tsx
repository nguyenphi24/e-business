import { Navigate, Route, Routes } from "react-router-dom";

import DashboardPage from "@/app/dashboard/page";
import InvoicesPage from "@/app/invoices/page";
import LoginPage from "@/app/login/page";
import PurchaseOrdersPage from "@/app/purchase-orders/page";
import PurchaseRequestsPage from "@/app/purchase-requests/page";
import RFQsPage from "@/app/rfqs/page";
import Providers from "@/app/providers";
import "@/app/globals.css";

export default function App() {
  return (
    <Providers>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/purchase-requests" element={<PurchaseRequestsPage />} />
        <Route path="/rfqs" element={<RFQsPage />} />
        <Route path="/purchase-orders" element={<PurchaseOrdersPage />} />
        <Route path="/invoices" element={<InvoicesPage />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Providers>
  );
}
