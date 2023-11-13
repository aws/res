import os


def main():
    words_to_suppress = ["blacklist",
                         "whitelist",
                         "slave",
                         "master",
                         "blackday",
                         "greyday",
                         "whiteday"]

    for root, dirs, files in os.walk("../"):
        for file in files:
            if ["node_modules", "venv-py-installer"] not in root:
                if file not in ["inclusive_scanner.py",
                                "THIRD_PARTY_LICENSES.txt",
                                "socawebui.sh",
                                "ComputeNode.sh"]:
                    if file.endswith(".md") \
                            or file.endswith(".py") \
                            or file.endswith(".template") \
                            or file.endswith(".html") \
                            or file.endswith(".txt") \
                            or file.endswith(".doc") \
                            or file.endswith(".log") \
                            or file.endswith(".sh"):
                        file_path = os.path.join(root, file)
                        f = open(file_path).read()
                        for word in words_to_suppress:
                            if word in f:
                                print(f"Found {word} in {file_path}")
                            if word.upper() in f:
                                print(f"Found {word} in {file_path}")


if __name__ == '__main__':
    main()