import asyncio
import sys
import click
from contextlib import suppress

from smarttel.seestar.client import SeestarClient
from smarttel.seestar.commands.common import CommandResponse
from smarttel.seestar.commands.discovery import select_device_and_connect
from smarttel.seestar.commands.simple import GetViewState


async def runner(host: str, port: int):
    client = SeestarClient(host, port, debug=True)

    await client.connect()

    msg: CommandResponse[dict] = await client.send_and_recv(GetViewState())
    print(f'Received GetViewState: {msg}')
    #while True:
    #    #msg: CommandResponse[GetTimeResponse] = await client.send_and_recv(GetTime())
    #    #print(f'---> Received: {msg}')
    #    print('')
    #    #await asyncio.sleep(5)

    while client.is_connected:
        msg = await client.recv()
        if msg is not None:
            print(f'----> Received: {msg}')
        with suppress(IndexError):
            event = client.recent_events.popleft()
            print(f'----> Event: {event}')
        await asyncio.sleep(0.1)

    #msg: CommandResponse[dict] = await client.send_and_recv(GetWheelPosition())
    #print(f'Received: {msg}')

    await client.disconnect()
    await asyncio.sleep(1)

@click.command()
@click.option("--host", help="Seestar host address")
@click.option("--port", type=int, default=4700, help="Seestar port (default: 4700)")
def main(host, port):
    """Connect to a Seestar device, with optional device discovery."""
    asyncio.run(select_device_and_connect(host, port))


if __name__ == "__main__":
    main()
