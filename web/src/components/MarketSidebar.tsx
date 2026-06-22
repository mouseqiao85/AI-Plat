import {
  AppstoreOutlined, ToolOutlined, DeploymentUnitOutlined,
  MenuFoldOutlined, MenuUnfoldOutlined,
} from "@ant-design/icons";

interface MenuItem {
  key: string;
  label: string;
  icon: React.ReactNode;
}

const menuItems: MenuItem[] = [
  { key: "project-management", label: "项目管理", icon: <AppstoreOutlined /> },
  { key: "tech-development", label: "技术开发", icon: <ToolOutlined /> },
  { key: "deployment-ops", label: "部署运维", icon: <DeploymentUnitOutlined /> },
];

interface Props {
  collapsed: boolean;
  onToggleCollapse: () => void;
  activeKey: string;
  onSelect: (key: string) => void;
}

export default function MarketSidebar({ collapsed, onToggleCollapse, activeKey, onSelect }: Props) {
  const isActive = (key: string) => activeKey === key;

  return (
    <div className={`market-sidebar${collapsed ? " collapsed" : ""}`}>
      <div className="market-sidebar-toggle" onClick={onToggleCollapse}>
        {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
      </div>

      <div className="market-sidebar-menu">
        {menuItems.map((item) => (
          <div
            key={item.key}
            className={`market-sidebar-item${isActive(item.key) ? " active" : ""}`}
            onClick={() => onSelect(item.key)}
          >
            <span className="market-sidebar-icon">{item.icon}</span>
            {!collapsed && <span className="market-sidebar-label">{item.label}</span>}
          </div>
        ))}
      </div>
    </div>
  );
}
