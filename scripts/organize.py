"""自动整理未归类笔记

将收件箱或未分类的笔记整理到正确的目录。
"""

import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class NoteOrganizer:
    """笔记整理器"""

    # 分类规则：关键词 → 目录
    CLASSIFICATION_RULES = {
        "读书笔记": {
            "keywords": ["书名", "作者", "读书", "阅读笔记", "书籍", "摘录"],
            "target_dir": "01-信息输入/阅读笔记",
            "file_prefix": "《",
        },
        "播客笔记": {
            "keywords": ["播客", "节目", "EP", "收听", "谈话"],
            "target_dir": "01-信息输入/播客笔记",
        },
        "课程笔记": {
            "keywords": ["课程", "学习", "Coursera", " Udemy", "视频"],
            "target_dir": "01-信息输入/课程笔记",
        },
        "概念笔记": {
            "keywords": ["概念", "定义", "是什么", "理解", "原理"],
            "target_dir": "03-知识整理/概念笔记",
        },
        "思维模型": {
            "keywords": ["思维模型", "框架", "方法论", "原则"],
            "target_dir": "03-知识整理/思维模型",
        },
        "人物档案": {
            "keywords": ["人物", "传记", "人物分析", "生平"],
            "target_dir": "03-知识整理/人物档案",
            "file_prefix": "人物_",
        },
        "项目笔记": {
            "keywords": ["项目", "进度", "里程碑", "V1", "V2", "版本"],
            "target_dir": "02-项目记录/进行中",
        },
        "会议记录": {
            "keywords": ["会议", "参会", "决议", "纪要", "行动项"],
            "target_dir": "02-项目记录/会议记录",
            "file_prefix": "会议_",
        },
        "周复盘": {
            "keywords": ["周复盘", "周报", "本周", "周总结"],
            "target_dir": "05-复盘归档/周复盘",
        },
        "月复盘": {
            "keywords": ["月复盘", "月报", "本月", "月总结"],
            "target_dir": "05-复盘归档/月复盘",
        },
        "文章": {
            "keywords": ["文章", "发表", "发布", "公众号"],
            "target_dir": "04-输出创作/文章",
        },
        "草稿": {
            "keywords": ["草稿", "draft", "待写"],
            "target_dir": "04-输出创作/草稿",
        },
        "日记": {
            "keywords": ["日记", "日志", "每日"],
            "target_dir": "01-信息输入",
            "file_pattern": r"\d{4}-\d{2}-\d{2}",
        },
    }

    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.inbox_path = self.vault_path / "01-信息输入" / "收件箱"
        self.log: List[Dict[str, str]] = []

    def scan_inbox(self) -> List[Path]:
        """扫描收件箱中的所有笔记"""
        if not self.inbox_path.exists():
            return []

        notes = []
        for file in self.inbox_path.glob("*.md"):
            if not file.name.startswith("_"):
                notes.append(file)
        return notes

    def scan_uncategorized(self) -> List[Path]:
        """扫描库中未分类的笔记（没有标签的）"""
        uncategorized = []
        for file in self.vault_path.rglob("*.md"):
            if file.name.startswith("_"):
                continue
            content = file.read_text(encoding="utf-8")
            if not self._has_tags(content):
                uncategorized.append(file)
        return uncategorized

    def _has_tags(self, content: str) -> bool:
        """检查笔记是否有标签"""
        # 检查 YAML frontmatter 中的 tags
        if re.search(r"^tags:.*", content, re.MULTILINE):
            return True
        # 检查 inline tags
        if re.search(r"#[a-zA-Z\u4e00-\u9fff]+", content):
            return True
        return False

    def classify_note(self, note_path: Path) -> Tuple[str, str]:
        """分类单条笔记"""
        content = note_path.read_text(encoding="utf-8")
        filename = note_path.stem

        # 根据关键词匹配分类
        for category, rule in self.CLASSIFICATION_RULES.items():
            # 检查文件名匹配
            if "file_pattern" in rule:
                if re.search(rule["file_pattern"], filename):
                    return rule["target_dir"], category

            # 检查关键词匹配
            for keyword in rule["keywords"]:
                if keyword.lower() in content.lower() or keyword in filename:
                    return rule["target_dir"], category

        # 默认分类
        return "01-信息输入", "未分类"

    def organize(
        self,
        source: Optional[str] = None,
        dry_run: bool = False,
        rename: bool = True,
    ) -> Dict[str, int]:
        """执行整理"""
        stats = {"processed": 0, "moved": 0, "renamed": 0, "skipped": 0}

        # 确定源目录
        if source:
            source_path = Path(source)
            notes = list(source_path.glob("*.md"))
        else:
            notes = self.scan_inbox() + self.scan_uncategorized()

        for note in notes:
            stats["processed"] += 1
            target_dir, category = self.classify_note(note)

            # 创建目标目录
            target_path = self.vault_path / target_dir
            if not target_path.exists():
                if not dry_run:
                    target_path.mkdir(parents=True, exist_ok=True)

            # 确定新文件名
            new_name = note.name
            if rename and category in self.CLASSIFICATION_RULES:
                rule = self.CLASSIFICATION_RULES[category]
                if "file_prefix" in rule:
                    new_name = f"{rule['file_prefix']}{note.stem}.md"

            # 移动文件
            new_path = target_path / new_name

            if new_path.exists():
                stats["skipped"] += 1
                self.log.append({
                    "action": "skip",
                    "file": str(note),
                    "reason": "目标文件已存在",
                })
                continue

            if not dry_run:
                shutil.move(str(note), str(new_path))
                if new_name != note.name:
                    stats["renamed"] += 1

            stats["moved"] += 1
            self.log.append({
                "action": "move",
                "file": str(note),
                "to": str(new_path),
                "category": category,
            })

        return stats

    def get_log(self) -> List[Dict[str, str]]:
        """获取整理日志"""
        return self.log

    def print_summary(self):
        """打印整理摘要"""
        print("\n整理摘要：")
        print("=" * 50)
        for entry in self.log:
            if entry["action"] == "move":
                print(f"✓ {entry['file']} → {entry['to']} ({entry['category']})")
            elif entry["action"] == "skip":
                print(f"✗ {entry['file']} (跳过: {entry['reason']})")


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="自动整理未归类笔记")
    parser.add_argument("--vault", "-v", required=True, help="Obsidian 库路径")
    parser.add_argument("--source", "-s", help="源目录（默认收件箱）")
    parser.add_argument("--dry-run", action="store_true", help="预览模式")
    parser.add_argument("--no-rename", action="store_true", help="不重命名文件")

    args = parser.parse_args()

    organizer = NoteOrganizer(args.vault)
    stats = organizer.organize(
        source=args.source,
        dry_run=args.dry_run,
        rename=not args.no_rename,
    )

    print(f"\n处理: {stats['processed']} 条笔记")
    print(f"移动: {stats['moved']} 条")
    print(f"重命名: {stats['renamed']} 条")
    print(f"跳过: {stats['skipped']} 条")

    if args.dry_run:
        print("\n(预览模式，未实际修改文件)")
    else:
        organizer.print_summary()


if __name__ == "__main__":
    main()