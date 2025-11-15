import os
import sys
# Ensure headless backend as a safeguard
os.environ.setdefault('MPLBACKEND', 'Agg')

from api import lichess


class Req:
    def __init__(self, user):
        # emulate request.query.get("user")
        self.query = {'user': user}


def save_bytes_to_file(b, path):
    with open(path, 'wb') as f:
        f.write(b)


if __name__ == '__main__':
    # Priority: command-line arg > TEST_USER env var > default
    import os
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='Run the local invocation of api/lichess')
    parser.add_argument('user', nargs='?', help='Lichess username to fetch', default=None)
    parser.add_argument('--save', action='store_true', help='Save output image to tests/output.png')
    args = parser.parse_args()

    if args.user:
        user = args.user
    else:
        user = os.environ.get('TEST_USER', 'introduzir username aqui') # substitua 'introduzir username aqui' pelo username desejado

    req = Req(user)
    try:
        res = lichess.main(req)
        print('Result type:', type(res))

        body = None
        status = None
        headers = None

        if isinstance(res, tuple):
            # Common forms: (bytes, status, headers) or (body, status)
            if len(res) >= 1:
                body = res[0]
            if len(res) >= 2:
                status = res[1]
            if len(res) >= 3:
                headers = res[2]
        else:
            body = res

        print('Status:', status)
        if headers:
            print('Headers:', headers)

        # If body is bytes, optionally save
        if isinstance(body, (bytes, bytearray)):
            print('Received bytes output (image).')
            if args.save or os.environ.get('SAVE_OUTPUT') == '1':
                out_path = os.path.join(os.path.dirname(__file__), 'output1.png')
                save_bytes_to_file(body, out_path)
                print('Saved image to', out_path)
            else:
                print('To save the image locally, run with `--save` or set `SAVE_OUTPUT=1`')
        else:
            print('Body:', body)
    except Exception as e:
        print('Unhandled exception:', e)
        raise
