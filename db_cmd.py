"""
"""
import sys
import os.path
import shutil
import cmd
import pathlib
import subprocess
import socket
import json

from utilities import term_str
from database.database import *
from database.db_queries import *

__author__ = 'Chronoes'

class DatabaseCmd(cmd.Cmd):
    intro = 'Image DB query interface'
    prompt = '(DB) $ '
    precmd_prompt = '-> '

    last_results = {}

    sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)

    def _connect_socket(self):
        try:
            self.sock.connect(('localhost', 8080))
        except ConnectionRefusedError:
            print('Socket server is not listening, retry after starting')
            return False
        except OSError as e:
            if e.errno == 106:
                return True
        return True

    def _close_socket(self):
        try:
            self.sock.send(bytes(json.dumps({
                'close': True
            }), 'utf-8'))
        except:
            pass
        finally:
            self.sock.close()


    def _run_socket(self, command):
        if self._connect_socket():
            self.sock.send(bytes(json.dumps({
                'command': command
            }), 'utf-8'))

            data = json.loads(self.sock.recv(2048).decode())
            if not data['success']:
                print(data['error'])
            return data['success']

        return False

    def precmd(self, line):
        if line.lstrip('\\') not in ('q', 'quit'):
            print(self.precmd_prompt, end='')
        else:
            line = 'quit'
        return line

    def postloop(self):
        self._close_socket()

    def do_count(self, arg):
        """Count all objects in database, default images: \\count [images|tags]"""
        if arg == 'tags':
            print(Tag.select().count(), 'tags recorded in database')
        else:
            print(Image.select().count(), 'images recorded in database')

    def do_drop(self, arg):
        """Drop all tables in database: \\drop"""
        if input('Confirm dropping tables Y/N: ').lower() == 'y':
            db.drop_tables(db.models)
            print('All tables dropped')

    def do_query(self, arg):
        """Query for images with given tags: \\query tag1 tag2 tag3..."""
        terminal_width = shutil.get_terminal_size()[0]
        results = query_results(arg.split())

        print()
        for img in results:
            self.last_results[img.id] = img

            img_id = term_str('> {:^8} <').format(img.id).bold()
            print('{:{fill}^{width}}'.format(img_id, fill='-', width=terminal_width + img_id.len_special()))
            print(img.group.name.capitalize(), pathlib.PureWindowsPath(img.group.path, img.filename))
            print(*get_image_tags(img))

        arrow_length = int(terminal_width * 0.2)
        print('{}{:{fill}^{width}}{}'.format(
            '<' * arrow_length, 'END', '>' * arrow_length, fill='-', width=terminal_width - 2 * arrow_length))

    def do_del(self, arg):
        """Delete image(s) by ID from DB and if possible, from filesystem: \\del 3 15"""
        ids = arg.split()
        deleted = []
        for img in query_by_id(ids):
            if self._run_socket('del {}'.format(str(pathlib.PureWindowsPath(img.group.path, img.filename)))):
                img.delete_instance(recursive=True, delete_nullable=True)
                deleted.append(img.id)

        print('Images', *deleted, end=' ')
        print('deleted')

    def do_open(self, arg):
        """Open image by ID with default image viewer: \\open 213 | \\open url 213
        Sends Windowsified path to socket on Windows to open image"""
        action = ''
        if not arg.isdigit():
            arg = arg.split()
            if len(arg) > 2:
                print('Expected 2 parameters, got ' + str(len(arg)))
                return False
            action, arg = arg


        img = self.last_results.get(int(arg))
        if not img:
            img = query_by_id([arg])
            if not img:
                print('Image with ID {} does not exist.'.format(arg))
                return False
            img = img.pop()

        if action.endswith('url'):
            path = img.original_link
        else:
            path = pathlib.PureWindowsPath(img.group.path, img.filename)

        if self._run_socket('start "" "{}"'.format(path)):
            print('Opening...', path)


    def do_quit(self, arg):
        """Exit the interpreter: \\q[uit]"""
        return True

    def default(self, line):
        self.do_query(line)

    def help_default(self):
        print('When command is not recognized, interpreter runs \'query <input>\' instead')

    def do_group(self, line):
        """Changes group of given image ID. \\group <image_id> <new_group>"""
        command = line.split(maxsplit=1)
        image_id = int(command[0])
        image = query_by_id([image_id]).pop()
        if not image:
            print('No such image with ID', command[0])
            return False

        new_group = find_group(command[1])

        if not new_group:
            print('No such group', command[1])
            return False

        if self._run_socket('move {} {}'.format(str(pathlib.PureWindowsPath(image.group.path, image.filename)), new_group.path)):
            Image.update(group=new_group).where(Image.id == image.id).execute()
            print('Changed group from', image.group.name, 'to', str(new_group.name))


if __name__ == '__main__':
    DatabaseCmd().cmdloop()
