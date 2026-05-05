import os

def print_tree(startpath, exclude_dirs={'.git', '__pycache__', 'venv', 'env', 'node_modules', '.idea'}):
    for root, dirs, files in os.walk(startpath):
        # Mutate the list in place to avoid walking into excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * level
        print(f'{indent}{os.path.basename(root)}/')
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            if not f.endswith(('.pyc', '.pyo', '.pyd')):
                print(f'{subindent}{f}')

print_tree('.')