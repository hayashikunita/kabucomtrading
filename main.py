import logging
import sys
from threading import Thread

from app.controllers.streamdata import stream
from app.controllers.webserver import start

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

if __name__ == "__main__":
    # kabusapi縺ｮ繧ｹ繝医Μ繝ｼ繝繝・・繧ｿ蜿門ｾ励・Web繧ｵ繝ｼ繝占ｵｷ蜍・
    streamThread = Thread(target=stream.stream_ingestion_data)
    serverThread = Thread(target=start)

    streamThread.start()
    serverThread.start()

    streamThread.join()
    serverThread.join()
