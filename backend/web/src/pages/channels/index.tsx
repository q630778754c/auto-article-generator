import { useEffect, useState } from 'react';
import { Card, Table, Tag, Button, Modal, Form, Input, Select, InputNumber, Space, message } from 'antd';
import { api, Channel } from '../../api';

const PLATFORMS = [
  { value: 'toutiao', label: '今日头条' },
  { value: 'penguin', label: '企鹅号' },
  { value: 'zhihu', label: '知乎' },
  { value: 'xhs', label: '小红书' },
  { value: 'baijiahao', label: '百家号' },
];

export default function Channels() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  const fetchData = async () => {
    setLoading(true);
    try {
      const resp = await api.channels.list(page, 20);
      setChannels(resp.data.data.items);
      setTotal(resp.data.data.total);
    } catch {
      // handled
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [page]);

  const handleCreate = async () => {
    const values = await form.validateFields();
    await api.channels.create(values);
    message.success('渠道已添加');
    setModalOpen(false);
    form.resetFields();
    fetchData();
  };

  const handleDelete = (id: number) => {
    Modal.confirm({
      title: '确认删除',
      content: '删除渠道后不可恢复，确认删除？',
      onOk: async () => {
        await api.channels.delete(id);
        message.success('已删除');
        fetchData();
      },
    });
  };

  const handleToggle = async (id: number, enabled: number) => {
    await api.channels.update(id, { enabled: enabled ? 0 : 1 });
    message.success('已更新');
    fetchData();
  };

  const healthColors: Record<string, string> = { normal: 'green', credential_expired: 'orange', abnormal: 'red' };

  return (
    <Card title="发布渠道管理" extra={<Button type="primary" onClick={() => setModalOpen(true)}>添加渠道</Button>}>
      <Table
        loading={loading}
        dataSource={channels}
        rowKey="id"
        pagination={{ current: page, total, pageSize: 20, onChange: setPage }}
        columns={[
          { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
          { title: '平台', dataIndex: 'platform', key: 'platform', width: 100, render: (p: string) => PLATFORMS.find(x => x.value === p)?.label || p },
          { title: '账号标签', dataIndex: 'account_label', key: 'account_label' },
          { title: '凭证', dataIndex: 'credential_masked', key: 'credential_masked' },
          { title: '健康', dataIndex: 'health_status', key: 'health_status', width: 120, render: (h: string) => <Tag color={healthColors[h]}>{h}</Tag> },
          { title: '日上限', dataIndex: 'daily_limit', key: 'daily_limit', width: 80 },
          { title: '连续失败', dataIndex: 'consecutive_fail', key: 'consecutive_fail', width: 80 },
          { title: '启用', dataIndex: 'enabled', key: 'enabled', width: 80, render: (e: number) => <Tag color={e ? 'green' : 'default'}>{e ? '是' : '否'}</Tag> },
          {
            title: '操作', key: 'action', width: 150, render: (_: any, record: Channel) => (
              <Space>
                <Button type="link" size="small" onClick={() => handleToggle(record.id, record.enabled)}>{record.enabled ? '禁用' : '启用'}</Button>
                <Button type="link" danger size="small" onClick={() => handleDelete(record.id)}>删除</Button>
              </Space>
            ),
          },
        ]}
      />
      <Modal title="添加渠道" open={modalOpen} onOk={handleCreate} onCancel={() => setModalOpen(false)} destroyOnClose>
        <Form form={form} layout="vertical">
          <Form.Item name="platform" label="平台" rules={[{ required: true }]}>
            <Select options={PLATFORMS} />
          </Form.Item>
          <Form.Item name="account_label" label="账号标签" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="credential" label="凭证" rules={[{ required: true, message: '凭证不能为空' }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item name="credential_type" label="凭证类型" initialValue="cookie">
            <Select options={[{ value: 'cookie', label: 'Cookie' }, { value: 'oauth', label: 'OAuth' }]} />
          </Form.Item>
          <Form.Item name="daily_limit" label="日发布上限" initialValue={10}>
            <InputNumber min={1} max={50} />
          </Form.Item>
          <Form.Item name="min_interval_min" label="最小间隔(分钟)" initialValue={30}>
            <InputNumber min={5} max={1440} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}