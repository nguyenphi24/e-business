import { Badge, Button, Empty, Popover } from "antd";
import { BellOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";

import { AppNotification } from "@/lib/api";
import { useNotifications } from "@/lib/notifications";

function formatTime(value: string) {
  return new Intl.DateTimeFormat("vi-VN", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}

export default function NotificationBell() {
  const navigate = useNavigate();
  const { items, unread, live, markRead, markAllRead } = useNotifications(true);

  async function open(item: AppNotification) {
    await markRead(item);
    if (item.payload.path) navigate(item.payload.path);
  }

  const content = <div className="notification-panel">
    <div className="notification-head">
      <strong>Thông báo</strong>
      <span className={`live-dot ${live ? "on" : ""}`} title={live ? "Đang nhận realtime" : "Đang kết nối lại"} />
      <Button size="small" type="link" disabled={unread === 0} onClick={() => void markAllRead()}>Đánh dấu đã đọc</Button>
    </div>
    {items.length === 0 ? <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Chưa có thông báo" /> : <div className="notification-list">
      {items.map((item) => <button type="button" key={item.id} className={`notification-item ${item.read_at ? "" : "unread"}`} onClick={() => void open(item)}>
        <span className="notification-title">{item.title}</span>
        <span className="notification-time">{formatTime(item.created_at)}</span>
      </button>)}
    </div>}
  </div>;

  return <Popover content={content} trigger="click" placement="rightTop">
    <button className="sidebar-link" type="button" title="Thông báo">
      <Badge count={unread} size="small" offset={[4, -2]}><BellOutlined /></Badge><span>Thông báo</span>
    </button>
  </Popover>;
}
