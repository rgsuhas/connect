#!/usr/bin/env python3
"""
Directory Structure Bootstrap for Pi Player
Creates all required directories with proper permissions on first run
"""

import os
import stat
from pathlib import Path

def init_directories():
    """Create all required directories for Pi Player"""
    
    base_dir = Path.cwd()
    print(f"🏗️  Initializing Pi Player directories in: {base_dir}")
    
    # Required directories
    directories = {
        "default_assets": "Ships with bundled sample videos",
        "media_cache": "Stores downloaded or transcoded assets", 
        "logs": "Holds rotating log files",
        "playlists": "Contains JSON playlists",
        "services": "Systemd service files",
        "__pycache__": "Python bytecode cache (auto-created)"
    }
    
    created_dirs = []
    existing_dirs = []
    
    for dir_name, description in directories.items():
        dir_path = base_dir / dir_name
        
        if dir_path.exists():
            existing_dirs.append(dir_name)
            print(f"  ✓ {dir_name}/ - {description} (exists)")
        else:
            dir_path.mkdir(parents=True, exist_ok=True)
            # Set proper permissions (755 for directories)
            dir_path.chmod(stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
            created_dirs.append(dir_name)
            print(f"  ✅ {dir_name}/ - {description} (created)")
    
    # Create gitignore entries for cache and logs
    gitignore_path = base_dir / ".gitignore"
    gitignore_entries = [
        "# Pi Player runtime files",
        "media_cache/",
        "logs/*.log",
        "current_playlist.json",
        "playback_state.json", 
        "last_playback.json",
        "__pycache__/",
        "*.pyc",
        "*.pyo",
        ""
    ]
    
    if gitignore_path.exists():
        existing_content = gitignore_path.read_text()
        new_entries = [entry for entry in gitignore_entries if entry not in existing_content]
        if new_entries:
            with open(gitignore_path, 'a') as f:
                f.write('\n' + '\n'.join(new_entries))
            print(f"  📝 Updated .gitignore with {len(new_entries)} new entries")
        else:
            print(f"  ✓ .gitignore already contains Pi Player entries")
    else:
        gitignore_path.write_text('\n'.join(gitignore_entries))
        print(f"  📝 Created .gitignore with Pi Player entries")
    
    # Create placeholder files to ensure directories are preserved in git
    placeholder_files = {
        "media_cache/.gitkeep": "Keep media cache directory in git",
        "logs/.gitkeep": "Keep logs directory in git"
    }
    
    for file_path, description in placeholder_files.items():
        full_path = base_dir / file_path
        if not full_path.exists():
            full_path.write_text(description)
            print(f"  📋 Created {file_path}")
    
    # Summary
    print(f"\n📊 Directory Initialization Summary:")
    print(f"   Created: {len(created_dirs)} directories")
    print(f"   Existing: {len(existing_dirs)} directories")
    print(f"   Base Path: {base_dir}")
    
    if created_dirs:
        print(f"   New directories: {', '.join(created_dirs)}")
    
    # Verify permissions
    print(f"\n🔐 Directory Permissions:")
    for dir_name in directories.keys():
        dir_path = base_dir / dir_name
        if dir_path.exists():
            perms = oct(dir_path.stat().st_mode)[-3:]
            print(f"   {dir_name}/: {perms}")
    
    return {
        "base_dir": str(base_dir),
        "created": created_dirs,
        "existing": existing_dirs,
        "total": len(directories)
    }

if __name__ == "__main__":
    print("🚀 Pi Player Directory Bootstrap")
    print("=" * 50)
    
    try:
        result = init_directories()
        print(f"\n✅ Directory initialization complete!")
        print(f"   All {result['total']} directories are ready")
        
    except Exception as e:
        print(f"\n❌ Directory initialization failed: {e}")
        raise