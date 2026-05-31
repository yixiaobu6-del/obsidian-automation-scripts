"""自动清理过期内容

清理长期未更新、草稿状态、临时文件等过期内容。
"""

import os
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class ContentCleaner:
    """内容清理器"""

    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.archive_path = self.vault_path / "05-复盘归档" / "归档"
        self.log: List[Dict] = []

    def find_stale_notes(
        self,
        days: int = 30,
        exclude_dirs: Optional[List[str]] = None,
    ) -> List[Path]:
        """查找长期未更新的笔记"""
        exclude_dirs = exclude_dirs or ["05-复盘归档", "assets", "06-模板脚本"]
        cutoff_date = datetime.now() - timedelta(days=days)
        stale_notes = []

        for file in self.vault_path.rglob("*.md"):
            # 排除目录
            if any(ex_dir in file.parts for ex_dir in exclude_dirs):
                continue
            if file.name.startswith("_"):
                continue

            # 检查修改日期
            mtime = datetime.fromtimestamp(file.stat().st_mtime)
            if mtime < cutoff_date:
                stale_notes.append(file)

        return stale_notes

    def find_draft_notes(self) -> List[Path]:
        """查找草稿状态的笔记"""
        drafts = []
        for file in self.vault_path.rglob("*.md"):
            if file.name.startswith("_"):
                continue

            content = file.read_text(encoding="utf-8")

            # 检查状态标签
            if re.search(r"#status/初稿|#status/draft", content):
                drafts.append(file)

            # 检查标题
            if "草稿" in file.stem.lower() or "draft" in file.stem.lower():
                drafts.append(file)

        return drafts

    def find_temp_files(self) -> List[Path]:
        """查找临时文件"""
        temp_files = []

        for file in self.vault_path.rglob("*"):
            if file.is_dir():
                continue

            # 临时文件特征
            temp_patterns = [
                r"^Untitled",
                r"^Untitled-\d+",
                r"^New note",
                r"^Temp",
                r"^\d{13}",  # timestamp filenames
                r"^scratch",
            ]

            for pattern in temp_patterns:
                if re.search(pattern, file.stem, re.IGNORECASE):
                    temp_files.append(file)
                    break

        return temp_files

    def find_empty_notes(self) -> List[Path]:
        """查找空白笔记"""
        empty = []
        for file in self.vault_path.rglob("*.md"):
            content = file.read_text(encoding="utf-8").strip()

            # 只包含空内容的笔记
            if not content or content == "":
                empty.append(file)
                continue

            # 只有 YAML frontmatter 的笔记
            if re.match(r"^---\n.*\n---\n?$", content):
                empty.append(file)

        return empty

    def find_duplicate_notes(self) -> List[Tuple[Path, Path]]:
        """查找可能重复的笔记"""
        notes_by_title: Dict[str, List[Path]] = {}

        for file in self.vault_path.rglob("*.md"):
            content = file.read_text(encoding="utf-8")
            title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)

            if title_match:
                title = title_match.group(1).strip()
                if title not in notes_by_title:
                    notes_by_title[title] = []
                notes_by_title[title].append(file)

        duplicates = []
        for title, files in notes_by_title.items():
            if len(files) > 1:
                duplicates.append((files[0], files[1]))

        return duplicates

    def archive_note(self, note_path: Path, dry_run: bool = False) -> bool:
        """归档笔记"""
        if not self.archive_path.exists():
            if not dry_run:
                self.archive_path.mkdir(parents=True, exist_ok=True)

        # 添加归档日期前缀
        archive_date = datetime.now().strftime("%Y-%m-%d")
        new_name = f"{archive_date}_{note_path.name}"
        archive_path = self.archive_path / new_name

        if not dry_run:
            shutil.move(str(note_path), str(archive_path))

        self.log.append({
            "action": "archive",
            "file": str(note_path),
            "to": str(archive_path),
        })
        return True

    def delete_note(self, note_path: Path, dry_run: bool = False) -> bool:
        """删除笔记"""
        if not dry_run:
            note_path.unlink()

        self.log.append({
            "action": "delete",
            "file": str(note_path),
        })
        return True

    def cleanup(
        self,
        stale_days: int = 90,
        archive_stale: bool = True,
        delete_temp: bool = True,
        delete_empty: bool = True,
        dry_run: bool = False,
    ) -> Dict[str, int]:
        """执行清理"""
        stats = {
            "stale_found": 0,
            "draft_found": 0,
            "temp_found": 0,
            "empty_found": 0,
            "archived": 0,
            "deleted": 0,
        }

        # 查找各类过期内容
        stale_notes = self.find_stale_notes(days=stale_days)
        draft_notes = self.find_draft_notes()
        temp_files = self.find_temp_files()
        empty_notes = self.find_empty_notes()

        stats["stale_found"] = len(stale_notes)
        stats["draft_found"] = len(draft_notes)
        stats["temp_found"] = len(temp_files)
        stats["empty_found"] = len(empty_notes)

        # 处理过期笔记
        if archive_stale:
            for note in stale_notes:
                self.archive_note(note, dry_run)
                stats["archived"] += 1

        # 处理临时文件
        if delete_temp:
            for file in temp_files:
                self.delete_note(file, dry_run)
                stats["deleted"] += 1

        # 处理空白笔记
        if delete_empty:
            for note in empty_notes:
                self.delete_note(note, dry_run)
                stats["deleted"] += 1

        return stats

    def generate_report(self) -> str:
        """生成清理报告"""
        lines = [
            "# 清理报告",
            "",
            f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## 操作记录",
            "",
        ]

        for entry in self.log:
            if entry["action"] == "archive":
                lines.append(f"归档: {entry['file']} → {entry['to']}")
            elif entry["action"] == "delete":
                lines.append(f"删除: {entry['file']}")

        return "\n".join(lines)


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="自动清理过期内容")
    parser.add_argument("--vault", "-v", required=True, help="Obsidian 库路径")
    parser.add_argument("--days", "-d", type=int, default=90, help="过期天数阈值")
    parser.add_argument("--dry-run", action="store_true", help="预览模式")
    parser.add_argument("--no-archive", action="store_true", help="不归档过期笔记")
    parser.add_argument("--no-delete-temp", action="store_true", help="不删除临时文件")
    parser.add_argument("--no-delete-empty", action="store_true", help="不删除空白笔记")
    parser.add_argument("--report", "-r", type=str, help="生成报告文件")

    args = parser.parse_args()

    cleaner = ContentCleaner(args.vault)
    stats = cleaner.cleanup(
        stale_days=args.days,
        archive_stale=not args.no_archive,
        delete_temp=not args.no_delete_temp,
        delete_empty=not args.no_delete_empty,
        dry_run=args.dry_run,
    )

    print("\n清理统计：")
    print("=" * 50)
    print(f"过期笔记: {stats['stale_found']} 条")
    print(f"草稿笔记: {stats['draft_found']} 条")
    print(f"临时文件: {stats['temp_found']} 个")
    print(f"空白笔记: {stats['empty_found']} 条")
    print("-" * 50)
    print(f"已归档: {stats['archived']} 条")
    print(f"已删除: {stats['deleted']} 条")

    if args.dry_run:
        print("\n(预览模式，未实际修改文件)")

    if args.report:
        report_path = Path(args.report)
        report_path.write_text(cleaner.generate_report(), encoding="utf-8")
        print(f"\n报告已保存: {args.report}")


if __name__ == "__main__":
    main()