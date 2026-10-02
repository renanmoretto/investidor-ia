import os
import threading
import webbrowser

import uvicorn

HOST = os.getenv('HOST', '127.0.0.1')
PORT = int(os.getenv('PORT', '8000'))


def main():
    url = f'http://{HOST}:{PORT}'
    print(f'Investidor-IA rodando em {url}')
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    uvicorn.run('web.main:app', host=HOST, port=PORT)


if __name__ == '__main__':
    main()
