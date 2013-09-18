import logging
import argparse
from heka.config import client_from_stream_config

log = logging.getLogger("HekaLogger")
log.setLevel(logging.DEBUG)
console = logging.StreamHandler()
log.addHandler(console)

parser = argparse.ArgumentParser(description="Load a sample heka configuration")
parser.add_argument('--config',
        type=argparse.FileType('r'),
        required=True)
parsed_args = parser.parse_args()

client = client_from_stream_config(parsed_args.config, 'heka')
client.incr('foo')

if hasattr(client.stream, 'msgs'):
    print client.stream.msgs
