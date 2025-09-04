#!/usr/bin/env python3

import os
import re
import shutil
import sys
import time


DRY_RUN = False           
MESH_EXTS = {'.stl', '.dae', '.obj', '.ply', '.fbx'}


def add_prefix_to_link_names(text: str, prefix: str) -> str:
    # <link name="NAME">
    pattern_link = re.compile(r'(<\s*link\s+[^>]*name=")([^"]+)(")', re.IGNORECASE)
    def repl_link(m):
        name = m.group(2)
        if name.startswith(prefix + '_'):
            return m.group(1) + name + m.group(3)
        return m.group(1) + prefix + '_' + name + m.group(3)
    text = pattern_link.sub(repl_link, text)

    # <parent link="NAME"/>
    pattern_parent = re.compile(r'(<\s*parent\s+[^>]*link=")([^"]+)(")', re.IGNORECASE)
    def repl_parent(m):
        name = m.group(2)
        if name.startswith(prefix + '_'):
            return m.group(1) + name + m.group(3)
        return m.group(1) + prefix + '_' + name + m.group(3)
    text = pattern_parent.sub(repl_parent, text)

    # <child link="NAME"/>
    pattern_child = re.compile(r'(<\s*child\s+[^>]*link=")([^"]+)(")', re.IGNORECASE)
    def repl_child(m):
        name = m.group(2)
        if name.startswith(prefix + '_'):
            return m.group(1) + name + m.group(3)
        return m.group(1) + prefix + '_' + name + m.group(3)
    text = pattern_child.sub(repl_child, text)

    return text


def process_folder(parts_dir: str, folder_name: str):
    folder_path = os.path.join(parts_dir, folder_name)
    if not os.path.isdir(folder_path):
        return

    urdf_dir = os.path.join(folder_path, 'urdf')
    xacro_file = os.path.join(urdf_dir, f"{folder_name}.xacro")
    meshes_dir = os.path.join(folder_path, 'meshes')
    export_dir = os.path.join(folder_path, folder_name)  # new folder to create/copy into

    if not os.path.exists(xacro_file):
        print(f"[SKIP] xacro not found: {xacro_file}")
        return

    mesh_map = {}  # old_name -> new_name
    if os.path.isdir(meshes_dir):
        for fname in sorted(os.listdir(meshes_dir)):
            fpath = os.path.join(meshes_dir, fname)
            if not os.path.isfile(fpath):
                continue
            base, ext = os.path.splitext(fname)
            if ext.lower() not in MESH_EXTS:
                continue

            # if file already starts with prefix_, don't rename
            if fname.startswith(folder_name + '_'):
                mesh_map[fname] = fname
                continue

            newname = f"{folder_name}_{fname}"
            newpath = os.path.join(meshes_dir, newname)

            # avoid collisions
            if os.path.exists(newpath):
                i = 1
                base_only, ext_only = os.path.splitext(newname)
                candidate = f"{base_only}_{i}{ext_only}"
                while os.path.exists(os.path.join(meshes_dir, candidate)):
                    i += 1
                    candidate = f"{base_only}_{i}{ext_only}"
                newname = candidate
                newpath = os.path.join(meshes_dir, newname)

            try:
                if DRY_RUN:
                    print(f"[DRY-RUN] would rename {fpath} -> {newpath}")
                else:
                    os.rename(fpath, newpath)
                    print(f"[RENAME] {os.path.join(folder_name,'meshes',fname)} -> {os.path.join(folder_name,'meshes',newname)}")
                mesh_map[fname] = newname
            except Exception as e:
                print(f"[ERROR] renaming {fpath} -> {newpath}: {e}")
    else:
        print(f"[NOTICE] no meshes/ folder in {folder_name}")

    try:
        with open(xacro_file, 'r', encoding='utf-8') as f:
            original = f.read()
    except Exception as e:
        print(f"[ERROR] reading xacro {xacro_file}: {e}")
        return

    updated_xacro = original
    urdf_content = original

    # replace package://folder_name/meshes/ -> meshes/
    urdf_content = re.sub(rf'package://{re.escape(folder_name)}/meshes/', 'meshes/', urdf_content)
    updated_xacro = re.sub(rf'package://{re.escape(folder_name)}/meshes/', 'meshes/', updated_xacro)

    # Apply per-file mesh renames (meshes/old -> meshes/new)
    for old, new in mesh_map.items():
        urdf_content = urdf_content.replace(f'meshes/{old}', f'meshes/{new}')
        updated_xacro = updated_xacro.replace(f'meshes/{old}', f'meshes/{new}')

    # Prefix link names in both files
    urdf_content = add_prefix_to_link_names(urdf_content, folder_name)
    updated_xacro = add_prefix_to_link_names(updated_xacro, folder_name)

    # For URDF: remove xmlns:xacro attribute from <robot ...>
    urdf_content = re.sub(r'\s+xmlns:xacro="http://www\.ros\.org/wiki/xacro"', '', urdf_content)

    # For URDF: remove all <xacro:include .../> lines
    urdf_content = re.sub(r'<xacro:include[^>]*?/\s*>\s*', '', urdf_content)

    # Write updated xacro back (overwrites original xacro) -- optional behavior kept
    try:
        if DRY_RUN:
            print(f"[DRY-RUN] would write updated xacro: {xacro_file}")
        else:
            with open(xacro_file, 'w', encoding='utf-8') as f:
                f.write(updated_xacro)
            print(f"[UPDATE] wrote updated xacro: {xacro_file}")
    except Exception as e:
        print(f"[ERROR] writing updated xacro {xacro_file}: {e}")

    # Create export folder and copy meshes + write urdf there
    urdf_out_path = os.path.join(export_dir, f"{folder_name}.urdf")
    if DRY_RUN:
        print(f"[DRY-RUN] would create export folder: {export_dir}")
    else:
        # if export_dir exists, remove it so we start clean (only affects previous export)
        if os.path.exists(export_dir):
            try:
                shutil.rmtree(export_dir)
                print(f"[REMOVE] existing export folder removed: {export_dir}")
            except Exception as e:
                print(f"[WARN] could not remove existing export folder {export_dir}: {e}")
        os.makedirs(export_dir, exist_ok=True)
        print(f"[MKDIR] created export folder: {export_dir}")

    # copy meshes folder (if any)
    if os.path.isdir(meshes_dir):
        dest_meshes = os.path.join(export_dir, 'meshes')
        if DRY_RUN:
            print(f"[DRY-RUN] would copy meshes {meshes_dir} -> {dest_meshes}")
        else:
            try:
                shutil.copytree(meshes_dir, dest_meshes)
                print(f"[COPY] meshes copied to export folder: {dest_meshes}")
            except Exception as e:
                print(f"[ERROR] copying meshes to export folder: {e}")

    # write the urdf into export folder
    try:
        if DRY_RUN:
            print(f"[DRY-RUN] would write urdf: {urdf_out_path}")
        else:
            with open(urdf_out_path, 'w', encoding='utf-8') as f:
                f.write(urdf_content)
            print(f"[WRITE] created urdf in export folder: {urdf_out_path}")
    except Exception as e:
        print(f"[ERROR] writing urdf {urdf_out_path}: {e}")


if __name__ == '__main__':
    # script should be placed in the parts/ folder and executed from there
    parts_dir = os.path.abspath(os.path.dirname(__file__))
    print(f"Running in parts directory: {parts_dir}")

    for entry in sorted(os.listdir(parts_dir)):
        # skip this script file and any non-directory
        if entry == os.path.basename(__file__):
            continue
        entry_path = os.path.join(parts_dir, entry)
        if not os.path.isdir(entry_path):
            continue
        # skip common hidden or python cache folders
        if entry.startswith('.') or entry == '__pycache__':
            continue
        try:
            process_folder(parts_dir, entry)
        except Exception as e:
            print(f"[ERROR] processing {entry}: {e}")

    print("\nDone.")
