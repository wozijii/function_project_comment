## 1.github连接本地项目

- ### 在 GitHub 创建新仓库

  ​	1、创建仓库不要选择添加README（如果本地已经有项目）

- **本地化初始项目**

  ​	1、打开终端，进入你的项目文件夹：git init 

  ​	2、添加文件到暂存区：git add .、git commit -m "第一次提交"

  ​	3、连接远程仓库：git remote add origin https://github.com/username/repository.git（这是你的仓库地址）

  ​	4、推送到 GitHub：git branch 查看分支  ；git push -u origin main（查看分支后推送）

- **可能遇见问题**

  ​	1、出现错误：需要添加公钥到github中

  ```bash
  # 生成密钥
  ssh-keygen -t ed25519 -C "your_email@example.com"
  ```

  ​	2、cat ~/.ssh/id_ed25519.pub（复制公钥）

  ​	3、然后将公钥添加到 GitHub → Settings → SSH and GPG keys → New SSH key

  ​	4、使用 SSH 地址连接：git remote add origin git@github.com:username/repository.git（仓库地址）



## 2.git 各种快速操作

- 基本工作流程

| 命令                       | 作用                 |
| -------------------------- | -------------------- |
| `git add <文件名>`         | 将文件添加到暂存区   |
| `git add .`                | 添加所有修改到暂存区 |
| `git commit -m "提交说明"` | 提交暂存区的更改     |
| `git push origin <分支名>` | 推送到远程仓库       |
| `git pull origin <分支名>` | 从远程仓库拉取更新   |

- 日常使用标准

```bash
git add .
git commit -m "修复了登录bug"
git push origin main
```

## 3.分支操作--------暂时不用