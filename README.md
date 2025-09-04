# URDF Generator from Fusion 360 Xacro Files

This Python script (`urdf.py`) converts Xacro files from Fusion 360 (via [fusion2urdf](https://github.com/syuntoku14/fusion2urdf)) into standalone URDF files. It renames links and meshes with a prefix, organizes outputs, and supports ROS2/Gazebo simulations.

## Features
- Converts Xacro to URDF, removing Xacro tags.
- Adds prefix to link/mesh names (e.g., `robot_link1` → `myrobot_link1`).
- Manages meshes (`.stl`, `.dae`, `.obj`) and copies to export folder.
- Dry-run mode for safe testing.

## Prerequisites
- Python 3.x
- [fusion2urdf](https://github.com/syuntoku14/fusion2urdf) for Xacro generation

## Installation
```
git clone https://github.com/yourusername/xacro2urdf.git
cd xacro2urdf
```
## Usage
1. Place the script `urdf.py` inside your `parts/` folder  
2. Open a terminal or command prompt in the `parts/` folder  
3. Run:
```
python urdf.py
```
4. The updated URDF and meshes will be generated inside each robot's export folder

## Notes
- The script modifies `.xacro` files in-place, but creates a `.xacro.bak` backup before changes  
- Output URDF removes `xmlns:xacro` attributes and `<xacro:include>` lines for compatibility  
- If you want to test without changing files, set `DRY_RUN = True` at the top of the script

## License
This repository is provided under the MIT License.
