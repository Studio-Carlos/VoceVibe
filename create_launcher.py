#!/usr/bin/env python3
"""
Script to create a clickable Desktop launcher for VoceVibe4 on macOS.
"""
import os
import stat
from pathlib import Path

def create_launcher():
    # Get project directory
    project_dir = Path(os.getcwd()).resolve()
    desktop_dir = Path(os.path.expanduser("~/Desktop"))
    
    launcher_path = desktop_dir / "VoceVibe4.command"
    
    # Content of the launcher script
    # We use a robust approach that activates the venv and runs main.py
    script_content = f"""#!/bin/bash
# VoceVibe4 Launcher

# Navigate to project directory
cd "{project_dir}"

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "❌ Virtual environment not found in {project_dir}"
    echo "Please run 'python3 -m venv .venv' and install requirements."
    read -p "Press Enter to exit..."
    exit 1
fi

# Run the application
echo "🚀 Starting VoceVibe4..."
python main.py

# Keep terminal open if it crashes
if [ $? -ne 0 ]; then
    echo "❌ Application crashed with error code $?"
    read -p "Press Enter to exit..."
fi
"""

    try:
        # Write the launcher file
        with open(launcher_path, "w") as f:
            f.write(script_content)
        
        # Make it executable
        st = os.stat(launcher_path)
        os.chmod(launcher_path, st.st_mode | stat.S_IEXEC)
        
        print(f"✅ Launcher created successfully at: {launcher_path}")
        print("👉 You can now double-click 'VoceVibe4.command' on your Desktop to start the app.")
        
    except Exception as e:
        print(f"❌ Failed to create launcher: {e}")

if __name__ == "__main__":
    create_launcher()
