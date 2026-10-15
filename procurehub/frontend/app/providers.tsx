import { ConfigProvider } from "antd";

export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: "#176b87",
          colorInfo: "#176b87",
          borderRadius: 10,
          fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
        },
      }}
    >
      {children}
    </ConfigProvider>
  );
}
