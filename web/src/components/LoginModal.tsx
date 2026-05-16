import { useState } from "react";
import { Modal, Form, Input, Button, message, Tabs } from "antd";
import { useAppStore } from "../stores/appStore";
import { authApi } from "../services/api";

interface Props {
  open: boolean;
  onClose: () => void;
}

export default function LoginModal({ open, onClose }: Props) {
  const { setAuth } = useAppStore();
  const [loading, setLoading] = useState(false);

  const onLogin = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      const res = await authApi.login(values.username, values.password);
      setAuth(res.user as any, res.access_token);
      message.success("登录成功");
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "登录失败";
      message.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const onRegister = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      const res = await authApi.register(values.username, values.password);
      setAuth(res.user as any, res.access_token);
      message.success("注册成功");
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "注册失败";
      message.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal open={open} onCancel={onClose} footer={null} title="数字员工仿真平台" destroyOnHidden>
      <Tabs
        items={[
          {
            key: "login",
            label: "登录",
            children: (
              <Form onFinish={onLogin} layout="vertical">
                <Form.Item name="username" label="用户名" rules={[{ required: true, message: "请输入用户名" }]}>
                  <Input placeholder="请输入用户名" />
                </Form.Item>
                <Form.Item name="password" label="密码" rules={[{ required: true, message: "请输入密码" }]}>
                  <Input.Password placeholder="请输入密码" />
                </Form.Item>
                <Form.Item>
                  <Button type="primary" htmlType="submit" block loading={loading}>
                    登录
                  </Button>
                </Form.Item>
              </Form>
            ),
          },
          {
            key: "register",
            label: "注册",
            children: (
              <Form onFinish={onRegister} layout="vertical">
                <Form.Item name="username" label="用户名" rules={[{ required: true, message: "请输入用户名" }, { min: 3, message: "用户名至少3个字符" }]}>
                  <Input placeholder="请输入用户名" />
                </Form.Item>
                <Form.Item name="password" label="密码" rules={[{ required: true, message: "请输入密码" }]}>
                  <Input.Password placeholder="请输入密码" />
                </Form.Item>
                <Form.Item>
                  <Button type="primary" htmlType="submit" block loading={loading}>
                    注册
                  </Button>
                </Form.Item>
              </Form>
            ),
          },
        ]}
      />
    </Modal>
  );
}
