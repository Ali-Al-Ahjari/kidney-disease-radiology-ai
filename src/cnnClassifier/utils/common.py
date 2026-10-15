import os
import yaml
from cnnClassifier import logger
import json
import joblib
from pathlib import Path
from typing import Any, Union, Optional
import base64
import io

try:
    from box.exceptions import BoxValueError
except ImportError:
    class BoxValueError(ValueError):
        pass

try:
    from box import ConfigBox
except ImportError:
    class ConfigBox(dict):
        def __getattr__(self, item):
            try:
                val = self[item]
                if isinstance(val, dict):
                    return ConfigBox(val)
                return val
            except KeyError:
                raise AttributeError(f"'ConfigBox' object has no attribute '{item}'")

try:
    from ensure import ensure_annotations
except ImportError:
    def ensure_annotations(func):
        return func



@ensure_annotations
def read_yaml(path_to_yaml: Path) -> ConfigBox:
    """reads yaml file and returns

    Args:
        path_to_yaml (Path): path like input

    Raises:
        ValueError: if yaml file is empty
        e: empty file

    Returns:
        ConfigBox: ConfigBox type
    """
    try:
        with open(path_to_yaml) as yaml_file:
            content = yaml.safe_load(yaml_file)
            if not content:
                raise ValueError("yaml file is empty")
            logger.info(f"yaml file: {path_to_yaml} loaded successfully")
            return ConfigBox(content)
    except BoxValueError:
        raise ValueError("yaml file is empty")
    except Exception as e:
        raise e
    


@ensure_annotations
def create_directories(path_to_directories: list, verbose=True):
    """create list of directories

    Args:
        path_to_directories (list): list of path of directories
        ignore_log (bool, optional): ignore if multiple dirs is to be created. Defaults to False.
    """
    for path in path_to_directories:
        os.makedirs(path, exist_ok=True)
        if verbose:
            logger.info(f"created directory at: {path}")


@ensure_annotations
def save_json(path: Path, data: dict):
    """save json data

    Args:
        path (Path): path to json file
        data (dict): data to be saved in json file
    """
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

    logger.info(f"json file saved at: {path}")




@ensure_annotations
def load_json(path: Path) -> ConfigBox:
    """load json files data

    Args:
        path (Path): path to json file

    Returns:
        ConfigBox: data as class attributes instead of dict
    """
    with open(path) as f:
        content = json.load(f)

    logger.info(f"json file loaded succesfully from: {path}")
    return ConfigBox(content)


@ensure_annotations
def save_bin(data: Any, path: Path):
    """save binary file

    Args:
        data (Any): data to be saved as binary
        path (Path): path to binary file
    """
    joblib.dump(value=data, filename=path)
    logger.info(f"binary file saved at: {path}")


@ensure_annotations
def load_bin(path: Path) -> Any:
    """load binary data

    Args:
        path (Path): path to binary file

    Returns:
        Any: object stored in the file
    """
    data = joblib.load(path)
    logger.info(f"binary file loaded from: {path}")
    return data

@ensure_annotations
def get_size(path: Path) -> str:
    """get size in KB

    Args:
        path (Path): path of the file

    Returns:
        str: size in KB
    """
    size_in_kb = round(os.path.getsize(path)/1024)
    return f"~ {size_in_kb} KB"


def decodeImage(imgstring, fileName):
    """Legacy helper: decodes base64 string and writes to file."""
    imgdata = decode_image_bytes(imgstring)
    with open(fileName, 'wb') as f:
        f.write(imgdata)


def decode_image_bytes(imgstring: str) -> bytes:
    """Decodes a base64 encoded image string to raw bytes in memory.
    Handles data URI prefixes (e.g., 'data:image/jpeg;base64,...').
    """
    if "," in imgstring:
        imgstring = imgstring.split(",", 1)[1]
    # Remove whitespace or newlines if any
    imgstring = imgstring.strip().replace("\n", "").replace("\r", "")
    return base64.b64decode(imgstring)


def encodeImageIntoBase64(croppedImagePath):
    with open(croppedImagePath, "rb") as f:
        return base64.b64encode(f.read())


def bytes_to_base64(data: bytes) -> str:
    """Encodes raw bytes to base64 string."""
    return base64.b64encode(data).decode('utf-8')



