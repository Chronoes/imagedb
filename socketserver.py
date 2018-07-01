import socket
import subprocess
import json

def main():
    server = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    server.bind(('localhost', 8080))
    server.listen(1)
    print('Listening on localhost:8080 (1 connection)')

    while True:
        client, address = server.accept()
        print('Client connected:', ':'.join(map(str, address)))
        while True:
            data = json.loads(client.recv(2048).decode())
            print(data)

            if data.get('close', False):
                client.close()
                print('Client disconnected:', ':'.join(map(str, address)))
                break

            command = data.get('command')

            if command:
                print(command)
                try:
                    proc = subprocess.Popen(command, shell=True)
                    (out, err) = proc.communicate()
                    client.send(bytes(json.dumps({
                        'success': True,
                        'output': out
                    }), encoding='utf-8'))
                except FileNotFoundError:
                    client.send(bytes(json.dumps({
                        'success': False,
                        'error': 'Invalid command to execute: ' + command
                    }), encoding='utf-8'))
                    continue


if __name__ == '__main__':
    main()
