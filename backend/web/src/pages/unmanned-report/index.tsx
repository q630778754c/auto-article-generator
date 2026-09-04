import { useEffect, useState } from 'react';
import { Card, Select, Button, Descriptions, Tag, Table, Statistic, Row, Col, Space } from 'antd';
import { api, type UnmannedReport, type SlaMetrics } from '../../api';

export default function UnmannedReport() {
  const [report, setReport] = useState<UnmannedReport | null>(null);
  const [sla, setSla] = useState<SlaMetrics | null>(null);
  const [windowHours, setWindowHours] = useState(72);
  const [loading, setLoading] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [reportResp, slaResp] = await Promise.all([
        api.pipeline.unmannedReport(windowHours),
        api.metrics.sla(),
      ]);
      setReport(reportResp.data.data);
      setSla(slaResp.data.data);
    } catch { /* */ } finally { setLoading(false); }
  };

  useEffect(() => { fetchData(); }, [windowHours]);

  return (
    <div>
      <Card title="无人值守验收报告" loading={loading} extra={
        <Space>
          <Select value={windowHours} onChange={setWindowHours} style={{ width: 120 }}
            options={[{ value: 24, label: '24小时' }, { value: 72, label: '72小时' }, { value: 168, label: '168小时' }]} />
          <Button onClick={fetchData}>刷新</Button>
        </Space>
      }>
        {report && (
          <>
            <Descriptions bordered column={2}>
              <Descriptions.Item label="验收窗口">{report.window_hours}小时</Descriptions.Item>
              <Descriptions.Item label="窗口起止">{report.window_start} ~ {report.window_end}</Descriptions.Item>
              <Descriptions.Item label="连续运行时长">{report.continuous_hours}小时</Descriptions.Item>
              <Descriptions.Item label="人工介入次数">{report.manual_intervention_count}</Descriptions.Item>
              <Descriptions.Item label="初始配置">{report.intervention_detail.initial_config}</Descriptions.Item>
              <Descriptions.Item label="凭证更新">{report.intervention_detail.credential_update}</Descriptions.Item>
              <Descriptions.Item label="告警处理">{report.intervention_detail.alert_handle}</Descriptions.Item>
              <Descriptions.Item label="人工确认">{report.intervention_detail.manual_confirm}</Descriptions.Item>
              <Descriptions.Item label="窗口内总产出">{report.daily_output_total}</Descriptions.Item>
              <Descriptions.Item label="审计日志数">{report.audit_log_total}</Descriptions.Item>
              <Descriptions.Item label="验收结果" span={2}>
                <Tag color={report.is_qualified ? 'green' : 'red'} style={{ fontSize: 14 }}>
                  {report.is_qualified ? '✓ 达标' : '✗ 未达标'}
                </Tag>
              </Descriptions.Item>
            </Descriptions>
          </>
        )}
      </Card>

      {sla && (
        <Card title="采集时延SLA（今日）" style={{ marginTop: 16 }}>
          <Row gutter={16}>
            <Col span={6}><Statistic title="总样本数" value={sla.total_samples} /></Col>
            <Col span={6}><Statistic title="达标数" value={sla.met_count} /></Col>
            <Col span={6}><Statistic title="达标率" value={`${(sla.compliance_rate * 100).toFixed(1)}%`} /></Col>
            <Col span={6}><Statistic title="平均时延" value={sla.avg_latency_sec} suffix="秒" /></Col>
          </Row>
        </Card>
      )}
    </div>
  );
}