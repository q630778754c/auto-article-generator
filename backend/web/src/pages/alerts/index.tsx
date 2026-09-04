import { useEffect, useState } from 'react';
import { Card, Table, Tag, Button, Select, Space, message } from 'antd';
import { api, AlertEvent } from '../../api';

export default function Alerts() {
  const [alerts, setAlerts] = useState<AlertEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [level, setLevel] = useState<string | undefined>();
  const [status, setStatus] = useState<string | undefined>();
  const [loading, setLoading] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const resp = await api.alerts.list(level, status, page, 20);
      setAlerts(resp.data.data.items);
      setTotal(resp.data.data.total);
    } catch { /* */ } finally { setLoading(false); }
  };

  useEffect(() => { fetchData(); }, [page, level, status]);

  const handleConfirm = async (id: number) => {
    await api.alerts.confirm(id);
    message.success('已确认');
    fetchData();
  };

  const levelColors: Record<string, string> = { P0: 'red', P1: 'orange', P2: 'blue' };

  return (
    <Card title="告警中心">
      <Space style={{ marginBottom: 16 }}>
        <Select placeholder="级别" allowClear style={{ width: 100 }} value={level} onChange={setLevel}
          options={[{ value: 'P0', label: 'P0' }, { value: 'P1', label: 'P1' }, { value: 'P2', label: 'P2' }]} />
        <Select placeholder="状态" allowClear style={{ width: 120 }} value={status} onChange={setStatus}
          options={[{ value: 'unconfirmed', label: '未确认' }, { value: 'confirmed', label: '已确认' }]} />
      </Space>
      <Table
        loading={loading}
        dataSource={alerts}
        rowKey="id"
        pagination={{ current: page, total, pageSize: 20, onChange: setPage }}
        columns={[
          { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
          { title: '级别', dataIndex: 'level', key: 'level', width: 60, render: (l: string) => <Tag color={levelColors[l]}>{l}</Tag> },
          { title: '来源', dataIndex: 'source', key: 'source', width: 80 },
          { title: '标题', dataIndex: 'title', key: 'title' },
          { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
          { title: '状态', dataIndex: 'status', key: 'status', width: 80, render: (s: string) => <Tag color={s === 'confirmed' ? 'green' : 'orange'}>{s}</Tag> },
          { title: '通知', dataIndex: 'notify_status', key: 'notify_status', width: 80 },
          { title: '触发时间', dataIndex: 'triggered_at', key: 'triggered_at', width: 180 },
          { title: '操作', key: 'action', width: 80, render: (_: any, r: AlertEvent) => r.status === 'unconfirmed' ? <Button type="link" size="small" onClick={() => handleConfirm(r.id)}>确认</Button> : null },
        ]}
      />
    </Card>
  );
}