import os

output_dir = r"D:\vibeStock\vibeStock\vibeStock\数据接口参考文档\AKShare_Split"

if not os.path.exists(output_dir):
    print("Directory not found.")
else:
    files = sorted(os.listdir(output_dir))
    for f in files[:10]:
        path = os.path.join(output_dir, f)
        try:
            with open(path, 'r', encoding='utf-8') as file:
                first_line = file.readline().strip()
                print(f"File: {f}")
                print(f"First line: {first_line}")
        except Exception as e:
            print(f"Error reading {f}: {e}")
