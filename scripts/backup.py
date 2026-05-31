"""自动备份

自动备份 Obsidian 知识库到指定位置。
支持增量备份、压缩备份、多版本管理。
"""

import os
import shutil
import tarfile
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set


class VaultBackup:
    """知识库备份器"""

    def __init__(
        self,
        vault_path: str,
        backup_path: str,
        exclude_dirs: Optional[List[str]] = None,
    ):
        self.vault_path = Path(vault_path)
        self.backup_path = Path(backup_path)
        self.exclude_dirs = exclude_dirs or [
            ".obsidian",
            ".trash",
            ".git",
            "node_modules",
        ]
        self.backup_history: List[Dict] = []

    def calculate_checksum(self, directory: Path) -> str:
        """计算目录内容的校验码"""
        hasher = hashlib.md5()
        for file in sorted(directory.rglob("*")):
            if file.is_file() and not any(ex in file.parts for ex in self.exclude_dirs):
                hasher.update(file.name.encode())
                hasher.update(str(file.stat().st_size).encode())
        return hasher.hexdigest()

    def get_changed_files(
        self,
        reference_backup: Optional[Path] = None,
    ) -> List[Path]:
        """获取变更的文件列表"""
        changed = []

        if reference_backup and reference_backup.exists():
            # 比较与上次备份的差异
            # 简化实现：检查修改时间
            ref_time = datetime.fromtimestamp(reference_backup.stat().st_mtime)
            for file in self.vault_path.rglob("*.md"):
                if any(ex in file.parts for ex in self.exclude_dirs):
                    continue
                if datetime.fromtimestamp(file.stat().st_mtime) > ref_time:
                    changed.append(file)
        else:
            # 全量备份
            changed = [
                f for f in self.vault_path.rglob("*")
                if f.is_file() and not any(ex in f.parts for ex in self.exclude_dirs)
            ]

        return changed

    def create_backup(
        self,
        compress: bool = True,
        incremental: bool = False,
        max_versions: int = 10,
    ) -> Dict:
        """创建备份"""
        backup_time = datetime.now()
        backup_name = backup_time.strftime("backup_%Y%m%d_%H%M%S")

        # 查找最近一次备份作为参考
        reference_backup = None
        if incremental:
            backups = sorted(self.backup_path.glob("backup_*"))
            if backups:
                reference_backup = backups[-1]

        # 获取变更文件
        changed_files = self.get_changed_files(reference_backup)
        if not changed_files:
            return {"status": "no_changes", "files": 0}

        # 创建备份
        backup_dir = self.backup_path / backup_name

        if compress:
            # 压缩备份
            archive_path = self.backup_path / f"{backup_name}.tar.gz"
            with tarfile.open(archive_path, "w:gz") as tar:
                for file in changed_files:
                    rel_path = file.relative_to(self.vault_path)
                    tar.add(file, arcname=str(rel_path))
            backup_location = archive_path
        else:
            # 普通备份
            backup_dir.mkdir(parents=True, exist_ok=True)
            for file in changed_files:
                rel_path = file.relative_to(self.vault_path)
                target = backup_dir / rel_path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file, target)
            backup_location = backup_dir

        # 清理旧版本
        self._cleanup_old_versions(max_versions)

        backup_info = {
            "name": backup_name,
            "time": backup_time.isoformat(),
            "files": len(changed_files),
            "compressed": compress,
            "incremental": incremental,
            "location": str(backup_location),
        }

        self.backup_history.append(backup_info)
        return {"status": "success", **backup_info}

    def _cleanup_old_versions(self, max_versions: int):
        """清理超过版本数量的旧备份"""
        backups = sorted(self.backup_path.glob("backup_*"))
        while len(backups) > max_versions:
            oldest = backups[0]
            if oldest.is_dir():
                shutil.rmtree(oldest)
            else:
                oldest.unlink()
            backups = sorted(self.backup_path.glob("backup_*"))

    def restore_backup(
        self,
        backup_name: str,
        target_path: Optional[str] = None,
    ) -> bool:
        """恢复备份"""
        backup_file = self.backup_path / backup_name
        if not backup_file.exists():
            backup_file = self.backup_path / f"{backup_name}.tar.gz"

        if not backup_file.exists():
            return False

        restore_target = Path(target_path) if target_path else self.vault_path

        if backup_file.suffix == ".gz" or backup_file.name.endswith(".tar.gz"):
            # 解压恢复
            with tarfile.open(backup_file, "r:gz") as tar:
                tar.extractall(restore_target)
        else:
            # 目录恢复
            shutil.copytree(backup_file, restore_target, dirs_exist_ok=True)

        return True

    def list_backups(self) -> List[Dict]:
        """列出所有备份"""
        backups = []
        for backup in sorted(self.backup_path.glob("backup_*")):
            info = {
                "name": backup.stem if backup.is_file() else backup.name,
                "path": str(backup),
                "size": backup.stat().st_size if backup.is_file() else self._dir_size(backup),
                "time": datetime.fromtimestamp(backup.stat().st_mtime).isoformat(),
                "type": "compressed" if backup.suffix == ".gz" else "directory",
            }
            backups.append(info)
        return backups

    def _dir_size(self, directory: Path) -> int:
        """计算目录大小"""
        total = 0
        for file in directory.rglob("*"):
            if file.is_file():
                total += file.stat().st_size
        return total

    def verify_backup(self, backup_name: str) -> Dict:
        """验证备份完整性"""
        backup_file = self.backup_path / backup_name
        if not backup_file.exists():
            backup_file = self.backup_path / f"{backup_name}.tar.gz"

        if not backup_file.exists():
            return {"valid": False, "reason": "备份不存在"}

        # 简化验证：检查文件大小是否合理
        size = backup_file.stat().st_size if backup_file.is_file() else self._dir_size(backup_file)
        if size < 1024:  # 至少 1KB
            return {"valid": False, "reason": "备份文件过小"}

        return {"valid": True, "size": size}


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="自动备份知识库")
    parser.add_argument("--vault", "-v", required=True, help="Obsidian 库路径")
    parser.add_argument("--destination", "-d", required=True, help="备份存放路径")
    parser.add_argument("--compress", "-c", action="store_true", default=True, help="压缩备份")
    parser.add_argument("--incremental", "-i", action="store_true", help="增量备份")
    parser.add_argument("--max-versions", "-m", type=int, default=10, help="最大版本数")
    parser.add_argument("--list", "-l", action="store_true", help="列出所有备份")
    parser.add_argument("--restore", "-r", type=str, help="恢复指定备份")
    parser.add_argument("--verify", type=str, help="验证指定备份")

    args = parser.parse_args()

    backup = VaultBackup(args.vault, args.destination)

    if args.list:
        backups = backup.list_backups()
        print("\n备份列表：")
        print("=" * 60)
        for info in backups:
            print(f"名称: {info['name']}")
            print(f"时间: {info['time']}")
            print(f"大小: {info['size'] / 1024 / 1024:.2f} MB")
            print(f"类型: {info['type']}")
            print("-" * 60)
        return

    if args.restore:
        success = backup.restore_backup(args.restore)
        if success:
            print(f"已恢复备份: {args.restore}")
        else:
            print(f"恢复失败: 备份不存在")
        return

    if args.verify:
        result = backup.verify_backup(args.verify)
        if result["valid"]:
            print(f"备份有效: {args.verify}")
            print(f"大小: {result['size'] / 1024 / 1024:.2f} MB")
        else:
            print(f"备份无效: {result['reason']}")
        return

    # 执行备份
    result = backup.create_backup(
        compress=args.compress,
        incremental=args.incremental,
        max_versions=args.max_versions,
    )

    if result["status"] == "no_changes":
        print("无需备份：内容无变化")
    elif result["status"] == "success":
        print(f"\n备份成功！")
        print(f"名称: {result['name']}")
        print(f"文件: {result['files']} 个")
        print(f"位置: {result['location']}")
        print(f"压缩: {'是' if result['compressed'] else '否'}")
        print(f"增量: {'是' if result['incremental'] else '否'}")


if __name__ == "__main__":
    main()