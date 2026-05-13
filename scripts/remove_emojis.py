import os
import re

def remove_emojis(text):
    # This regex matches a wide range of Unicode emojis
    return re.sub(r'[\U00010000-\U0010ffff]', '', text)

def process_directory(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".md") or file.endswith(".yml"):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    new_content = remove_emojis(content)
                    
                    if new_content != content:
                        with open(path, "w", encoding="utf-8") as f:
                            f.write(new_content)
                        print(f"Removed emojis from: {path}")
                except Exception as e:
                    print(f"Error processing {path}: {e}")

if __name__ == "__main__":
    process_directory("c:\\AgenticOs")
