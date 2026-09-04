import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Button, Space, Badge } from 'antd';
import { useAppStore } from '../stores/app';
import { api } from '../api';
import { useEffect, useState } from 'react';

const { Header, Sider, Content } = Layout;

const menuItems = [
  { key: '/dashboard', label: '流水线监控' },
  { key: '/publish-records', label: '发布记录' },
  { key: '/channels', label: '账号渠道' },
  { key: '/config', label: '系统配置' },
  { key: '/alerts', label: '告警中心' },
  { key: '/spot-check', label: '审核质量抽查' },
  { key: '/unmanned-report', label: '无人值守验收' },
];

export default function MainLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { username, clearAuth, alertCount, setAlertCount } = useAppStore();
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const resp = await api.alerts.list(undefined, 'unconfirmed', 1, 1);
        setAlertCount(resp.data.data.total);
      } catch {
        // ignore
      }
    };
    fetchAlerts();
    const timer = setInterval(fetchAlerts, 60000);
    return () => clearInterval(timer);
  }, [setAlertCount]);

  const handleLogout = async () => {
    try {
      await api.auth.logout();
    } finally {
      clearAuth();
      navigate('/login');
    }
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed}>
        <div style={{ height: 48, margin: 8, color: '#fff', textAlign: 'center', lineHeight: '48px', fontSize: 16, fontWeight: 'bold' }}>
          {collapsed ? 'AI' : 'AI内容生产系统'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems.map((item) => ({
            ...item,
            label: item.key === '/alerts' ? <Badge count={alertCount} offset={[10, 0]}>{item.label}</Badge> : item.label,
          }))}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{ padding: '0 24px', background: '#fff', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 18, fontWeight: 'bold' }}>全自动AI内容生产与发布系统</span>
          <Space>
            <span>欢迎，{username}</span>
            <Button type="link" onClick={handleLogout}>退出登录</Button>
          </Space>
        </Header>
        <Content style={{ margin: 16, padding: 24, background: '#fff', borderRadius: 8, overflow: 'auto' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}