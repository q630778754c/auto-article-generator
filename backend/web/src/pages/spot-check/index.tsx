import { useEffect, useState } from 'react';
import { Card, Table, Tag, Button, Select, Space, message, Modal, Radio } from 'antd';
import { api, ReviewQuality } from '../../api';

export default function SpotCheck() {
  const [samples, setSamples] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [quality, setQuality] = useState<ReviewQuality[]>([]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [sampleResp, qualityResp] = await Promise.all([
        api.metrics.spotCheck(undefined, page, 20),
        api.metrics.reviewQuality(7),
      ]);
      setSamples(sampleResp.data.data.items);
      setTotal(sampleResp.data.data.total);
      setQuality(qualityResp.data.data.items);
    } catch { /* */ } finally { setLoading(false); }
  };

  useEffect(() => { fetchData(); }, [page]);

  const handleJudge = (id: number) => {
    let judgment = 'false_kill';
    Modal.confirm({
      title: '提交人工判定',
      content: (
        <Radio.Group defaultValue="false_kill" onChange={(e) => { judgment = e.target.value; }}>
          <Space direction="vertical">
            <Radio value="false_kill">误杀（不应拦截）</Radio>
            <Radio value="keep_intercept">维持拦截（正确拦截）</Radio>
          </Space>
        </Radio.Group>
      ),
      onOk: async () => {
        await api.metrics.judgeSpotCheck(id, judgment);
        message.success('判定已提交');
        fetchData();
      },
    });
  };

  return (
    <div>
      <Card title="审核质量日统计（近7天）" style={{ marginBottom: 16 }}>
        <Table
          size="small"
          dataSource={quality}
          rowKey="stat_date"
          pagination={false}
          columns={[
            { title: '日期', dataIndex: 'stat_date', key: 'stat_date' },
            { title: '审核总数', dataIndex: 'review_total', key: 'review_total' },
            { title: '一次通过', dataIndex: 'first_pass', key: 'first_pass' },
            { title: '退回', dataIndex: 'send_back', key: 'send_back' },
            { title: '硬拦截', dataIndex: 'hard_block', key: 'hard_block' },
            { title: '通过率', dataIndex: 'first_pass_rate', key: 'first_pass_rate', render: (v: number) => `${(v * 100).toFixed(1)}%` },
            { title: '拦截率', dataIndex: 'intercept_rate', key: 'intercept_rate', render: (v: number) => `${(v * 100).toFixed(1)}%` },
            { title: '平台拒绝率', dataIndex: 'platform_reject_rate', key: 'platform_reject_rate', render: (v: number) => `${(v * 100).toFixed(1)}%` },
          ]}
        />
      </Card>

      <Card title="人工抽查样本">
        <Table
          loading={loading}
          dataSource={samples}
          rowKey="id"
          pagination={{ current: page, total, pageSize: 20, onChange: setPage }}
          columns={[
            { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
            { title: '文章ID', dataIndex: 'article_id', key: 'article_id', width: 80 },
            { title: '审核轮次', dataIndex: 'review_round', key: 'review_round', width: 80 },
            { title: '是否被拦截', dataIndex: 'was_intercepted', key: 'was_intercepted', width: 100, render: (v: number) => <Tag color={v ? 'red' : 'green'}>{v ? '是' : '否'}</Tag> },
            { title: '人工判定', dataIndex: 'human_judgment', key: 'human_judgment', width: 120, render: (v: string) => v ? <Tag color={v === 'false_kill' ? 'orange' : 'green'}>{v}</Tag> : '-' },
            { title: '判定人', dataIndex: 'operator', key: 'operator', width: 100 },
            { title: '判定时间', dataIndex: 'judged_at', key: 'judged_at', width: 180 },
            { title: '操作', key: 'action', width: 80, render: (_: any, r: any) => !r.human_judgment ? <Button type="link" size="small" onClick={() => handleJudge(r.id)}>判定</Button> : null },
          ]}
        />
      </Card>
    </div>
  );
}