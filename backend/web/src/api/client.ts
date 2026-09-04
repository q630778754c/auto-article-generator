import axios, { AxiosInstance, AxiosResponse } from 'axios';
import { message } from 'antd';

declare const __BUILD_VERSION__: string;
declare const __BUILD_TIME__: string;

export const BUILD_VERSION: string = typeof __BUILD_VERSION__ !== 'undefined' ? __BUILD_VERSION__ : 'dev';
export const BUILD_TIME: string = typeof __BUILD_TIME__ !== 'undefined' ? __BUILD_TIME__ : '';

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || '') + '/api/v1';

export interface ApiResponse<T = any> {
  code: number;
  message: string;
  data: T;
}

export interface PageData<T = any> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

const client: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
});

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (response: AxiosResponse<ApiResponse>) => {
    const body = response.data;
    if (body.code !== 0) {
      message.error(body.message || '操作失败');
      return Promise.reject(new Error(body.message));
    }
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('username');
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login';
      }
    }
    const msg = error.response?.data?.message || error.message || '网络异常';
    if (error.response?.status !== 401) {
      message.error(msg);
    }
    return Promise.reject(error);
  }
);

export default client;