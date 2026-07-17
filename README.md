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

### 前端打包校验

```bash
npm run build
```

## 前后端联调（当前已可互通）

1. 启动后端（默认 `127.0.0.1:8000`）。
2. 启动前端（默认 `127.0.0.1:5173`，已通过 Vite 代理 `/api` 到后端）。
3. 打开前端页面：
   - 先在“教师登录（JWT）”输入账号密码获取 token（access/refresh token 会持久化到浏览器本地）
   - 再点击“加载看板”请求 `/api/students/alerts_board/`（支持回车触发，同时加载统计卡片）
   - 可按关键字筛选，并可切换“仅风险/仅待处理”过滤后下载 CSV（导出文件名自动包含过滤模式与阈值）
   - 可点击“查看详情”打开学生侧边栏，查看该学生的预警详情与学习进度，并可直接导出该学生预警/进度/详情总览 CSV
   - 可点击“重置筛选”快速恢复默认条件；可点击“退出登录”清除本地会话；access 过期时会自动尝试 refresh token 续期

## 下一步建议
- 建立评分维度、课程、学生、作业等数据模型
- 使用 DRF ViewSet 与权限类实现教师评分接口
- 前端对接 API，完成评分表单与统计图表

### 已暴露的 API 资源（示例）
- `GET /api/students/` 学生档案
- `GET /api/students/me/` 当前登录学生档案（学生端）
- `GET /api/students/me/progress/` 当前登录学生学习进度（学生端）
- `GET /api/students/me/alerts/?threshold=<分数>` 当前登录学生预警信息（学生端）
- `GET /api/students/search/?q=<关键字>` 按学号搜索学生
- `GET /api/students/alerts_board/?threshold=<分数>&q=<关键字>&limit=<数量>&risk_only=1&pending_only=1` 学生预警总览看板（支持按学号/用户名筛选、数量限制、仅风险/仅待处理过滤）
- `GET /api/students/alerts_board_export/?threshold=<分数>&q=<关键字>&risk_only=1&pending_only=1` 导出学生预警总览 CSV（支持筛选与仅风险/仅待处理过滤）
- `GET /api/students/alerts_board_stats/?threshold=<分数>&q=<关键字>&risk_only=1&pending_only=1` 学生预警总览统计（预警学生数/待处理总数/风险总数，支持仅风险/仅待处理过滤）
- `GET /api/students/{id}/progress/` 学生跨课程学习进度
- `GET /api/students/{id}/detail_dashboard/?threshold=<分数>` 学生详情面板（预警+学习进度）
- `GET /api/students/{id}/detail_dashboard_export/?threshold=<分数>` 导出学生详情总览 CSV（预警+学习进度）
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
- `GET /api/score-audit-logs/?action=<动作>&target_type=<对象类型>&target_id=<对象ID>&actor_username=<用户名>&date_from=<YYYY-MM-DD>&date_to=<YYYY-MM-DD>&limit=<数量>&page=<页码>&page_size=<每页条数>&ordering=<id|-id|created_at|-created_at>` 评分操作审计日志（教师，支持过滤/分页/排序）
- `GET /api/score-audit-logs/export/?action=<动作>&target_type=<对象类型>&target_id=<对象ID>&actor_username=<用户名>&date_from=<YYYY-MM-DD>&date_to=<YYYY-MM-DD>` 导出评分操作审计日志 CSV（教师）
- `GET /api/score-audit-logs/stats/?action=<动作>&target_type=<对象类型>&target_id=<对象ID>&actor_username=<用户名>&date_from=<YYYY-MM-DD>&date_to=<YYYY-MM-DD>` 评分操作审计统计（教师）
- `GET /api/score-audit-logs/filter-options/` 获取审计日志筛选项（动作/对象类型/操作人，教师）
- `GET /api/score-audit-logs/health/` 审计日志健康概览（总数、最早/最新记录，教师）
- `POST /api/score-audit-logs/purge/` 清理指定日期之前审计日志（教师，参数：`before_date`、`dry_run`、`max_delete`、`confirm=DELETE`，可选筛选：`action`、`target_type`、`actor_username`）

> 审计日志已为常用查询维度（时间、动作、对象、操作人）建立索引，适合教师端按条件分页检索与导出。


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

## 开发自检（建议）

后端在提交前可先执行一次语法编译检查：

```bash
cd backend
python -m compileall .
```
