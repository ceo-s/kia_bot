import os
import json


def create_db_path():
    with open("conf.json", "r") as file:
        conf = json.load(file)

    paths = []
    paths.append(conf["DB"]["BASE_DIR"])
    paths.append(conf["LLM"]["DB"]["TEXTS_DIR"])
    paths.append(conf["LLM"]["DB"]["EMBEDDINGS_DIR"])
    paths.append(conf["DB"]["RELATIONAL"]["DATABASE_DIR"])

    for path in paths:
        if not os.path.exists(path):
            os.mkdir(path)
            print(f"Succesfully created \"{path}\"")
        else:
            print(f"Path \"{path}\" already exists!")


def setup():
    create_db_path()


if __name__ == '__main__':
    setup()
