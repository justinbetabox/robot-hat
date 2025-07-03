#!/usr/bin/env python3
import os
from time import sleep
from typing import Dict, Optional

class Config:
    """
    A file-based configuration database.

    This class manages configuration data stored in a text file using an INI-style format.
    It supports sections (e.g. [section]) and key-value pairs.
    """

    def __init__(self, path: str, mode: Optional[str] = None, owner: Optional[str] = None, description: Optional[str] = None) -> None:
        """
        Initialize the Config object.

        :param path: The file path for the configuration file.
        :param mode: The file permission mode as a string (e.g., "775").
        :param owner: The owner (user) for the file.
        :param description: Optional description to be written as header comments.
        :raises ValueError: If no path is provided.
        """
        self.path: str = path
        if self.path is not None:
            self.file_check_create(self.path, mode, owner, description)
        else:
            raise ValueError("Config: Missing file path parameter.")
        self._dict: Dict[str, Dict[str, str]] = {}
        self.read()

    def __getitem__(self, key: str) -> Dict[str, str]:
        return self._dict[key]
    
    def __setitem__(self, key: str, value: Dict[str, str]) -> None:
        self._dict[key] = value

    def file_check_create(self, path: str, mode: Optional[str] = None, owner: Optional[str] = None, description: Optional[str] = None) -> None:
        """
        Ensure the configuration file and its directory exist. If not, create them.

        :param path: The file path to check or create.
        :param mode: The file permission mode as a string (e.g., "775").
        :param owner: The owner to assign to the file.
        :param description: Optional header text to write as comments.
        """
        directory = path.rsplit('/', 1)[0]
        try:
            if os.path.exists(path):
                if not os.path.isfile(path):
                    print("Could not create file; a folder with the same name exists.")
                    return
            else:
                if os.path.exists(directory):
                    if not os.path.isdir(directory):
                        print("Could not create file; a file with the same name exists.")
                        return
                else:
                    os.makedirs(directory, mode=0o754)
                    sleep(0.001)
                with open(path, 'w') as f:
                    if description is not None:
                        # Write the description as commented lines.
                        lines = description.strip().split('\n')
                        header = "\n".join(f"# {line}" for line in lines) + "\n\n"
                        f.write(header)
                    else:
                        f.write("")
                if mode is not None:
                    os.system(f"sudo chmod {mode} {path}")
                if owner is not None:
                    os.system(f"sudo chown -R {owner}:{owner} {directory}")
        except Exception as e:
            raise e

    @staticmethod
    def _read(path: str) -> Dict[str, Dict[str, str]]:
        """
        Read the configuration file and return its content as a nested dictionary.

        :param path: The file path to read.
        :return: A dictionary with sections as keys and key-value pairs as inner dictionaries.
        """
        config_dict: Dict[str, Dict[str, str]] = {}
        current_section = ""
        config_dict[current_section] = {}
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith('#'):
                    continue
                elif line.startswith('[') and line.endswith(']'):
                    current_section = line[1:-1].strip()
                    config_dict[current_section] = {}
                elif '=' in line:
                    option, value = line.split('=', 1)
                    config_dict[current_section][option.strip()] = value.strip()
        return config_dict

    @staticmethod
    def _write(path: str, config_dict: Dict[str, Dict[str, str]]) -> None:
        """
        Write the configuration dictionary to the file, preserving sections and comments.

        :param path: The file path to write to.
        :param config_dict: The configuration dictionary.
        """
        # Read current file to preserve comments and order.
        parts: Dict[str, list] = {}
        updated = config_dict.copy()
        sections = list(updated.keys())

        with open(path, 'r') as f:
            lines = f.readlines()
            current_section = ""
            parts[current_section] = []
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    parts[current_section].append("\n")
                elif stripped.startswith('#'):
                    parts[current_section].append(line)
                elif stripped.startswith('[') and stripped.endswith(']'):
                    if current_section in sections:
                        for opt, val in updated[current_section].items():
                            parts[current_section].append(f"{opt} = {val}\n")
                        updated.pop(current_section)
                    current_section = stripped[1:-1].strip()
                    parts[current_section] = [line]
                elif '=' in stripped:
                    option, _ = stripped.split('=', 1)
                    option = option.strip()
                    if current_section in sections and option in updated[current_section]:
                        new_val = updated[current_section].pop(option)
                        parts[current_section].append(f"{option} = {new_val}\n")
                    else:
                        parts[current_section].append(line)
                else:
                    parts[current_section].append(line)
            if current_section in sections:
                for opt, val in updated[current_section].items():
                    parts[current_section].append(f"{opt} = {val}\n")
                updated.pop(current_section)
            for sec in list(updated.keys()):
                parts[sec] = [f"[{sec}]\n"]
                for opt, val in updated[sec].items():
                    parts[sec].append(f"{opt} = {val}\n")
                parts[sec].append("\n")
                updated.pop(sec)
        with open(path, 'w') as f:
            for sec in parts:
                for line in parts[sec]:
                    f.write(line)

    def read(self) -> Dict[str, Dict[str, str]]:
        """
        Read the configuration file and update the internal dictionary.

        :return: The configuration dictionary.
        """
        self._dict = self._read(self.path)
        return self._dict

    def write(self) -> None:
        """
        Write the internal configuration dictionary to the file.
        """
        self._write(self.path, self._dict)

    def get(self, section: str, option: str, default: Optional[str] = None) -> str:
        """
        Get a configuration option value. If missing, sets it to the default.

        :param section: The section name.
        :param option: The option name.
        :param default: The default value if the option does not exist.
        :return: The configuration value as a string.
        """
        if section not in self._dict:
            self._dict[section] = {option: str(default)}
        elif option not in self._dict[section]:
            self._dict[section][option] = str(default)
        return self._dict[section][option]

    def set(self, section: str, option: str, value: str) -> None:
        """
        Set a configuration option value.

        :param section: The section name.
        :param option: The option name.
        :param value: The value to set.
        """
        if section not in self._dict:
            self._dict[section] = {}
        self._dict[section][option] = value


if __name__ == '__main__':
    description = '''
    robot-hat config test
    hello
    world
    '''
    config = Config(path='/opt/robot-hat/test.config',
                    mode='775',
                    owner='xo',
                    description=description)

    print("Initial config:")
    print(config.read())

    config['section1'] = {}
    config['section1']['option1'] = '1234'
    config['section2'] = {'option1': '100'}
    print("After adding section1 and section2:")
    print(config.read())
 
    config.write()

    print("section2, option1:", config.get('section2', 'option1'))
    print("section3, option1 (default):", config.get('section3', 'option1', default='hello'))

    config.set('section4', 'option1', 'hi')
    config.write()