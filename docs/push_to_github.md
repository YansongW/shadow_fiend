# 推送到 GitHub 指南

## 方案 A：使用 GitHub CLI（推荐）

1. 安装 GitHub CLI：
   ```bash
   brew install gh
   ```

2. 登录 GitHub：
   ```bash
   gh auth login
   ```

3. 创建仓库并推送：
   ```bash
   cd /Users/yansong/yimu
   gh repo create yimu --public --source=. --remote=origin --push
   ```

## 方案 B：手动在 GitHub 网页创建

1. 访问 https://github.com/new
2. Repository name 填 `yimu`
3. 选择 **Public** 和 **Add a README file**（可选）
4. 点击 **Create repository**
5. 在本地执行：
   ```bash
   cd /Users/yansong/yimu
   git remote add origin https://github.com/YOUR_USERNAME/yimu.git
   git branch -M main
   git push -u origin main
   ```

## 后续更新

```bash
git add .
git commit -m "Your commit message"
git push origin main
```
