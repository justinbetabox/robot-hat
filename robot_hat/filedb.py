#!/usr/bin/env python3
"""
A simple file-based key-value store for Robot Hat configuration.
"""
import os
from time import sleep
from typing import Optional
import pwd
import grp


class fileDB:
    """
    A simple file based database.

    This database reads and writes configuration arguments in a specific file.
    """

    def __init__(self, db: str, mode: Optional[str] = None, owner: Optional[str] = None) -> None:
        """
        Initialize the file database.

        :param db: The file path used to store the data.
        :param mode: The file permission mode as a string (e.g. '774').
        :param owner: The owner (user) for the file.
        :raises ValueError: If no file path is provided.
        """
        self.db: str = db
        if not self.db:
            raise ValueError('db: Missing file path parameter.')
        self.file_check_create(db, mode, owner)

    def file_check_create(self, file_path: str, mode: Optional[str] = None, owner: Optional[str] = None) -> None:
        """
        Check if the file exists, and create it (and its directory) if not.

        :param file_path: The file path to check.
        :param mode: The file mode to apply (e.g. '774').
        :param owner: The owner to assign to the file.
        """
        directory = os.path.dirname(file_path)
        try:
            if os.path.exists(file_path):
                if not os.path.isfile(file_path):
                    print('Could not create file; a folder with the same name exists.')
                    return
            else:
                if os.path.exists(directory):
                    if not os.path.isdir(directory):
                        print('Could not create directory; a file with the same name exists.')
                        return
                else:
                    os.makedirs(directory, mode=0o754)
                    sleep(0.001)
                with open(file_path, 'w') as f:
                    f.write("# robot-hat config and calibration values\n\n")

            # Apply mode if provided
            if mode is not None:
                try:
                    perms = int(mode, 8)
                    os.chmod(file_path, perms)
                except ValueError:
                    print(f"Invalid mode '{mode}'; skipping chmod.")
            # Apply owner if provided
            if owner is not None:
                try:
                    pw = pwd.getpwnam(owner)
                    gr = grp.getgrnam(owner)
                    uid, gid = pw.pw_uid, gr.gr_gid
                    os.chown(file_path, uid, gid)
                    os.chown(directory, uid, gid)
                except KeyError:
                    print(f"User/group '{owner}' not found; skipping chown.")
        except Exception as e:
            raise e

    def get(self, name: str, default_value: Optional[str] = None) -> Optional[str]:
        """
        Retrieve the value of a configuration argument by name.

        :param name: The name of the argument.
        :param default_value: The default value to return if not found.
        :return: The value as a string, or default_value if not found.
        """
        try:
            with open(self.db, 'r') as conf:
                lines = conf.readlines()
            for line in lines:
                if line.strip().startswith('#') or '=' not in line:
                    continue
                key, val = line.split('=', 1)
                if key.strip() == name:
                    return val.strip()
            return default_value
        except FileNotFoundError:
            # Ensure file exists for next time
            with open(self.db, 'w'):
                pass
            return default_value
        except Exception:
            return default_value

    def set(self, name: str, value: str) -> None:
        """
        Set or update the value of a configuration argument.

        If the argument does not exist, it is appended to the file.

        :param name: The name of the argument.
        :param value: The value to set.
        """
        try:
            with open(self.db, 'r') as conf:
                lines = conf.readlines()
        except FileNotFoundError:
            lines = []

        updated = False
        new_lines: list[str] = []
        for line in lines:
            if line.strip().startswith('#') or '=' not in line:
                new_lines.append(line)
                continue
            key, _ = line.split('=', 1)
            if key.strip() == name:
                new_lines.append(f'{name} = {value}\n')
                updated = True
            else:
                new_lines.append(line)

        if not updated:
            new_lines.append(f'{name} = {value}\n')

        with open(self.db, 'w') as conf:
            conf.writelines(new_lines)


if __name__ == '__main__':
    db = fileDB('/opt/robot-hat/test2.config')
    db.set('a', '1')
    db.set('b', '2')
    print(db.get('a'))
    print(db.get('c'))
