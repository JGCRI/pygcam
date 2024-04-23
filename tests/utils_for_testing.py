from io import StringIO
from pygcam.config import readConfigFile

def load_config_from_string(text):
    stream = StringIO(text)
    readConfigFile(stream)

