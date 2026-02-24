import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Col,
  Input,
  InputNumber,
  Layout,
  Row,
  Space,
  Statistic,
  Switch,
  Table,
  Tag,
  Typography,
  message,
} from "antd";

const { Header, Content } = Layout;
const { Title, Paragraph, Text } = Typography;

const API_BASE = "/api";
const ACCESS_TOKEN_STORAGE_KEY = "teacher_access_token";
const REFRESH_TOKEN_STORAGE_KEY = "teacher_refresh_token";

function buildQuery(params) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") {
      return;
    }
    searchParams.set(key, String(value));
  });
  return searchParams.toString();
}

function csvFilename({ threshold, mode, keyword }) {
  const now = new Date();
  const stamp = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, "0")}${String(
    now.getDate()
  ).padStart(2, "0")}_${String(now.getHours()).padStart(2, "0")}${String(now.getMinutes()).padStart(
    2,
    "0"
  )}${String(now.getSeconds()).padStart(2, "0")}`;
  const safeKeyword = (keyword || "all").replace(/[^a-zA-Z0-9一-龥_-]/g, "").slice(0, 20) || "all";
  return `students_alerts_board_${mode}_t${threshold}_${safeKeyword}_${stamp}.csv`;
}

export default function App() {
  const [messageApi, contextHolder] = message.useMessage();

  const [username, setUsername] = useState("teacher");
  const [password, setPassword] = useState("pass123456");
  const [accessToken, setAccessToken] = useState(
    () => localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY) || ""
  );
  const [refreshToken, setRefreshToken] = useState(
    () => localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY) || ""
  );
  const [loginLoading, setLoginLoading] = useState(false);

  const [threshold, setThreshold] = useState(80);
  const [keyword, setKeyword] = useState("");
  const [limit, setLimit] = useState(20);
  const [riskOnly, setRiskOnly] = useState(false);
  const [pendingOnly, setPendingOnly] = useState(false);
  const [boardLoading, setBoardLoading] = useState(false);
  const [boardData, setBoardData] = useState({
    count: 0,
    total_count: 0,
    results: [],
    threshold: 80,
    keyword: "",
    limit: 20,
  });
  const [statsData, setStatsData] = useState({
    alert_student_count: 0,
    pending_total: 0,
    risk_total: 0,
  });

  const hasSession = accessToken.trim().length > 0;

  useEffect(() => {
    if (accessToken) {
      localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, accessToken);
    } else {
      localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
    }
  }, [accessToken]);

  useEffect(() => {
    if (refreshToken) {
      localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, refreshToken);
    } else {
      localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY);
    }
  }, [refreshToken]);

  const clearSession = (notice = "已退出登录") => {
    setAccessToken("");
    setRefreshToken("");
    setBoardData({
      count: 0,
      total_count: 0,
      results: [],
      threshold,
      keyword,
      limit,
    });
    setStatsData({
      alert_student_count: 0,
      pending_total: 0,
      risk_total: 0,
    });
    messageApi.info(notice);
  };

  const resetFilters = () => {
    setThreshold(80);
    setKeyword("");
    setLimit(20);
    setRiskOnly(false);
    setPendingOnly(false);
    messageApi.success("筛选条件已重置");
  };

  const tryRefreshAccessToken = async () => {
    if (!refreshToken) {
      return null;
    }
    const response = await fetch(`${API_BASE}/auth/token/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh: refreshToken }),
    });
    if (!response.ok) {
      return null;
    }
    const payload = await response.json();
    if (!payload.access) {
      return null;
    }
    setAccessToken(payload.access);
    return payload.access;
  };

  const authFetch = async (url, options = {}) => {
    const execute = async (tokenValue) =>
      fetch(url, {
        ...options,
        headers: {
          ...(options.headers || {}),
          Authorization: `Bearer ${tokenValue}`,
        },
      });

    let response = await execute(accessToken);
    if (response.status !== 401) {
      return response;
    }

    const renewedAccess = await tryRefreshAccessToken();
    if (!renewedAccess) {
      clearSession("登录已过期，请重新登录");
      return response;
    }

    response = await execute(renewedAccess);
    return response;
  };

  const columns = useMemo(
    () => [
      {
        title: "学号",
        dataIndex: "student_number",
        key: "student_number",
      },
      {
        title: "用户名",
        dataIndex: "username",
        key: "username",
      },
      {
        title: "待处理课程数",
        dataIndex: "pending_count",
        key: "pending_count",
        render: (value) =>
          value > 0 ? <Tag color="gold">{value}</Tag> : <Tag>{value}</Tag>,
      },
      {
        title: "风险课程数",
        dataIndex: "risk_count",
        key: "risk_count",
        render: (value) =>
          value > 0 ? <Tag color="red">{value}</Tag> : <Tag>{value}</Tag>,
      },
    ],
    []
  );

  const fetchAlertsStats = async () => {
    if (!hasSession) {
      return;
    }
    try {
      const query = buildQuery({ threshold, q: keyword, risk_only: riskOnly ? 1 : 0, pending_only: pendingOnly ? 1 : 0 });
      const response = await authFetch(`${API_BASE}/students/alerts_board_stats/?${query}`);
      if (!response.ok) {
        throw new Error(`统计加载失败（HTTP ${response.status}）`);
      }
      const payload = await response.json();
      setStatsData(payload);
    } catch (error) {
      messageApi.error(error.message || "统计加载失败");
    }
  };

  const fetchAlertsBoard = async () => {
    if (!hasSession) {
      messageApi.warning("请先登录，再加载预警看板");
      return;
    }

    setBoardLoading(true);
    try {
      const query = buildQuery({ threshold, q: keyword, limit, risk_only: riskOnly ? 1 : 0, pending_only: pendingOnly ? 1 : 0 });
      const response = await authFetch(`${API_BASE}/students/alerts_board/?${query}`);

      if (!response.ok) {
        throw new Error(`加载失败（HTTP ${response.status}）`);
      }

      const payload = await response.json();
      setBoardData(payload);
      setStatsData((current) => ({
        ...current,
        alert_student_count: payload.total_count ?? 0,
      }));
      messageApi.success("预警看板加载成功");
      await fetchAlertsStats();
    } catch (error) {
      messageApi.error(error.message || "加载失败");
    } finally {
      setBoardLoading(false);
    }
  };

  const handleLogin = async () => {
    setLoginLoading(true);
    try {
      const response = await fetch(`${API_BASE}/auth/token/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        throw new Error(`登录失败（HTTP ${response.status}）`);
      }

      const payload = await response.json();
      if (!payload.access || !payload.refresh) {
        throw new Error("登录返回中未包含完整 token（access + refresh）");
      }
      setAccessToken(payload.access);
      setRefreshToken(payload.refresh);
      messageApi.success("登录成功，已获取 access / refresh token");

      const query = buildQuery({ threshold, q: keyword, limit, risk_only: riskOnly ? 1 : 0, pending_only: pendingOnly ? 1 : 0 });
      const boardResponse = await fetch(`${API_BASE}/students/alerts_board/?${query}`, {
        headers: {
          Authorization: `Bearer ${payload.access}`,
        },
      });
      if (boardResponse.ok) {
        const boardPayload = await boardResponse.json();
        setBoardData(boardPayload);
      }
      await fetchAlertsStats();
    } catch (error) {
      messageApi.error(error.message || "登录失败");
    } finally {
      setLoginLoading(false);
    }
  };

  const handleExport = async () => {
    if (!hasSession) {
      messageApi.warning("请先登录，再导出 CSV");
      return;
    }
    try {
      const query = buildQuery({ threshold, q: keyword, risk_only: riskOnly ? 1 : 0, pending_only: pendingOnly ? 1 : 0 });
      const response = await authFetch(`${API_BASE}/students/alerts_board_export/?${query}`);
      if (!response.ok) {
        throw new Error(`导出失败（HTTP ${response.status}）`);
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      const exportMode = riskOnly ? "risk" : pendingOnly ? "pending" : "all";
      anchor.download = csvFilename({ threshold, mode: exportMode, keyword });
      anchor.click();
      window.URL.revokeObjectURL(url);
      messageApi.success("CSV 导出成功");
    } catch (error) {
      messageApi.error(error.message || "导出失败");
    }
  };

  return (
    <Layout style={{ minHeight: "100vh", background: "#f5f7fb" }}>
      {contextHolder}
      <Header style={{ background: "#1f3a8a" }}>
        <Title style={{ color: "#fff", margin: 0 }} level={3}>
          学生学习情况评分系统（前后端联调）
        </Title>
      </Header>

      <Content style={{ padding: 24 }}>
        <Space direction="vertical" size={16} style={{ width: "100%", maxWidth: 1100, margin: "0 auto" }}>
          <Card
            title="1) 教师登录（JWT）"
            extra={
              <Button disabled={!hasSession} onClick={() => clearSession()}>
                退出登录
              </Button>
            }
          >
            <Row gutter={12}>
              <Col xs={24} md={8}>
                <Input
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="用户名"
                  onPressEnter={handleLogin}
                />
              </Col>
              <Col xs={24} md={8}>
                <Input.Password
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="密码"
                  onPressEnter={handleLogin}
                />
              </Col>
              <Col xs={24} md={8}>
                <Button type="primary" loading={loginLoading} onClick={handleLogin} block>
                  登录并获取 Token
                </Button>
              </Col>
            </Row>
            <Paragraph style={{ marginTop: 12, marginBottom: 0 }}>
              <Text strong>Token 状态：</Text> {hasSession ? "已登录（支持自动刷新）" : "未登录"}
            </Paragraph>
          </Card>

          <Card title="2) 学生预警总览看板（调用 /api/students/alerts_board/）">
            <Row gutter={[12, 12]}>
              <Col xs={24} md={6}>
                <InputNumber
                  min={0}
                  value={threshold}
                  onChange={(value) => setThreshold(value ?? 80)}
                  style={{ width: "100%" }}
                  addonBefore="阈值"
                />
              </Col>
              <Col xs={24} md={8}>
                <Input
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                  placeholder="筛选关键字（学号/用户名）"
                  onPressEnter={fetchAlertsBoard}
                />
              </Col>
              <Col xs={24} md={4}>
                <InputNumber
                  min={1}
                  value={limit}
                  onChange={(value) => setLimit(value ?? 20)}
                  style={{ width: "100%" }}
                  addonBefore="限制"
                />
              </Col>
              <Col xs={24} md={2}>
                <Space>
                  <Switch checked={riskOnly} onChange={(v) => { setRiskOnly(v); if (v) setPendingOnly(false); }} />
                  <Text>仅风险</Text>
                </Space>
              </Col>
              <Col xs={24} md={2}>
                <Space>
                  <Switch checked={pendingOnly} onChange={(v) => { setPendingOnly(v); if (v) setRiskOnly(false); }} />
                  <Text>仅待处理</Text>
                </Space>
              </Col>
              <Col xs={24} md={4}>
                <Space style={{ width: "100%" }}>
                  <Button type="primary" loading={boardLoading} onClick={fetchAlertsBoard}>
                    加载看板
                  </Button>
                  <Button onClick={handleExport}>导出 CSV</Button>
                  <Button onClick={resetFilters}>重置筛选</Button>
                </Space>
              </Col>
            </Row>

            {!hasSession && (
              <Alert
                style={{ marginTop: 12 }}
                type="warning"
                showIcon
                message="尚未登录：请先获取 JWT token 再请求看板。"
              />
            )}

            <Row gutter={[12, 12]} style={{ marginTop: 12, marginBottom: 12 }}>
              <Col xs={24} md={8}>
                <Card>
                  <Statistic title="预警学生数" value={statsData.alert_student_count} />
                </Card>
              </Col>
              <Col xs={24} md={8}>
                <Card>
                  <Statistic title="待处理课程总数" value={statsData.pending_total} />
                </Card>
              </Col>
              <Col xs={24} md={8}>
                <Card>
                  <Statistic title="风险课程总数" value={statsData.risk_total} valueStyle={{ color: "#cf1322" }} />
                </Card>
              </Col>
            </Row>

            <Paragraph style={{ marginTop: 12 }} type="secondary">
              返回记录：{boardData.count} / 总命中：{boardData.total_count} / 当前阈值：{boardData.threshold} / 过滤模式：{boardData.filter_mode === "risk" ? "仅风险" : boardData.filter_mode === "pending" ? "仅待处理" : "全部"}
            </Paragraph>

            <Table
              rowKey={(record) => record.student_id}
              loading={boardLoading}
              columns={columns}
              dataSource={boardData.results}
              pagination={false}
            />
          </Card>
        </Space>
      </Content>
    </Layout>
  );
}
