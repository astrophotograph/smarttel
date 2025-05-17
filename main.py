import asyncio
import sys
from typing import Literal

from cli.ui import SeestarUI
from smarttel.seestar.client import SeestarClient
from smarttel.seestar.commands.common import CommandResponse
from smarttel.seestar.commands.parameterized import IscopeStopView, StopStage
from smarttel.seestar.commands.simple import GetTime, GetTimeResponse, GetCameraInfo, GetCameraInfoResponse, \
    GetCameraState, GetDiskVolume, GetDeviceState, GetViewState, GetSetting, GetUserLocation, ScopeGetEquCoord, \
    ScopeGetRaDecCoord, GetAnnotatedResult, GetFocuserPosition, GetWheelSetting, GetWheelState, GetWheelPosition


async def runner(host: str, port: int):
    client = SeestarClient(host, port, debug=True)

    await client.connect()

    while True:
        msg: CommandResponse[GetTimeResponse] = await client.send_and_recv(GetTime())
        #print(f'---> Received: {msg}')
        print('')
        await asyncio.sleep(5)

    #msg: CommandResponse[dict] = await client.send_and_recv(GetWheelPosition())
    #print(f'Received: {msg}')
    #await asyncio.sleep(1)

    await client.disconnect()
    await asyncio.sleep(1)


def main(host: str, port: int):
    # app = SeestarUI()
    # app.run()
    asyncio.run(runner(host, port))

if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]))
