#!/usr/bin/env python3
"""
Script to rename all references from 'buddy' to 'pal' in MyRecoveryPal codebase.
This handles various case formats and ensures consistent renaming.
"""

import os
import re
import argparse
from pathlib import Path
from typing import List, Tuple, Set

class BuddyToPalRenamer:
    def __init__(self, dry_run=True, verbose=False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.changes_made = []
        self.files_to_rename = []
        
        # Define replacement patterns (order matters - most specific first)
        self.replacements = [
            # Model and class names
            ('RecoveryBuddy', 'RecoveryPal'),
            ('recovery_buddy', 'recovery_pal'),
            ('RECOVERY_BUDDY', 'RECOVERY_PAL'),
            
            # URL patterns and view names
            ('buddy_dashboard', 'pal_dashboard'),
            ('request_buddy', 'request_pal'),
            ('buddy_relationships', 'pal_relationships'),
            ('buddy_relationship', 'pal_relationship'),
            
            # Template references
            ('buddy_dashboard.html', 'pal_dashboard.html'),
            ('request_buddy.html', 'request_pal.html'),
            
            # Form names
            ('RecoveryBuddyForm', 'RecoveryPalForm'),
            
            # Database fields and related names
            ('buddy_relationships_as_user1', 'pal_relationships_as_user1'),
            ('buddy_relationships_as_user2', 'pal_relationships_as_user2'),
            
            # Method names
            ('get_recovery_buddy', 'get_recovery_pal'),
            ('has_buddy', 'has_pal'),
            
            # Plural forms - specific cases first
            ('Recovery Buddies', 'Recovery Pals'),
            ('recovery buddies', 'recovery pals'),
            ('Recovery buddies', 'Recovery pals'),
            
            # URL paths with plural
            ('/buddies/', '/pals/'),
            ('buddies/', 'pals/'),
            
            # Comments and strings - case variations
            ('Recovery buddy', 'Recovery pal'),
            ('recovery buddy', 'recovery pal'),
            ('Recovery Buddy', 'Recovery Pal'),
            
            # Plural forms - general
            ('BUDDIES', 'PALS'),
            ('Buddies', 'Pals'),
            ('buddies', 'pals'),
            
            # Singular forms - should come after plurals to avoid partial replacements
            ('BUDDY', 'PAL'),
            ('Buddy', 'Pal'),
            ('buddy', 'pal'),
        ]
        
        # File extensions to process
        self.valid_extensions = {
            '.py', '.html', '.txt', '.md', '.yml', '.yaml', 
            '.json', '.js', '.css', '.rst', '.cfg', '.ini',
            '.sh', '.env', '.example'
        }
        
        # Directories to skip
        self.skip_dirs = {
            '.git', '__pycache__', 'node_modules', 'venv', 
            'env', '.env', 'migrations', 'static_root', 
            'media', '.idea', '.vscode', 'htmlcov',
            '.pytest_cache', '.tox'
        }
        
        # Files to skip
        self.skip_files = {
            '.gitignore', '.dockerignore', 'rename_buddy_to_pal.py'
        }

    def should_process_file(self, filepath: Path) -> bool:
        """Check if file should be processed."""
        # Skip if in skip list
        if filepath.name in self.skip_files:
            return False
            
        # Skip binary files
        if filepath.suffix in {'.pyc', '.pyo', '.so', '.dll', '.exe', '.zip', '.tar', '.gz'}:
            return False
            
        # Process if has valid extension
        if filepath.suffix in self.valid_extensions:
            return True
            
        # Also process files without extension (like Dockerfile, Makefile)
        if not filepath.suffix and filepath.is_file():
            try:
                # Check if it's a text file
                with open(filepath, 'r', encoding='utf-8') as f:
                    f.read(512)  # Try reading first 512 bytes
                return True
            except:
                return False
                
        return False

    def should_process_directory(self, dirpath: Path) -> bool:
        """Check if directory should be processed."""
        return dirpath.name not in self.skip_dirs

    def replace_in_content(self, content: str) -> Tuple[str, List[str]]:
        """Replace all buddy references with pal in content."""
        modified_content = content
        changes = []
        
        for old_pattern, new_pattern in self.replacements:
            if old_pattern in modified_content:
                # Count occurrences before replacement
                count = modified_content.count(old_pattern)
                modified_content = modified_content.replace(old_pattern, new_pattern)
                changes.append(f"  '{old_pattern}' -> '{new_pattern}' ({count} occurrences)")
        
        return modified_content, changes

    def process_file(self, filepath: Path):
        """Process a single file."""
        try:
            # Read file content
            with open(filepath, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # Replace content
            modified_content, changes = self.replace_in_content(original_content)
            
            # Only proceed if changes were made
            if original_content != modified_content:
                if self.verbose or not self.dry_run:
                    print(f"\n📝 Processing: {filepath}")
                    for change in changes:
                        print(change)
                
                if not self.dry_run:
                    # Write modified content back
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(modified_content)
                    print(f"  ✅ Updated file")
                
                self.changes_made.append((str(filepath), changes))
            
            # Check if filename needs renaming
            if 'buddy' in filepath.name.lower():
                new_name = filepath.name
                for old_pattern, new_pattern in self.replacements:
                    new_name = new_name.replace(old_pattern, new_pattern)
                
                if new_name != filepath.name:
                    new_path = filepath.parent / new_name
                    self.files_to_rename.append((filepath, new_path))
                    if self.verbose:
                        print(f"  📁 File needs renaming: {filepath.name} -> {new_name}")
                        
        except Exception as e:
            print(f"❌ Error processing {filepath}: {e}")

    def rename_files(self):
        """Rename files that contain 'buddy' in their names."""
        if not self.files_to_rename:
            return
            
        print(f"\n📁 Files to rename: {len(self.files_to_rename)}")
        for old_path, new_path in self.files_to_rename:
            print(f"  {old_path.name} -> {new_path.name}")
            if not self.dry_run:
                try:
                    old_path.rename(new_path)
                    print(f"    ✅ Renamed")
                except Exception as e:
                    print(f"    ❌ Error: {e}")

    def process_directory(self, root_dir: str):
        """Process all files in directory recursively."""
        root_path = Path(root_dir)
        
        if not root_path.exists():
            print(f"❌ Directory not found: {root_dir}")
            return
        
        print(f"🔍 Scanning directory: {root_dir}")
        print(f"{'DRY RUN MODE' if self.dry_run else 'LIVE MODE'} - {'Verbose' if self.verbose else 'Summary only'}")
        print("-" * 50)
        
        # Collect all files to process
        files_to_process = []
        for dirpath, dirnames, filenames in os.walk(root_path):
            dirpath_obj = Path(dirpath)
            
            # Filter directories to skip
            dirnames[:] = [d for d in dirnames if self.should_process_directory(Path(dirpath) / d)]
            
            # Process files
            for filename in filenames:
                filepath = dirpath_obj / filename
                if self.should_process_file(filepath):
                    files_to_process.append(filepath)
        
        print(f"Found {len(files_to_process)} files to check\n")
        
        # Process all files
        for filepath in files_to_process:
            self.process_file(filepath)
        
        # Summary
        print("\n" + "=" * 50)
        print("SUMMARY")
        print("=" * 50)
        
        if self.changes_made:
            print(f"\n✅ Files with changes: {len(self.changes_made)}")
            if not self.verbose:
                for filepath, changes in self.changes_made[:10]:  # Show first 10
                    print(f"  - {filepath}")
                if len(self.changes_made) > 10:
                    print(f"  ... and {len(self.changes_made) - 10} more")
        else:
            print("\n✅ No changes needed")
        
        # Handle file renaming
        if self.files_to_rename:
            self.rename_files()
        
        if self.dry_run and (self.changes_made or self.files_to_rename):
            print("\n⚠️  This was a DRY RUN. No files were modified.")
            print("Run with --execute flag to apply changes.")

    def create_migration_notes(self):
        """Create notes about database migrations needed."""
        migration_notes = """
DATABASE MIGRATION NOTES
========================

After running this script, you'll need to create Django migrations for the model changes:

1. Create migrations:
   ```bash
   python manage.py makemigrations accounts
   ```

2. Review the generated migration file carefully. You may need to:
   - Add a data migration to rename the database table from 'accounts_recoverybuddy' to 'accounts_recoverypal'
   - Update any foreign key references
   - Handle any custom database constraints

3. Example custom migration operations to add:
   ```python
   operations = [
       migrations.RenameModel(
           old_name='RecoveryBuddy',
           new_name='RecoveryPal',
       ),
       migrations.RenameField(
           model_name='user',
           old_name='buddy_relationships_as_user1',
           new_name='pal_relationships_as_user1',
       ),
       migrations.RenameField(
           model_name='user',
           old_name='buddy_relationships_as_user2',
           new_name='pal_relationships_as_user2',
       ),
   ]
   ```

4. Apply migrations:
   ```bash
   python manage.py migrate
   ```

5. Update any existing data in the database if needed.

6. Clear cache:
   ```bash
   python manage.py clear_cache
   ```

7. Restart your development server.
"""
        
        if not self.dry_run and self.changes_made:
            with open('MIGRATION_NOTES.txt', 'w') as f:
                f.write(migration_notes)
            print("\n📋 Created MIGRATION_NOTES.txt with database migration instructions")


def main():
    parser = argparse.ArgumentParser(
        description='Rename all "buddy" references to "pal" in MyRecoveryPal codebase'
    )
    parser.add_argument(
        'directory',
        nargs='?',
        default='.',
        help='Root directory to process (default: current directory)'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Execute changes (default is dry run)'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Show detailed output'
    )
    
    args = parser.parse_args()
    
    # Create renamer instance
    renamer = BuddyToPalRenamer(
        dry_run=not args.execute,
        verbose=args.verbose
    )
    
    # Process directory
    renamer.process_directory(args.directory)
    
    # Create migration notes if changes were made
    if not renamer.dry_run and renamer.changes_made:
        renamer.create_migration_notes()


if __name__ == '__main__':
    main()