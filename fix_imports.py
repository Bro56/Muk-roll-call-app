import os

for root, dirs, files in os.walk("."):
    for file in files:
        if file.endswith(".py"):
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            
            original = content
            content = content.replace("from app_utils.", "from app_utils.")
            content = content.replace("import app_utils.", "import app_utils.")
            
            if content != original:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"Fixed: {path}")