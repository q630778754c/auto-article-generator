import { useEffect, useState } from 'react';
import { Card, Row, Col, Statistic, Button, Space, Tag, Table, message, Modal } from 'antd';
import { api, PipelineStatus, MetricsDaily } from '../../api';

export default function Dashboard() {
  const [status, setStatus] = useState<PipelineStatus | null>(null);
  const [metrics, setMetrics] = useState<MetricsDaily[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [statusResp, metricsResp] = await Promise.all([
        api.pipeline.status(),
        api.metrics.daily(7),
      ]);
      setStatus(statusResp.data.data);
      setMetrics(metricsResp.data.data.items);
    } catch {
      // handled by interceptor
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const timer = setInterval(fetchData, 60000);
    return () => clearInterval(timer);
  }, []);

  const handleAction = async (action: 'start' | 'pause' | 'resume' | 'stop') => {
    if (action === 'stop') {
      Modal.confirm({
        title: '确认停止',
        content: '停止流水线是不可逆操作，确认要停止吗？',
        onOk: async () => {
          await api.pipeline.stop();
          message.success('已停止');
          fetchData();
        },
      });
      return;
    }
    await api.pipeline[action]();
    message.success('操作成功');
    fetchData();
  };

  const stateColor: Record<string, string> = {
    idle: 'default', running: 'green', paused: 'orange', stopped: 'red',
  };

  const today = metrics[0];

  return (
    <div>
      <Card title="流水线状态" loading={loading} extra={
        <Space>
          <Button type="primary" onClick={() => handleAction('start')} disabled={status?.state === 'running'}>启动</Button>
          <Button onClick={() => handleAction('pause')} disabled={status?.state !== 'running'}>暂停</Button>
          <Button onClick={() => handleAction('resume')} disabled={status?.state !== 'paused'}>恢复</Button>
          <Button danger onClick={() => handleAction('stop')} disabled={status?.state === 'stopped'}>停止</Button>
        </Space>
      }>
        <Row gutter={16}>
          <Col span={4}>
            <Statistic title="运行状态" valueRender={() => <Tag color={stateColor[status?.state || 'idle']}>{status?.state || 'idle'}</Tag>} />
          </Col>
          <Col span={4}><Statistic title="活跃任务" value={status?.active_count || 0} /></Col>
          <Col span={4}><Statistic title="待处理" value={status?.pending_count || 0} /></Col>
          <Col span={4}><Statistic title="今日产出" value={status?.daily_output || 0} suffix={`/ ${status?.daily_limit || 50}`} /></Col>
          <Col span={4}>
            <Statistic title="停滞检测" valueRender={() => <Tag color={status?.is_stagnant ? 'red' : 'green'}>{status?.is_stagnant ? '停滞' : '正常'}</Tag>} />
          </Col>
          <Col span={4}>
            <Statistic title="缺失配置" value={status?.missing_configs?.length || 0} />
          </Col>
        </Row>
      </Card>

      <Card title="今日指标" style={{ marginTop: 16 }} loading={loading}>
        <Row gutter={16}>
          <Col span={4}><Statistic title="采集数" value={today?.collected_count || 0} /></Col>
          <Col span={4}><Statistic title="改写数" value={today?.rewritten_count || 0} /></Col>
          <Col span={4}><Statistic title="配图数" value={today?.image_count || 0} /></Col>
          <Col span={4}><Statistic title="审核总数" value={today?.review_total || 0} /></Col>
          <Col span={4}><Statistic title="审核通过" value={today?.review_passed || 0} /></Col>
          <Col span={4}><Statistic title="发布数" value={today?.published_count || 0} /></Col>
          <Col span={4}><Statistic title="端到端总数" value={today?.e2e_total || 0} /></Col>
          <Col span={4}><Statistic title="端到端成功" value={today?.e2e_success || 0} /></Col>
          <Col span={4}><Statistic title="流水线失败" value={today?.pipeline_failed || 0} /></Col>
        </Row>
      </Card>

      <Card title="近7天指标趋势" style={{ marginTop: 16 }}>
        <Table
          size="small"
          dataSource={metrics}
          rowKey="stat_date"
          pagination={false}
          columns={[
            { title: '日期', dataIndex: 'stat_date', key: 'stat_date' },
            { title: '采集', dataIndex: 'collected_count', key: 'collected_count' },
            { title: '改写', dataIndex: 'rewritten_count', key: 'rewritten_count' },
            { title: '配图', dataIndex: 'image_count', key: 'image_count' },
            { title: '审核', dataIndex: 'review_total', key: 'review_total' },
            { title: '发布', dataIndex: 'published_count', key: 'published_count' },
            { title: '端到端成功', dataIndex: 'e2e_success', key: 'e2e_success' },
            { title: '失败', dataIndex: 'pipeline_failed', key: 'pipeline_failed' },
          ]}
        />
      </Card>
    </div>
  );
}