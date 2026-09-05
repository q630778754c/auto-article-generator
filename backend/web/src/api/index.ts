import client, { ApiResponse, PageData } from './client';

export interface Source {
  id: number;
  name: string;
  source_type: string;
  url: string;
  enabled: number;
  run_status: string;
  max_items_per_poll: number;
  fail_count: number;
}

export interface Channel {
  id: number;
  platform: string;
  account_label: string;
  credential_type: string;
  credential_masked: string;
  enabled: number;
  health_status: string;
  daily_limit: number;
  min_interval_min: number;
  consecutive_fail: number;
  last_published_at: string | null;
}

export interface Article {
  id: number;
  material_id: number;
  title: string;
  style: string;
  rewrite_count: number;
  model_used: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface AlertEvent {
  id: number;
  level: string;
  source: string;
  title: string;
  description: string;
  ref_type: string | null;
  ref_value: string | null;
  status: string;
  notify_status: string;
  triggered_at: string;
  confirmed_by: string | null;
  confirmed_at: string | null;
}

export interface PipelineStatus {
  state: string;
  active_count: number;
  pending_count: number;
  daily_output: number;
  daily_limit: number;
  is_stagnant?: boolean;
  missing_configs?: string[];
}

export interface UnmannedReport {
  window_hours: number;
  window_start: string;
  window_end: string;
  continuous_hours: number;
  manual_intervention_count: number;
  intervention_detail: {
    initial_config: number;
    credential_update: number;
    alert_handle: number;
    manual_confirm: number;
  };
  daily_output_total: number;
  audit_log_total: number;
  is_qualified: boolean;
}

export interface SlaMetrics {
  stat_date: string;
  total_samples: number;
  met_count: number;
  compliance_rate: number;
  avg_latency_sec: number;
  max_latency_sec: number;
}

export interface ReviewQuality {
  stat_date: string;
  review_total: number;
  first_pass: number;
  send_back: number;
  hard_block: number;
  first_pass_rate: number;
  intercept_rate: number;
  platform_reject_rate: number;
  platform_reject_total: number;
  submit_total: number;
}

export interface MetricsDaily {
  stat_date: string;
  collected_count: number;
  rewritten_count: number;
  image_count: number;
  review_total: number;
  review_passed: number;
  published_count: number;
  e2e_total: number;
  e2e_success: number;
  pipeline_failed: number;
}

export interface ProcessLog {
  id: number;
  trace_id: string;
  step: string;
  status: string;
  message: string;
  created_at: string;
}

export interface SystemConfig {
  config_key: string;
  config_value: string;
  category: string;
  effect_mode: string;
  version: number;
  updated_by: string;
  updated_at: string;
}

export interface ApiKey {
  id: number;
  name: string;
  key_masked: string;
  scope: string;
  rate_limit: number;
  expires_days: number | null;
  expires_at: string | null;
  enabled: boolean;
  created_by: string;
  total_calls: number;
  success_calls: number;
  fail_calls: number;
  last_used_at: string | null;
  created_at: string;
  updated_at: string;
}

export const api = {
  auth: {
    login: (username: string, password: string) =>
      client.post<ApiResponse<{ token: string; username: string }>>('/auth/login', { username, password }),
    logout: () => client.post<ApiResponse>('/auth/logout'),
    me: () => client.get<ApiResponse<{ username: string }>>('/auth/me'),
    sendCode: (email: string) =>
      client.post<ApiResponse>('/auth/send-code', { email }),
    register: (data: { email: string; code: string; password: string; nickname?: string }) =>
      client.post<ApiResponse<{ token: string; user: any }>>('/auth/register', data),
    verifyLogin: (email: string, code: string) =>
      client.post<ApiResponse<{ token: string; user: any; is_new_user: boolean }>>('/auth/verify-login', { email, code }),
    resetPassword: (data: { email: string; code: string; new_password: string }) =>
      client.post<ApiResponse>('/auth/reset-password', data),
    platformLogin: (email: string, password: string) =>
      client.post<ApiResponse<{ token: string; user: any }>>('/auth/platform-login', { email, password }),
  },
  adminUsers: {
    list: (keyword = '', page = 1, page_size = 20) =>
      client.get<ApiResponse>('/auth/admin/users', { params: { keyword, page, page_size } }),
    get: (user_id: string) =>
      client.get<ApiResponse>(`/auth/admin/users/${user_id}`),
    update: (user_id: string, data: { nickname?: string; status?: string }) =>
      client.put<ApiResponse>(`/auth/admin/users/${user_id}`, data),
    toggle: (user_id: string) =>
      client.post<ApiResponse>(`/auth/admin/users/${user_id}/toggle`),
    unbind: (user_id: string) =>
      client.delete<ApiResponse>(`/auth/admin/users/${user_id}/unbind`),
  },
  apikeys: {
    list: (page = 1, page_size = 20) =>
      client.get<ApiResponse<PageData<ApiKey>>>('/apikeys', { params: { page, page_size } }),
    create: (data: { name: string; scope: string; rate_limit?: number; expires_days?: number | null }) =>
      client.post<ApiResponse<ApiKey & { key: string }>>('/apikeys', data),
    get: (id: number) =>
      client.get<ApiResponse<ApiKey>>(`/apikeys/${id}`),
    update: (id: number, data: { name?: string; scope?: string; rate_limit?: number; expires_days?: number | null }) =>
      client.put<ApiResponse<ApiKey>>(`/apikeys/${id}`, data),
    toggle: (id: number) =>
      client.post<ApiResponse<ApiKey>>(`/apikeys/${id}/toggle`),
    delete: (id: number) =>
      client.delete<ApiResponse>(`/apikeys/${id}`),
    usage: (id: number) =>
      client.get<ApiResponse<{ total_calls: number; success_calls: number; fail_calls: number; last_used_at: string | null }>>(`/apikeys/${id}/usage`),
  },
  sources: {
    list: (page = 1, page_size = 20) =>
      client.get<ApiResponse<PageData<Source>>>('/sources', { params: { page, page_size } }),
    create: (data: Partial<Source>) => client.post<ApiResponse<{ id: number }>>('/sources', data),
    update: (id: number, data: Partial<Source>) => client.put<ApiResponse>(`/sources/${id}`, data),
    delete: (id: number) => client.delete<ApiResponse>(`/sources/${id}`),
  },
  channels: {
    list: (page = 1, page_size = 20) =>
      client.get<ApiResponse<PageData<Channel>>>('/channels', { params: { page, page_size } }),
    create: (data: any) => client.post<ApiResponse<{ id: number }>>('/channels', data),
    update: (id: number, data: any) => client.put<ApiResponse>(`/channels/${id}`, data),
    delete: (id: number) => client.delete<ApiResponse>(`/channels/${id}`),
  },
  config: {
    list: (category?: string) =>
      client.get<ApiResponse<{ items: SystemConfig[] }>>('/config', { params: { category } }),
    upsert: (key: string, data: any) => client.put<ApiResponse>(`/config/${key}`, data),
    delete: (key: string) => client.delete<ApiResponse>(`/config/${key}`),
  },
  pipeline: {
    status: () => client.get<ApiResponse<PipelineStatus>>('/pipeline/status'),
    start: () => client.post<ApiResponse<PipelineStatus>>('/pipeline/start'),
    pause: () => client.post<ApiResponse>('/pipeline/pause'),
    resume: () => client.post<ApiResponse>('/pipeline/resume'),
    stop: () => client.post<ApiResponse>('/pipeline/stop'),
    records: (page = 1, page_size = 20) =>
      client.get<ApiResponse<PageData>>('/pipeline/records', { params: { page, page_size } }),
    unmannedReport: (window_hours = 72) =>
      client.get<ApiResponse<UnmannedReport>>('/pipeline/unmanned/acceptance-report', { params: { window_hours } }),
  },
  articles: {
    list: (status?: string, page = 1, page_size = 20) =>
      client.get<ApiResponse<PageData<Article>>>('/articles', { params: { status, page, page_size } }),
    get: (id: number) => client.get<ApiResponse>(`/articles/${id}`),
    delete: (id: number) => client.delete<ApiResponse>(`/articles/${id}`),
  },
  alerts: {
    list: (level?: string, status?: string, page = 1, page_size = 20) =>
      client.get<ApiResponse<PageData<AlertEvent>>>('/alerts', { params: { level, status, page, page_size } }),
    confirm: (id: number) => client.post<ApiResponse>(`/alerts/${id}/confirm`, {}),
  },
  metrics: {
    daily: (days = 7) => client.get<ApiResponse<{ items: MetricsDaily[] }>>('/metrics/daily', { params: { days } }),
    logs: (trace_id?: string, step?: string, page = 1, page_size = 50) =>
      client.get<ApiResponse<PageData<ProcessLog>>>('/metrics/logs', { params: { trace_id, step, page, page_size } }),
    quota: () => client.get<ApiResponse>('/metrics/quota'),
    auditLogs: (page = 1, page_size = 50) =>
      client.get<ApiResponse>('/metrics/audit-logs', { params: { page, page_size } }),
    sla: (stat_date?: string) => client.get<ApiResponse<SlaMetrics>>('/metrics/sla', { params: { stat_date } }),
    reviewQuality: (days = 7) =>
      client.get<ApiResponse<{ items: ReviewQuality[] }>>('/metrics/review-quality', { params: { days } }),
    spotCheck: (judged?: boolean, page = 1, page_size = 20) =>
      client.get<ApiResponse>('/metrics/spot-check', { params: { judged, page, page_size } }),
    judgeSpotCheck: (sample_id: number, human_judgment: string) =>
      client.put<ApiResponse>(`/metrics/spot-check/${sample_id}/judge`, null, { params: { human_judgment } }),
  },
};