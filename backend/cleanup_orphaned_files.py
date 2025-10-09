#!/usr/bin/env python3
"""
Utility script to clean up orphaned uploaded files.
Removes files that are no longer associated with any knowledge base.
"""
import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.file_upload_service import file_upload_service


def load_knowledge_bases():
    """Load existing knowledge bases."""
    kb_file = Path("data/knowledge_bases.json")
    if kb_file.exists():
        with open(kb_file, 'r') as f:
            return json.load(f)
    return {}


def get_active_file_ids():
    """Get all file IDs that are still in use by knowledge bases."""
    active_file_ids = set()
    knowledge_bases = load_knowledge_bases()

    for kb_id, kb_data in knowledge_bases.items():
        agent_statuses = kb_data.get('agent_statuses', [])
        for agent_status in agent_statuses:
            file_ids = agent_status.get('file_ids', [])
            active_file_ids.update(file_ids)

    return active_file_ids


def cleanup_orphaned_files(dry_run=True):
    """Clean up orphaned files that are not associated with any knowledge base."""
    print("🧹 Starting orphaned file cleanup...")

    # Get active file IDs
    active_file_ids = get_active_file_ids()
    print(f"📊 Found {len(active_file_ids)} files in active knowledge bases")

    # Get all registered files
    registry = file_upload_service._file_registry
    total_files = len(registry)
    print(f"📊 Total registered files: {total_files}")

    # Find orphaned files in registry
    orphaned_files = []
    total_size = 0

    for file_id, file_info in registry.items():
        if file_id not in active_file_ids:
            orphaned_files.append((file_id, file_info))
            total_size += file_info.file_size

    print(f"🗑️ Found {len(orphaned_files)} orphaned files in registry ({total_size / (1024*1024):.2f} MB)")

    # Also check for files on disk not in registry
    uploads_dir = Path("uploads")
    unregistered_files = []
    unregistered_size = 0

    if uploads_dir.exists():
        for category_dir in uploads_dir.iterdir():
            if category_dir.is_dir():
                for file_path in category_dir.iterdir():
                    if file_path.is_file():
                        # Check if this file is in the registry
                        found_in_registry = False
                        for file_info in registry.values():
                            if str(file_path) == file_info.file_path or str(file_path) == file_info.upload_path:
                                found_in_registry = True
                                break

                        if not found_in_registry:
                            file_size = file_path.stat().st_size
                            unregistered_files.append((file_path, file_size))
                            unregistered_size += file_size

    if unregistered_files:
        print(f"🗑️ Found {len(unregistered_files)} unregistered files on disk ({unregistered_size / (1024*1024):.2f} MB)")

    total_orphaned = len(orphaned_files) + len(unregistered_files)
    total_orphaned_size = total_size + unregistered_size

    print(f"\n📊 Total cleanup: {total_orphaned} files ({total_orphaned_size / (1024*1024):.2f} MB)")

    if not orphaned_files and not unregistered_files:
        print("✅ No orphaned files to clean up")
        return

    # Show orphaned files in registry
    if orphaned_files:
        print("\nOrphaned files in registry:")
        for file_id, file_info in orphaned_files:
            size_mb = file_info.file_size / (1024*1024)
            created_at = file_info.created_at
            print(f"  - {file_info.original_filename} ({size_mb:.2f} MB) - {file_info.category.value} - created: {created_at}")

    # Show unregistered files on disk
    if unregistered_files:
        print("\nUnregistered files on disk:")
        for file_path, file_size in unregistered_files:
            size_mb = file_size / (1024*1024)
            print(f"  - {file_path.name} ({size_mb:.2f} MB) - {file_path.parent.name}")

    if dry_run:
        print("\n⚠️ DRY RUN MODE - No files will be deleted")
        print("Run with --execute flag to actually delete files")
        return

    # Delete orphaned files
    print("\n🗑️ Deleting files...")
    deleted_count = 0
    deleted_size = 0

    # Delete orphaned files in registry
    for file_id, file_info in orphaned_files:
        try:
            # Delete physical file
            file_path = Path(file_info.file_path or file_info.upload_path)
            if file_path.exists():
                file_path.unlink()

            # Remove from registry
            if file_id in file_upload_service._file_registry:
                del file_upload_service._file_registry[file_id]

            deleted_count += 1
            deleted_size += file_info.file_size
            print(f"  ✓ Deleted {file_info.original_filename}")
        except Exception as e:
            print(f"  ✗ Failed to delete {file_info.original_filename}: {e}")

    # Delete unregistered files on disk
    for file_path, file_size in unregistered_files:
        try:
            if file_path.exists():
                file_path.unlink()
                deleted_count += 1
                deleted_size += file_size
                print(f"  ✓ Deleted {file_path.name}")
        except Exception as e:
            print(f"  ✗ Failed to delete {file_path.name}: {e}")

    # Save updated registry
    file_upload_service._save_file_registry()

    print(f"\n✅ Cleanup complete!")
    print(f"   Deleted: {deleted_count} files ({deleted_size / (1024*1024):.2f} MB)")
    print(f"   Remaining: {len(file_upload_service._file_registry)} registered files")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Clean up orphaned uploaded files')
    parser.add_argument('--execute', action='store_true', help='Actually delete files (default is dry run)')
    args = parser.parse_args()

    cleanup_orphaned_files(dry_run=not args.execute)
