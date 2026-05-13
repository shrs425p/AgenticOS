import os

# Placeholder link to be replaced
OLD_LINK = "https://github.com/your-repo/AgenticOs.git"
# User's actual repository link
NEW_LINK = "https://github.com/shrs425p/AgenticOS.git"

def update_links(text):
    return text.replace(OLD_LINK, NEW_LINK)

def process_directory(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".md"):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    new_content = update_links(content)
                    
                    if new_content != content:
                        with open(path, "w", encoding="utf-8") as f:
                            f.write(new_content)
                        print(f"Updated link in: {path}")
                except Exception as e:
                    print(f"Error processing {path}: {e}")

if __name__ == "__main__":
    process_directory("c:\\AgenticOs\\docs")
    process_directory("c:\\AgenticOs")
