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
