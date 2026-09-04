import { useEffect, useState } from 'react';
import { Card, Table, Tag, Button, Space, Select, Modal, message } from 'antd';
import { api, Article } from '../../api';

export default function PublishRecords() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [loading, setLoading] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const resp = await api.articles.list(statusFilter, page, 20);
      setArticles(resp.data.data.items);
      setTotal(resp.data.data.total);
    } catch {
      // handled
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [page, statusFilter]);

  const handleDelete = (id: number) => {
    Modal.confirm({
      title: '确认删除',
      content: '删除后不可恢复，确认删除该文章？',
      onOk: async () => {
        await api.articles.delete(id);
        message.success('已删除');
        fetchData();
      },
    });
  };

  const statusColors: Record<string, string> = {
    draft: 'default', in_review: 'processing', approved: 'green',
    rejected: 'red', violation_blocked: 'red', archived: 'default', awaiting_confirm: 'orange',
  };

  return (
    <Card title="文章与发布记录">
      <Space style={{ marginBottom: 16 }}>
        <Select
          placeholder="按状态筛选"
          allowClear
          style={{ width: 150 }}
          value={statusFilter}
          onChange={(v) => { setStatusFilter(v); setPage(1); }}
          options={[
            { value: 'draft', label: '草稿' },
            { value: 'in_review', label: '审核中' },
            { value: 'approved', label: '已通过' },
            { value: 'rejected', label: '已拒绝' },
            { value: 'awaiting_confirm', label: '待确认' },
            { value: 'archived', label: '已归档' },
          ]}
        />
      </Space>
      <Table
        loading={loading}
        dataSource={articles}
        rowKey="id"
        pagination={{ current: page, total, pageSize: 20, onChange: setPage }}
        columns={[
          { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
          { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true },
          { title: '状态', dataIndex: 'status', key: 'status', width: 120, render: (s: string) => <Tag color={statusColors[s]}>{s}</Tag> },
          { title: '体裁', dataIndex: 'style', key: 'style', width: 100 },
          { title: '改写次数', dataIndex: 'rewrite_count', key: 'rewrite_count', width: 80 },
          { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
          {
            title: '操作', key: 'action', width: 120, render: (_: any, record: Article) => (
              <Button type="link" danger size="small" onClick={() => handleDelete(record.id)}>删除</Button>
            ),
          },
        ]}
      />
    </Card>
  );
}