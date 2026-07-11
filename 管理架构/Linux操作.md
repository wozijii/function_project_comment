# Linux 常用操作

> 入职第一周 Linux 盲点汇总 —— 记下来，下次不用再查。

---

## 1. 新建文件

```bash
touch filename.txt          # 创建空文件（已存在则更新时间戳）
vim filename.txt            # 创建并编辑文件
echo "内容" > filename.txt  # 创建文件并写入内容（覆盖）
echo "追加" >> filename.txt # 追加内容到文件末尾
```

---

## 2. 新建文件夹

```bash
mkdir dirname               # 创建单层目录
mkdir -p a/b/c              # 递归创建多层目录（父目录不存在自动创建）
```

---

## 3. 删除文件

```bash
rm filename.txt             # 删除单个文件
rm -i filename.txt          # 删除前确认（安全习惯）
rm file1.txt file2.txt      # 删除多个文件
```

---

## 4. 删除文件夹

```bash
rmdir dirname               # 删除空目录（非空会报错）
rm -r dirname               # 递归删除目录及其内容
rm -rf dirname              # 强制递归删除（⚠️ 危险，不会确认，别写错路径）
```

> **警告：** `rm -rf` 是 Linux 里最危险的命令，执行前再三确认路径！

---

## 5. 复制文件

```bash
cp source.txt dest.txt              # 复制文件
cp source.txt /path/to/dest/        # 复制到指定目录
cp -i source.txt dest.txt           # 覆盖前确认
```

---

## 6. 复制文件夹

```bash
cp -r sourcedir destdir             # 递归复制目录及内容
cp -a sourcedir destdir             # 保留权限、时间戳、软链接等（完整复制）
```

---

## 7. 查看端口占用 & 杀死释放端口

```bash
# 查看端口占用（比如 8080）
netstat -tlnp | grep 8080           # 查看哪个进程占用了 8080
lsof -i :8080                       # 同上，更直观

# 杀死进程释放端口
kill PID                            # 正常终止进程（PID 是上面查到的进程号）
kill -9 PID                         # 强制杀死进程（kill 不掉的时候用）
```

**完整流程：**
```bash
lsof -i :8080                       # 第一步：查占用
kill -9 12345                       # 第二步：杀进程（12345 换成实际 PID）
lsof -i :8080                       # 第三步：确认已释放
```

---

## 8. 查看进程占用情况

```bash
ps aux                              # 查看所有进程
ps aux | grep keyword               # 按关键字筛选进程
top                                 # 实时查看进程（按 q 退出）
htop                                # 更友好的 top（需要安装）

# 常用 ps 组合
ps aux | grep java                  # 找 Java 进程
ps aux | grep node                  # 找 Node 进程
ps aux | grep python                # 找 Python 进程
ps -ef | grep keyword              # 另一种写法，效果类似
```

**top 快捷键：**
| 按键 | 功能 |
|------|------|
| `P`  | 按 CPU 占用排序 |
| `M`  | 按内存占用排序 |
| `q`  | 退出 |

---

## 9. 使用 grep 查找字符出现的位置

```bash
# 在文件中查找
grep "关键字" filename              # 在文件中查找字符串
grep -n "关键字" filename           # 显示匹配的行号
grep -i "关键字" filename           # 忽略大小写
grep -c "关键字" filename           # 统计匹配行数

# 在目录下递归查找（超常用）
grep -r "关键字" /path/to/dir      # 在目录及子目录中递归查找
grep -rn "关键字" .                 # 在当前目录递归查找，显示行号
grep -rn "关键字" --include="*.js"  # 只在 .js 文件中查找
grep -rn "关键字" --include="*.ts"  # 只在 .ts 文件中查找

# 实战示例
grep -rn "TODO" src/               # 找项目里所有 TODO 注释
grep -rn "console.log" src/        # 找所有调试日志
grep -rn "password" --include="*.java"  # 找代码中密码相关的地方
```

---

## 速查表

| 场景 | 命令 |
|------|------|
| 创建空文件 | `touch file` |
| 创建目录 | `mkdir dir` |
| 创建多层目录 | `mkdir -p a/b/c` |
| 删除文件 | `rm file` |
| 删除目录 | `rm -rf dir` |
| 复制文件 | `cp src dest` |
| 复制目录 | `cp -r src dest` |
| 移动/重命名 | `mv old new` |
| 查看端口 | `lsof -i :端口号` |
| 杀进程 | `kill -9 PID` |
| 看所有进程 | `ps aux` |
| 实时看进程 | `top` |
| 文件中查找 | `grep "文字" file` |
| 目录递归查找 | `grep -rn "文字" .` |
| 指定文件类型查找 | `grep -rn "文字" --include="*.js"` |

---

*2026-07-11 入职第一周复盘*
