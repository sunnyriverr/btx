"""Loopback TCP relay with one aggregate downstream pacing clock."""
import asyncio
import threading
import time

class Relay:
    def __init__(self, backend, rate=1 << 20):
        self.backend = backend
        self.rate = rate
        self.samples = []
        self.interrupted = False
        self.closed_streams = 0
        self.writers = set()
        self.handlers = set()
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()
        self.port = self.call(self.start())

    def call(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result(10)

    async def start(self):
        self.lock = asyncio.Lock()
        self.next_send = 0
        self.server = await asyncio.start_server(self.serve, '127.0.0.1', 0, limit=32768)
        return self.server.sockets[0].getsockname()[1]

    async def pump(self, reader, writer, paced):
        while chunk := await reader.read(16384):
            if paced:
                async with self.lock:
                    now = self.loop.time()
                    await asyncio.sleep(max(0, self.next_send - now))
                    sent = self.loop.time()
                    self.next_send = sent + len(chunk) / self.rate
                    writer.write(chunk)
                    self.samples.append((sent, len(chunk)))
            else:
                writer.write(chunk)
            await writer.drain()

    async def serve(self, client, client_writer):
        if self.interrupted:
            client_writer.close()
            return
        upstream = None
        tasks = []
        handler = asyncio.current_task()
        self.handlers.add(handler)
        self.writers.add(client_writer)
        try:
            upstream_reader, upstream = await asyncio.open_connection('127.0.0.1', self.backend, limit=32768)
            self.writers.add(upstream)
            tasks = [asyncio.create_task(self.pump(client, upstream, False)),
                     asyncio.create_task(self.pump(upstream_reader, client_writer, True))]
            _, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        except OSError:
            pass
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            self.handlers.discard(handler)
            for writer in (client_writer, upstream):
                if writer is not None:
                    writer.close()
                    self.writers.discard(writer)

    async def interrupt(self):
        self.interrupted = True
        self.closed_streams = len(self.writers)
        for writer in list(self.writers):
            writer.transport.abort()

    async def resume(self):
        self.interrupted = False

    async def shutdown(self):
        self.server.close()
        # Python 3.12+ may wait for live connections in wait_closed().
        for writer in list(self.writers):
            writer.transport.abort()
        handlers = list(self.handlers)
        for handler in handlers:
            handler.cancel()
        await asyncio.gather(*handlers, return_exceptions=True)
        await self.server.wait_closed()

    def close(self):
        if self.thread.is_alive():
            self.call(self.shutdown())
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.thread.join(5)
            self.loop.close()

def pacing(samples, rate):
    if len(samples) < 2:
        return False
    # The earlier chunk must consume its share of the aggregate schedule.
    return all(size > 0 and size <= 16384 and (next_at - at) * rate + 64 >= size
               for (at, size), (next_at, _) in zip(samples, samples[1:]))
