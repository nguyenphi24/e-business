import { ConfigProvider } from "antd";
import viVN from "antd/locale/vi_VN";
import dayjs from "dayjs";
import "dayjs/locale/vi";

dayjs.locale("vi");

export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ConfigProvider
      locale={viVN}
      theme={{
        token: {
          colorPrimary: "#3A64F6",
          colorInfo: "#3A64F6",
          colorSuccess: "#10B981",
          colorWarning: "#F5B000",
          colorError: "#FF4D6D",
          colorTextBase: "#14172C",
          colorTextSecondary: "#7C8498",
          colorBorder: "#E6EAF2",
          colorBorderSecondary: "#EEF1F7",
          colorBgContainer: "#FFFFFF",
          colorBgLayout: "#F4F6FB",
          borderRadius: 12,
          borderRadiusLG: 18,
          fontFamily:
            "'Plus Jakarta Sans', Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
          fontSize: 14,
          boxShadowSecondary: "0 12px 32px rgba(20, 23, 44, 0.06)",
        },
        components: {
          Button: {
            borderRadius: 12,
            controlHeight: 38,
            controlHeightLG: 44,
            fontWeight: 600,
            primaryShadow: "0 8px 18px rgba(58, 100, 246, 0.25)",
          },
          Table: {
            headerBg: "#F8FAFF",
            headerColor: "#7C8498",
            headerSplitColor: "transparent",
            rowHoverBg: "#F5F8FF",
            borderColor: "#EEF1F7",
            cellPaddingBlock: 14,
          },
          Card: {
            borderRadiusLG: 22,
          },
          Modal: {
            borderRadiusLG: 22,
          },
          Input: {
            controlHeight: 42,
            controlHeightLG: 46,
            borderRadius: 12,
          },
          InputNumber: {
            controlHeight: 42,
            controlHeightLG: 46,
            borderRadius: 12,
          },
          DatePicker: {
            controlHeight: 42,
            controlHeightLG: 46,
            borderRadius: 12,
          },
          Select: {
            controlHeight: 42,
            controlHeightLG: 46,
            borderRadius: 12,
          },
          Tag: {
            borderRadiusSM: 999,
          },
        },
      }}
    >
      {children}
    </ConfigProvider>
  );
}
