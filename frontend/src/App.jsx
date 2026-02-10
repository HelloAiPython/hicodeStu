import { Button, Card, Col, Layout, Row, Typography } from "antd";

const { Header, Content } = Layout;
const { Title, Paragraph } = Typography;

const metrics = [
  { title: "课堂表现", items: ["开小差记录", "回答问题", "课堂练习"] },
  { title: "课后作业", items: ["完成情况", "正确率", "订正情况"] },
];

export default function App() {
  return (
    <Layout style={{ minHeight: "100vh", background: "#f5f7fb" }}>
      <Header style={{ background: "#1f3a8a" }}>
        <Title style={{ color: "#fff", margin: 0 }} level={3}>
          学生学习情况评分系统
        </Title>
      </Header>
      <Content style={{ padding: "32px" }}>
        <Card style={{ maxWidth: 960, margin: "0 auto" }}>
          <Title level={4}>教师评分看板（示例）</Title>
          <Paragraph type="secondary">
            在此可查看学生课堂表现与课后作业的关键维度，并快速录入评分。
          </Paragraph>
          <Row gutter={[16, 16]}>
            {metrics.map((section) => (
              <Col xs={24} md={12} key={section.title}>
                <Card title={section.title} bordered>
                  <ul>
                    {section.items.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </Card>
              </Col>
            ))}
          </Row>
          <Button type="primary" style={{ marginTop: 16 }}>
            进入评分
          </Button>
        </Card>
      </Content>
    </Layout>
  );
}
