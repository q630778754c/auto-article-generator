import { useState, useEffect } from 'react';
import { Table, Button, Modal, Form, Input, InputNumber, Select, Space, Tag, message, Tooltip, Typography } from 'antd';
import { PlusOutlined, DeleteOutlined, CheckCircleOutlined, StopOutlined, BarChartOutlined, CopyOutlined } from '@ant-design/icons';
import { api, ApiKey } from '../../api';

const { Text, Paragraph } = Typography;

const SCOPE_OPTIONS = [
  { value: 'rss_only', label: '仅 RSS 抓取' },
  { value: 'webpage_only', label: '仅网页抓取' },
  { value: 'all_collector', label: '全部爬虫 API' },
];

const EXPIRES_OPTIONS = [
  { value: 7, label: '7 天' },
  { value: 30, label: '30 天' },
  { value: 90, label: '90 天' },
  { value: 180, label: '180 天' },
  { value: null, label: '永久' },
];

export default function ApiKeysPage() {
  const [data, setData] = useState<ApiKey[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [keyModalOpen, setKeyModalOpen] = useState(false);
  const [newKey, setNewKey] = useState('');
  const [usageOpen, setUsageOpen] = useState(false);
  const [usageData, setUsageData] = useState<any>(null);
  const [form] = Form.useForm();

  const fetchData = async (p = page) => {
    setLoading(true);
    try {
      const resp = await api.apikeys.list(p, 20);
      setData(resp.data.data.items);
      setTotal(resp.data.data.total);
    } catch {
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const handleCreate = async () => {
    const values = await form.validateFields();
    try {
      const resp = await api.apikeys.create({
        name: values.name,
        scope: values.scope || 'all_collector',
        rate_limit: values.rate_limit || 100,
        expires_days: values.expires_days ?? 90,
      });
      setNewKey(resp.data.data.key);
      setKeyModalOpen(true);
      setCreateOpen(false);
      form.resetFields();
      fetchData();
    } catch {
    }
  };

  const handleToggle = async (id: number) => {
    try {
      await api.apikeys.toggle(id);
      message.success('操作成功');
      fetchData();
    } catch {
    }
  };

  const handleDelete = (id: number) => {
    Modal.confirm({
      title: '确定删除此 API Key？',
      content: '删除后不可恢复',
      okText: '确定',
      cancelText: '取消',
      okType: 'danger',
      onOk: async () => {
        try {
          await api.apikeys.delete(id);
          message.success('删除成功');
          fetchData();
        } catch {
        }
      },
    });
  };

  const handleUsage = async (id: number) => {
    try {
      const resp = await api.apikeys.usage(id);
      setUsageData(resp.data.data);
      setUsageOpen(true);
    } catch {
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(newKey).then(() => message.success('已复制到剪贴板'));
  };

  const columns = [
    { title: '名称', dataIndex: 'name', key: 'name' },
    {
      title: 'Key',
      dataIndex: 'key_masked',
      key: 'key_masked',
      render: (v: string) => (
        <Tooltip title="完整 Key 仅在创建时显示一次">
          <Text code>{v}</Text>
        </Tooltip>
      ),
    },
    {
      title: '权限范围',
      dataIndex: 'scope',
      key: 'scope',
      render: (v: string) => {
        const opt = SCOPE_OPTIONS.find(o => o.value === v);
        return opt ? opt.label : v;
      },
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      render: (v: boolean) => v ? <Tag color="green">启用</Tag> : <Tag color="red">禁用</Tag>,
    },
    { title: '速率限制', dataIndex: 'rate_limit', key: 'rate_limit', render: (v: number) => `${v}/min` },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at' },
    { title: '最近使用', dataIndex: 'last_used_at', key: 'last_used_at', render: (v: string | null) => v || '从未使用' },
    { title: '调用次数', key: 'calls', render: (_: any, r: ApiKey) => `${r.total_calls} (成功${r.success_calls}/失败${r.fail_calls})` },
    {
      title: '操作',
      key: 'action',
      render: (_: any, r: ApiKey) => (
        <Space>
          <Button size="small" icon={r.enabled ? <StopOutlined /> : <CheckCircleOutlined />} onClick={() => handleToggle(r.id)}>
            {r.enabled ? '禁用' : '启用'}
          </Button>
          <Button size="small" icon={<BarChartOutlined />} onClick={() => handleUsage(r.id)}>用量</Button>
          <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(r.id)}>删除</Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h2>API Key 管理</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>创建 API Key</Button>
      </div>
      <Table
        columns={columns}
        dataSource={data}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          total,
          pageSize: 20,
          onChange: (p) => { setPage(p); fetchData(p); },
        }}
      />

      <Modal title="创建 API Key" open={createOpen} onOk={handleCreate} onCancel={() => { setCreateOpen(false); form.resetFields(); }} okText="创建" cancelText="取消">
        <Form form={form} layout="vertical" initialValues={{ scope: 'all_collector', rate_limit: 100, expires_days: 90 }}>
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }, { max: 50, message: '最多50字符' }]}>
            <Input placeholder="请输入名称" />
          </Form.Item>
          <Form.Item name="scope" label="权限范围">
            <Select options={SCOPE_OPTIONS} />
          </Form.Item>
          <Form.Item name="rate_limit" label="速率限制（次/分钟）" rules={[{ type: 'number', min: 1, max: 1000 }]}>
            <InputNumber min={1} max={1000} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="expires_days" label="有效期">
            <Select options={EXPIRES_OPTIONS} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal title="API Key 创建成功" open={keyModalOpen} onCancel={() => setKeyModalOpen(false)} footer={[
        <Button key="ok" type="primary" onClick={() => setKeyModalOpen(false)}>我已保存</Button>,
      ]}>
        <Paragraph type="warning">请妥善保存 Key 值，关闭后仅显示掩码！</Paragraph>
        <Input.Group compact>
          <Input style={{ width: '85%' }} readOnly value={newKey} />
          <Button style={{ width: '15%' }} icon={<CopyOutlined />} onClick={handleCopy}>复制</Button>
        </Input.Group>
      </Modal>

      <Modal title="用量统计" open={usageOpen} onCancel={() => setUsageOpen(false)} footer={null}>
        {usageData && (
          <div>
            <p>总调用次数：{usageData.total_calls}</p>
            <p>成功次数：{usageData.success_calls}</p>
            <p>失败次数：{usageData.fail_calls}</p>
            <p>最近使用：{usageData.last_used_at || '从未使用'}</p>
          </div>
        )}
      </Modal>
    </div>
  );
}