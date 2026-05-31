"""自动更新索引

扫描知识库并自动生成索引文件。
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set


class IndexUpdater:
    """索引更新器"""

    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.notes: Dict[str, Dict] = {}
        self.tags: Dict[str, Set[str]] = {}
        self.links: Dict[str, Set[str]] = {}

    def scan_all_notes(self) -> Dict[str, Dict]:
        """扫描所有笔记"""
        for file in self.vault_path.rglob("*.md"):
            if file.name.startswith("_"):
                continue

            content = file.read_text(encoding="utf-8")
            relative_path = file.relative_to(self.vault_path)

            note_info = {
                "path": str(relative_path),
                "title": self._extract_title(content) or file.stem,
                "tags": self._extract_tags(content),
                "links": self._extract_links(content),
                "created": self._extract_created_date(content),
                "modified": datetime.fromtimestamp(file.stat().st_mtime).strftime("%Y-%m-%d"),
                "word_count": len(content.split()),
                "line_count": len(content.split("\n")),
            }

            self.notes[file.stem] = note_info

            # 收集标签统计
            for tag in note_info["tags"]:
                if tag not in self.tags:
                    self.tags[tag] = set()
                self.tags[tag].add(file.stem)

            # 收集链接统计
            for link in note_info["links"]:
                if link not in self.links:
                    self.links[link] = set()
                self.links[link].add(file.stem)

        return self.notes

    def _extract_title(self, content: str) -> Optional[str]:
        """提取标题"""
        match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return None

    def _extract_tags(self, content: str) -> List[str]:
        """提取标签"""
        tags = []

        # YAML frontmatter tags
        yaml_match = re.search(r"tags:\s*\[([^\]]+)\]", content)
        if yaml_match:
            tags.extend([t.strip() for t in yaml_match.group(1).split(",")])

        yaml_match2 = re.search(r"tags:\s*\n(\s+-\s+.+\n)+", content)
        if yaml_match2:
            for line in yaml_match2.group(0).split("\n"):
                if line.strip().startswith("-"):
                    tags.append(line.strip().replace("- ", "").strip())

        # Inline tags
        inline_tags = re.findall(r"#([a-zA-Z\u4e00-\u9fff/]+)", content)
        tags.extend(inline_tags)

        return list(set(tags))

    def _extract_links(self, content: str) -> List[str]:
        """提取双向链接"""
        links = re.findall(r"\[\[([^\]]+)\]\]", content)
        # 处理带显示文本的链接 [[文件名|显示文本]]
        clean_links = []
        for link in links:
            if "|" in link:
                clean_links.append(link.split("|")[0].strip())
            else:
                clean_links.append(link.strip())
        return list(set(clean_links))

    def _extract_created_date(self, content: str) -> Optional[str]:
        """提取创建日期"""
        match = re.search(r"创建时间:\s*([0-9:-]+)", content)
        if match:
            return match.group(1).strip()
        match = re.search(r"created:\s*([0-9-]+)", content)
        if match:
            return match.group(1).strip()
        return None

    def generate_main_index(self) -> str:
        """生成主索引"""
        sections = [
            "# 索引",
            "",
            "> 自动生成的知识库索引，定期更新。",
            "",
            "## 统计概览",
            "",
            f"- **总笔记数：** {len(self.notes)}",
            f"- **总标签数：** {len(self.tags)}",
            f"- **总链接数：** {len(self.links)}",
            f"- **更新时间：** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
        ]

        # 按标签分类
        sections.append("## 按标签分类\n")

        # 类型标签
        type_tags = {t: s for t, s in self.tags.items() if t.startswith("type/")}
        if type_tags:
            sections.append("### 笔记类型\n")
            sections.append("| 类型 | 笔记数 | 示例 |")
            sections.append("|------|--------|------|")
            for tag, notes in sorted(type_tags.items(), key=lambda x: -len(x[1])):
                examples = list(notes)[:3]
                sections.append(f"| {tag.replace('type/', '')} | {len(notes)} | [[{', '.join(examples[:2])}]] |")
            sections.append("")

        # 状态标签
        status_tags = {t: s for t, s in self.tags.items() if t.startswith("status/")}
        if status_tags:
            sections.append("### 笔记状态\n")
            for tag, notes in sorted(status_tags.items()):
                sections.append(f"**{tag.replace('status/', '')}：** {len(notes)} 条")
                for note in list(notes)[:5]:
                    sections.append(f"- [[{note}]]")
                sections.append("")

        # 领域标签
        domain_tags = {t: s for t, s in self.tags.items() if t.startswith("领域/")}
        if domain_tags:
            sections.append("### 知识领域\n")
            sections.append("| 领域 | 笔记数 |")
            sections.append("|------|--------|")
            for tag, notes in sorted(domain_tags.items(), key=lambda x: -len(x[1])):
                sections.append(f"| {tag.replace('领域/', '')} | {len(notes)} |")
            sections.append("")

        # 最近更新
        sections.append("## 最近更新\n")
        sections.append("| 笔记 | 更新日期 |")
        sections.append("|------|----------|")

        recent = sorted(
            self.notes.items(),
            key=lambda x: x[1]["modified"],
            reverse=True
        )[:10]

        for name, info in recent:
            sections.append(f"| [[{name}]] | {info['modified']} |")
        sections.append("")

        # 高频链接
        sections.append("## 高频引用\n")
        sections.append("| 笔记 | 被引用数 |")
        sections.append("|------|----------|")

        linked = sorted(self.links.items(), key=lambda x: -len(x[1]))[:10]
        for link, sources in linked:
            sections.append(f"| [[{link}]] | {len(sources)} |")
        sections.append("")

        return "\n".join(sections)

    def generate_tag_index(self) -> str:
        """生成标签索引"""
        lines = [
            "# 标签索引",
            "",
            f"> 共 {len(self.tags)} 个标签",
            "",
        ]

        # 按字母顺序排列
        for tag in sorted(self.tags.keys()):
            notes = self.tags[tag]
            lines.append(f"## {tag}")
            lines.append("")
            lines.append(f"({len(notes)} 条笔记)")
            lines.append("")
            for note in sorted(notes):
                lines.append(f"- [[{note}]]")
            lines.append("")

        return "\n".join(lines)

    def generate_link_graph(self) -> str:
        """生成链接图谱（Markdown 版）"""
        lines = [
            "# 链接图谱",
            "",
            f"> 共 {len(self.links)} 个链接关系",
            "",
        ]

        for target, sources in sorted(self.links.items(), key=lambda x: -len(x[1])):
            lines.append(f"## [[{target}]]")
            lines.append("")
            lines.append(f"被 {len(sources)} 条笔记引用：")
            lines.append("")
            for source in sorted(sources):
                lines.append(f"- [[{source}]] → [[{target}]]")
            lines.append("")

        return "\n".join(lines)

    def update_index_files(
        self,
        main_index: str = "索引.md",
        tag_index: str = "标签索引.md",
        link_index: str = "链接图谱.md",
    ):
        """更新索引文件"""
        # 主索引
        main_path = self.vault_path / main_index
        main_path.write_text(self.generate_main_index(), encoding="utf-8")
        print(f"已更新: {main_path}")

        # 标签索引
        tag_path = self.vault_path / tag_index
        tag_path.write_text(self.generate_tag_index(), encoding="utf-8")
        print(f"已更新: {tag_path}")

        # 链接图谱
        link_path = self.vault_path / link_index
        link_path.write_text(self.generate_link_graph(), encoding="utf-8")
        print(f"已更新: {link_path}")


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="自动更新知识库索引")
    parser.add_argument("--vault", "-v", required=True, help="Obsidian 库路径")
    parser.add_argument("--output-main", default="索引.md", help="主索引文件名")
    parser.add_argument("--output-tags", default="标签索引.md", help="标签索引文件名")
    parser.add_argument("--output-links", default="链接图谱.md", help="链接图谱文件名")

    args = parser.parse_args()

    updater = IndexUpdater(args.vault)
    updater.scan_all_notes()

    print(f"\n扫描完成：")
    print(f"- 笔记: {len(updater.notes)} 条")
    print(f"- 标签: {len(updater.tags)} 个")
    print(f"- 链接: {len(updater.links)} 个\n")

    updater.update_index_files(
        main_index=args.output_main,
        tag_index=args.output_tags,
        link_index=args.output_links,
    )


if __name__ == "__main__":
    main()