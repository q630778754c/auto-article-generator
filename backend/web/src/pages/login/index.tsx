import { useState, useEffect } from 'react';
import { Card, Form, Input, Button, message, Tabs, Tooltip } from 'antd';
import { useNavigate } from 'react-router-dom';
import { api } from '../../api';
import { useAppStore } from '../../stores/app';

type LoginMode = 'password' | 'code' | 'register' | 'reset' | 'admin_local';

export default function Login() {
  const navigate = useNavigate();
  const { setAuth } = useAppStore();
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<LoginMode>('password');
  const [countdown, setCountdown] = useState(0);
  const [sendLoading, setSendLoading] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    if (countdown <= 0) return;
    const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
    return () => clearTimeout(timer);
  }, [countdown]);

  const handleSendCode = async () => {
    const email = form.getFieldValue('email');
    if (!email) {
      message.warning('请先输入邮箱');
      return;
    }
    setSendLoading(true);
    try {
      await api.auth.sendCode(email);
      message.success('验证码已发送');
      setCountdown(60);
    } catch {
    } finally {
      setSendLoading(false);
    }
  };

  const onFinish = async (values: any) => {
    setLoading(true);
    try {
      if (mode === 'admin_local') {
        const resp = await api.auth.login(values.username, values.password);
        const { token, username } = resp.data.data;
        setAuth(username, token, 'local');
        message.success('登录成功');
        navigate('/dashboard');
      } else if (mode === 'password') {
        const resp = await api.auth.platformLogin(values.email, values.password);
        const { token, user } = resp.data.data;
        setAuth(user?.username || values.email, token, 'unified', values.email);
        message.success('登录成功');
        navigate('/dashboard');
      } else if (mode === 'code') {
        const resp = await api.auth.verifyLogin(values.email, values.code);
        const { token, user, is_new_user } = resp.data.data;
        setAuth(user?.username || values.email, token, 'unified', values.email);
        message.success(is_new_user ? '注册并登录成功' : '登录成功');
        navigate('/dashboard');
      } else if (mode === 'register') {
        const resp = await api.auth.register({
          email: values.email,
          code: values.code,
          password: values.password,
          nickname: values.nickname || '',
        });
        const { token, user } = resp.data.data;
        setAuth(user?.username || values.email, token, 'unified', values.email);
        message.success('注册成功');
        navigate('/dashboard');
      } else if (mode === 'reset') {
        await api.auth.resetPassword({
          email: values.email,
          code: values.code,
          new_password: values.new_password,
        });
        message.success('密码重置成功，请使用新密码登录');
        setMode('password');
        form.resetFields(['code', 'new_password', 'nickname']);
      }
    } catch {
    } finally {
      setLoading(false);
    }
  };

  const tabItems = [
    { key: 'password', label: '密码登录' },
    { key: 'code', label: '验证码登录' },
    { key: 'register', label: '注册' },
    { key: 'reset', label: '忘记密码' },
  ];

  const renderForm = () => {
    if (mode === 'admin_local') {
      return (
        <Form form={form} onFinish={onFinish} layout="vertical">
          <Form.Item name="username" label="用户名" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input placeholder="请输入用户名" />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password placeholder="请输入密码" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>登录</Button>
          </Form.Item>
        </Form>
      );
    }

    const showCode = mode === 'code' || mode === 'register' || mode === 'reset';
    const showPassword = mode === 'password' || mode === 'register';
    const showNewPassword = mode === 'reset';
    const showNickname = mode === 'register';

    return (
      <Form form={form} onFinish={onFinish} layout="vertical">
        <Form.Item name="email" label="邮箱" rules={[{ required: true, message: '请输入邮箱' }, { type: 'email', message: '邮箱格式不正确' }]}>
          <Input placeholder="请输入邮箱" />
        </Form.Item>
        {showCode && (
          <Form.Item name="code" label="验证码" rules={[{ required: true, message: '请输入验证码' }]}>
            <Input.Group compact>
              <Input style={{ width: '60%' }} placeholder="验证码" />
              <Button
                style={{ width: '40%' }}
                disabled={countdown > 0}
                loading={sendLoading}
                onClick={handleSendCode}
              >
                {countdown > 0 ? `${countdown}s` : '发送验证码'}
              </Button>
            </Input.Group>
          </Form.Item>
        )}
        {showPassword && (
          <Form.Item name="password" label="密码" rules={[{ required: true, message: '请输入密码' }, { min: 6, message: '密码至少6位' }]}>
            <Input.Password placeholder="请输入密码" />
          </Form.Item>
        )}
        {showNewPassword && (
          <Form.Item name="new_password" label="新密码" rules={[{ required: true, message: '请输入新密码' }, { min: 6, message: '密码至少6位' }]}>
            <Input.Password placeholder="请输入新密码" />
          </Form.Item>
        )}
        {showNickname && (
          <Form.Item name="nickname" label="昵称">
            <Input placeholder="请输入昵称（可选）" />
          </Form.Item>
        )}
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading} block>
            {mode === 'register' ? '注册' : mode === 'reset' ? '重置密码' : '登录'}
          </Button>
        </Form.Item>
      </Form>
    );
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', background: '#f0f2f5' }}>
      <Card style={{ width: 440 }}>
        <Tabs
          activeKey={mode === 'admin_local' ? 'password' : mode}
          onChange={(key) => { setMode(key as LoginMode); form.resetFields(); }}
          items={tabItems}
          centered
        />
        {renderForm()}
        <div style={{ textAlign: 'center', marginTop: 8 }}>
          {mode === 'admin_local' ? (
            <Button type="link" onClick={() => { setMode('password'); form.resetFields(); }}>返回统一平台登录</Button>
          ) : (
            <Tooltip title="使用本地管理员账号登录">
              <Button type="link" onClick={() => { setMode('admin_local'); form.resetFields(); }}>管理员本地登录</Button>
            </Tooltip>
          )}
        </div>
      </Card>
    </div>
  );
}
