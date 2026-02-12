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

### 首次初始化（避免 no such table 错误）

```bash
python manage.py makemigrations core
python manage.py migrate
```

### 初始化演示课程与评分规则

```bash
python manage.py init_demo_data --teacher <教师用户名> --course-code C001 --course-name "示例课程"
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
- `GET /api/students/search/?q=<关键字>` 按学号搜索学生
- `GET /api/students/alerts_board/?threshold=<分数>` 学生预警总览看板
- `GET /api/students/alerts_board_export/?threshold=<分数>` 导出学生预警总览 CSV
- `GET /api/students/{id}/progress/` 学生跨课程学习进度
- `GET /api/students/{id}/alerts/?threshold=<分数>` 学生预警信息
- `GET /api/students/{id}/alerts_export/?threshold=<分数>` 导出学生预警 CSV
- `GET /api/students/{id}/progress_export/` 导出学生学习进度 CSV
- `GET /api/courses/` 课程
- `GET /api/courses/global_overview/` 全局统计总览
- `GET /api/courses/compare/?course_ids=<id>&course_ids=<id>` 多课程横向对比
- `GET /api/courses/workload/?teacher_id=<id>` 教师课程批改工作量总览
- `GET /api/courses/workload_export/?teacher_id=<id>` 导出教师工作量 CSV
- `GET /api/courses/{id}/overview/` 课程总体统计（已评分人数、均分）
- `GET /api/courses/{id}/leaderboard/` 课程排名汇总
- `GET /api/courses/{id}/leaderboard_export/` 导出课程排名 CSV
- `GET /api/courses/{id}/report_export/` 导出课程报告 CSV（含分数段）
- `GET /api/courses/{id}/report/` 课程分数段报告（优秀/良好/及格/不及格/待评分）
- `GET /api/courses/{id}/pending_list/` 课程待评分学生列表
- `GET /api/courses/{id}/risk_list/?threshold=<分数>` 课程风险学生列表
- `GET /api/courses/{id}/action_board/?threshold=<分数>&limit=<数量>` 课程干预看板
- `GET /api/enrollments/` 选课关系
- `POST /api/enrollments/bulk_create/` 批量创建选课关系
- `GET /api/enrollments/{id}/summary/` 单个学生在课程内的评分汇总
- `GET /api/enrollments/{id}/history/` 单个学生在课程内的评分历史轨迹
- `GET /api/score-rules/` 评分规则
- `GET /api/score-rules/validate/?course_id=<id>` 校验课程权重总和是否为100
- `POST /api/score-rules/normalize/` 归一化课程启用权重到100
- `GET /api/score-rules/audit/` 审计全部课程权重配置
- `GET /api/classroom-scores/` 课堂评分
- `POST /api/classroom-scores/bulk_create/` 批量录入课堂评分
- `GET /api/homework-scores/` 作业评分
- `POST /api/homework-scores/bulk_create/` 批量录入作业评分


### 排名接口过滤参数（leaderboard）
- `only_scored=1`：只返回已有总分学生
- `student_number=<学号片段>`：按学号筛选
- `min_score=<数字>`：按最低总分筛选
- `limit=<数字>`：先限制总结果条数
- `page=<数字>`：页码（默认 1）
- `page_size=<数字>`：每页条数（默认 20）

示例：
```bash
curl "http://127.0.0.1:8000/api/courses/1/leaderboard/?only_scored=1&min_score=80&limit=50&page=1&page_size=10" \
  -H "Authorization: Bearer <你的access_token>"
```
