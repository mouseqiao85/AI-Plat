import { useState } from "react";
import {
  AppstoreOutlined, ToolOutlined, StarOutlined,
  EditOutlined, SettingOutlined, RightOutlined,
  DownOutlined, MenuFoldOutlined, MenuUnfoldOutlined,
} from "@ant-design/icons";

interface MenuItem {
  key: string;
  label: string;
  icon: React.ReactNode;
  children?: { key: string; label: string }[];
}

const menuItems: MenuItem[] = [
  { key: "projects", label: "项目管理", icon: <AppstoreOutlined /> },
  {
    key: "tech", label: "技术管理", icon: <ToolOutlined />,
    children: [
      { key: "efficiency", label: "效率工具" },
      { key: "other", label: "其他场景" },
    ],
  },
  { key: "favorites", label: "我的收藏", icon: <StarOutlined /> },
  { key: "my-creations", label: "我的创建", icon: <EditOutlined /> },
  { key: "settings", label: "设置", icon: <SettingOutlined /> },
];

interface Props {
  collapsed: boolean;
  onToggleCollapse: () => void;
  activeKey: string;
  onSelect: (key: string) => void;
}

export default function MarketSidebar({ collapsed, onToggleCollapse, activeKey, onSelect }: Props) {
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({
    tech: true,
  });

  const toggleGroup = (key: string) => {
    setExpandedGroups((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const isActive = (key: string) => activeKey === key;

  return (
    <div className={`market-sidebar${collapsed ? " collapsed" : ""}`}>
      <div className="market-sidebar-toggle" onClick={onToggleCollapse}>
        {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
      </div>

      <div className="market-sidebar-menu">
        {menuItems.map((item) => {
          if (item.children) {
            const isExpanded = expandedGroups[item.key];
            return (
              <div key={item.key} className="market-sidebar-group">
                <div
                  className={`market-sidebar-item${isActive(item.key) ? " active" : ""}`}
                  onClick={() => toggleGroup(item.key)}
                >
                  <span className="market-sidebar-icon">{item.icon}</span>
                  {!collapsed && (
                    <>
                      <span className="market-sidebar-label">{item.label}</span>
                      <span className="market-sidebar-arrow">
                        {isExpanded ? <DownOutlined style={{ fontSize: 10 }} /> : <RightOutlined style={{ fontSize: 10 }} />}
                      </span>
                    </>
                  )}
                </div>
                {!collapsed && isExpanded && (
                  <div className="market-sidebar-submenu">
                    {item.children.map((child) => (
                      <div
                        key={child.key}
                        className={`market-sidebar-subitem${isActive(child.key) ? " active" : ""}`}
                        onClick={() => onSelect(child.key)}
                      >
                        {child.label}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          }

          return (
            <div
              key={item.key}
              className={`market-sidebar-item${isActive(item.key) ? " active" : ""}`}
              onClick={() => onSelect(item.key)}
            >
              <span className="market-sidebar-icon">{item.icon}</span>
              {!collapsed && <span className="market-sidebar-label">{item.label}</span>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
