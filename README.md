# Obsidian 自动化脚本库

为 Obsidian 知识库提供自动化维护脚本，包括整理、索引更新、清理、备份等功能，以及 macOS launchd 定时任务配置。

## 功能特性

| 脚本 | 功能 | 适用场景 |
|------|------|----------|
| `organize.py` | 自动整理未归类笔记 | 每日清理收件箱 |
| `update_index.py` | 自动更新知识库索引 | 每日更新索引文件 |
| `cleanup.py` | 自动清理过期内容 | 每周清理旧笔记 |
| `backup.py` | 自动备份知识库 | 每日增量备份 |

## 安装

### 1. 复制脚本到本地

```bash
mkdir -p ~/obsidian/scripts
cp -r scripts/* ~/obsidian/scripts/
```

### 2. 配置路径

编辑脚本或创建配置文件，设置你的 Obsidian 库路径。

### 3. 安装定时任务（macOS）

```bash
# 复制 plist 文件到 LaunchAgents
cp launchd/*.plist ~/Library/LaunchAgents/

# 编辑 plist 中的路径
vim ~/Library/LaunchAgents/com.obsidian.backup.plist
# 替换 /path/to/your/obsidian/vault 为你的实际路径

# 加载定时任务
launchctl load ~/Library/LaunchAgents/com.obsidian.backup.plist
launchctl load ~/Library/LaunchAgents/com.obsidian.organize.plist
launchctl load ~/Library/LaunchAgents/com.obsidian.update_index.plist
launchctl load ~/Library/LaunchAgents/com.obsidian.cleanup.plist
```

## 脚本说明

### organize.py - 自动整理笔记

将收件箱或未分类的笔记整理到正确的目录。

```bash
# 整理收件箱
python3 organize.py --vault /path/to/vault

# 整理指定目录
python3 organize.py --vault /path/to/vault --source /path/to/source

# 预览模式
python3 organize.py --vault /path/to/vault --dry-run
```

**分类规则：**

| 关键词 | 目标目录 |
|--------|----------|
| 书名、作者、读书 | 01-信息输入/阅读笔记 |
| 播客、节目、EP | 01-信息输入/播客笔记 |
| 概念、定义、是什么 | 03-知识整理/概念笔记 |
| 项目、进度、里程碑 | 02-项目记录/进行中 |
| 会议、参会、纪要 | 02-项目记录/会议记录 |
| 周复盘、周报 | 05-复盘归档/周复盘 |

### update_index.py - 更新索引

扫描知识库并自动生成索引文件。

```bash
# 更新索引
python3 update_index.py --vault /path/to/vault

# 自定义输出文件名
python3 update_index.py --vault /path/to/vault \
    --output-main 索引.md \
    --output-tags 标签索引.md \
    --output-links 链接图谱.md
```

**生成的文件：**

- `索引.md` - 主索引，包含统计概览、按标签分类、最近更新
- `标签索引.md` - 所有标签的笔记列表
- `链接图谱.md` - 双向链接关系图

### cleanup.py - 清理过期内容

清理长期未更新、草稿、临时文件等。

```bash
# 清理90天未更新的笔记
python3 cleanup.py --vault /path/to/vault --days 90

# 预览模式
python3 cleanup.py --vault /path/to/vault --dry-run

# 生成清理报告
python3 cleanup.py --vault /path/to/vault --report cleanup_report.md

# 不归档，只删除临时文件
python3 cleanup.py --vault /path/to/vault --no-archive
```

**清理类型：**

| 类型 | 处理方式 |
|------|----------|
| 过期笔记（N天未更新） | 移动到归档目录 |
| 草稿状态笔记 | 移动到归档目录 |
| 临时文件（Untitled、Temp） | 直接删除 |
| 空白笔记 | 直接删除 |

### backup.py - 自动备份

自动备份知识库，支持压缩和增量备份。

```bash
# 创建压缩备份
python3 backup.py --vault /path/to/vault --destination /path/to/backups

# 增量备份
python3 backup.py --vault /path/to/vault --destination /path/to/backups --incremental

# 列出所有备份
python3 backup.py --vault /path/to/vault --destination /path/to/backups --list

# 恢复备份
python3 backup.py --vault /path/to/vault --destination /path/to/backups --restore backup_20250101_120000

# 验证备份
python3 backup.py --vault /path/to/vault --destination /path/to/backups --verify backup_20250101_120000
```

**备份特性：**

- 支持压缩备份（tar.gz）
- 支持增量备份（只备份变更文件）
- 自动清理旧版本（保留最近N个）
- 排除 `.obsidian`、`.trash` 等目录

## 定时任务配置

### launchd plist 文件

| 文件 | 执行时间 | 任务 |
|------|----------|------|
| `com.obsidian.backup.plist` | 每天 23:00 | 备份知识库 |
| `com.obsidian.organize.plist` | 每天 21:00 | 整理笔记 |
| `com.obsidian.update_index.plist` | 每天 22:30 | 更新索引 |
| `com.obsidian.cleanup.plist` | 每周日 22:00 | 清理过期内容 |

### 管理 launchd 任务

```bash
# 查看任务状态
launchctl list | grep obsidian

# 停止任务
launchctl unload ~/Library/LaunchAgents/com.obsidian.backup.plist

# 重新加载
launchctl load ~/Library/LaunchAgents/com.obsidian.backup.plist

# 查看日志
tail -f /tmp/obsidian_backup.log
```

## 项目结构

```
Obsidian自动化脚本库/
├── README.md
├── scripts/
│   ├── organize.py       # 自动整理
│   ├── update_index.py   # 更新索引
│   ├── cleanup.py        # 清理过期内容
│   └── backup.py         # 自动备份
└── launchd/
    ├── com.obsidian.backup.plist
    ├── com.obsidian.organize.plist
    ├── com.obsidian.update_index.plist
    └── com.obsidian.cleanup.plist
```

## 与其他工具集成

### Obsidian 插件

推荐配合以下 Obsidian 插件使用：

| 插件 | 说明 |
|------|------|
| Templater | 模板自动化 |
| Dataview | 数据查询和统计 |
| Obsidian Git | Git 版本控制（额外备份层） |

### Linux cron 配置

```bash
# 编辑 crontab
crontab -e

# 添加定时任务
0 23 * * * /usr/bin/python3 ~/obsidian/scripts/backup.py --vault ~/vault --destination ~/backups
0 21 * * * /usr/bin/python3 ~/obsidian/scripts/organize.py --vault ~/vault
30 22 * * * /usr/bin/python3 ~/obsidian/scripts/update_index.py --vault ~/vault
0 22 * * 0 /usr/bin/python3 ~/obsidian/scripts/cleanup.py --vault ~/vault --days 90
```

## 许可证

MIT License