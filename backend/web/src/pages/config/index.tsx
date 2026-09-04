import { useEffect, useState } from 'react';
import { Card, Tabs, Table, Form, Input, Button, Select, InputNumber, Switch, message, Space, Modal } from 'antd';
import { api, SystemConfig, Source } from '../../api';

type TabKey = 'sources' | 'ai' | 'pipeline';

export default function Config() {
  return (
    <Card title="系统配置">
      <Tabs
        items={[
          { key: 'sources', label: '资讯源管理', children: <SourcesTab /> },
          { key: 'ai', label: 'AI服务配置', children: <AiTab /> },
          { key: 'pipeline', label: '流水线策略', children: <PipelineTab /> },
        ]}
      />
    </Card>
  );
}

function SourcesTab() {
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  const fetch = async () => {
    setLoading(true);
    try {
      const resp = await api.sources.list(1, 100);
      setSources(resp.data.data.items);
    } catch { /* */ } finally { setLoading(false); }
  };

  useEffect(() => { fetch(); }, []);

  const handleCreate = async () => {
    const values = await form.validateFields();
    if (!values.url) { message.error('源地址不能为空'); return; }
    await api.sources.create(values);
    message.success('已添加');
    setModalOpen(false);
    form.resetFields();
    fetch();
  };

  const handleDelete = (id: number) => {
    Modal.confirm({
      title: '确认删除',
      content: '删除资讯源后不可恢复，确认删除？',
      onOk: async () => { await api.sources.delete(id); message.success('已删除'); fetch(); },
    });
  };

  return (
    <>
      <Button type="primary" style={{ marginBottom: 16 }} onClick={() => setModalOpen(true)}>添加资讯源</Button>
      <Table
        loading={loading}
        dataSource={sources}
        rowKey="id"
        pagination={false}
        columns={[
          { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
          { title: '名称', dataIndex: 'name', key: 'name' },
          { title: '类型', dataIndex: 'source_type', key: 'source_type', width: 80 },
          { title: 'URL', dataIndex: 'url', key: 'url', ellipsis: true },
          { title: '启用', dataIndex: 'enabled', key: 'enabled', width: 60, render: (e: number) => (e ? '是' : '否') },
          { title: '单次上限', dataIndex: 'max_items_per_poll', key: 'max_items_per_poll', width: 80 },
          { title: '失败次数', dataIndex: 'fail_count', key: 'fail_count', width: 80 },
          { title: '操作', key: 'action', width: 120, render: (_: any, r: Source) => (
            <Space>
              <Button type="link" size="small" onClick={async () => { await api.sources.update(r.id, { enabled: r.enabled ? 0 : 1 }); fetch(); }}>{r.enabled ? '禁用' : '启用'}</Button>
              <Button type="link" danger size="small" onClick={() => handleDelete(r.id)}>删除</Button>
            </Space>
          )},
        ]}
      />
      <Modal title="添加资讯源" open={modalOpen} onOk={handleCreate} onCancel={() => setModalOpen(false)} destroyOnClose>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="source_type" label="类型" rules={[{ required: true }]}>
            <Select options={[{ value: 'rss', label: 'RSS' }, { value: 'webpage', label: '网页' }]} />
          </Form.Item>
          <Form.Item name="url" label="URL" rules={[{ required: true, message: '源地址不能为空' }]}><Input /></Form.Item>
          <Form.Item name="max_items_per_poll" label="单次抓取上限" initialValue={20}><InputNumber min={1} max={100} /></Form.Item>
        </Form>
      </Modal>
    </>
  );
}

function AiTab() {
  const [configs, setConfigs] = useState<SystemConfig[]>([]);
  const [loading, setLoading] = useState(false);

  const fetch = async () => {
    setLoading(true);
    try {
      const resp = await api.config.list('ai_service');
      setConfigs(resp.data.data.items);
    } catch { /* */ } finally { setLoading(false); }
  };

  useEffect(() => { fetch(); }, []);

  return (
    <Table
      loading={loading}
      dataSource={configs}
      rowKey="config_key"
      pagination={false}
      columns={[
        { title: '配置键', dataIndex: 'config_key', key: 'config_key' },
        { title: '配置值', dataIndex: 'config_value', key: 'config_value', render: (v: string) => v.includes('key') ? `****${v.slice(-4)}` : v },
        { title: '版本', dataIndex: 'version', key: 'version', width: 60 },
        { title: '更新人', dataIndex: 'updated_by', key: 'updated_by', width: 100 },
        { title: '更新时间', dataIndex: 'updated_at', key: 'updated_at', width: 180 },
      ]}
    />
  );
}

function PipelineTab() {
  const [configs, setConfigs] = useState<SystemConfig[]>([]);
  const [loading, setLoading] = useState(false);

  const fetch = async () => {
    setLoading(true);
    try {
      const resp = await api.config.list('pipeline_strategy');
      setConfigs(resp.data.data.items);
    } catch { /* */ } finally { setLoading(false); }
  };

  useEffect(() => { fetch(); }, []);

  return (
    <Table
      loading={loading}
      dataSource={configs}
      rowKey="config_key"
      pagination={false}
      columns={[
        { title: '配置键', dataIndex: 'config_key', key: 'config_key' },
        { title: '配置值', dataIndex: 'config_value', key: 'config_value' },
        { title: '生效模式', dataIndex: 'effect_mode', key: 'effect_mode', width: 100 },
        { title: '版本', dataIndex: 'version', key: 'version', width: 60 },
        { title: '更新时间', dataIndex: 'updated_at', key: 'updated_at', width: 180 },
      ]}
    />
  );
}
