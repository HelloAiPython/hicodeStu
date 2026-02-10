# 学生学习情况评分系统

本仓库包含 Django + Django REST Framework 的后端骨架，以及 React + Ant Design 的前端骨架。

## 后端（Django + DRF）

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### JWT 登录

```bash
curl -X POST http://127.0.0.1:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"<你的用户名>","password":"<你的密码>"}'
```

### 携带 JWT 访问示例

```bash
curl http://127.0.0.1:8000/api/courses/ \
  -H "Authorization: Bearer <你的access_token>"
```

## 前端（React + Ant Design）

```bash
cd frontend
npm install
npm run dev
```

## 下一步建议
- 建立评分维度、课程、学生、作业等数据模型
- 使用 DRF ViewSet 与权限类实现教师评分接口
- 前端对接 API，完成评分表单与统计图表

### 已暴露的 API 资源（示例）
- `GET /api/students/` 学生档案
- `GET /api/students/{id}/progress/` 学生跨课程学习进度
- `GET /api/courses/` 课程
- `GET /api/courses/{id}/overview/` 课程总体统计（已评分人数、均分）
- `GET /api/courses/{id}/leaderboard/` 课程排名汇总
- `GET /api/courses/{id}/report/` 课程分数段报告（优秀/良好/及格/不及格/待评分）
- `GET /api/enrollments/` 选课关系
- `GET /api/enrollments/{id}/summary/` 单个学生在课程内的评分汇总
- `GET /api/score-rules/` 评分规则
- `GET /api/classroom-scores/` 课堂评分
- `GET /api/homework-scores/` 作业评分
