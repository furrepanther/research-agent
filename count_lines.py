import os

def count_productive_lines(filepath):
    """Count non-comment, non-blank lines in a Python file"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        productive = 0
        in_docstring = False
        
        for line in lines:
            stripped = line.strip()
            
            # Toggle docstring state
            if '"""' in stripped or "'''" in stripped:
                in_docstring = not in_docstring
                continue
            
            # Skip if in docstring, blank, or comment
            if in_docstring or not stripped or stripped.startswith('#'):
                continue
            
            productive += 1
        
        return productive
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return 0

# Count src/ directory
src_total = 0
src_files = 0
for root, dirs, files in os.walk('src'):
    for filename in files:
        if filename.endswith('.py'):
            filepath = os.path.join(root, filename)
            lines = count_productive_lines(filepath)
            src_total += lines
            src_files += 1

# Count root files
root_files = ['gui.py', 'main.py']
root_total = 0
root_count = 0
for filename in root_files:
    if os.path.exists(filename):
        lines = count_productive_lines(filename)
        root_total += lines
        root_count += 1
        print(f"{filename}: {lines} productive lines")

print(f"\n=== SUMMARY ===")
print(f"src/ directory: {src_files} files, {src_total} productive lines")
print(f"Root level: {root_count} files, {root_total} productive lines")
print(f"\nTOTAL: {src_files + root_count} files, {src_total + root_total} productive lines")
