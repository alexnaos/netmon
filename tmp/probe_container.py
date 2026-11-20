import socket

try:
    s = socket.create_connection(('127.0.0.1', 1883), 3)
    print('CONTAINER_CONN_OK')
    s.close()
except Exception as e:
    print('CONTAINER_ERR', repr(e))
