import asyncio
import collections
import json
from typing import TypeVar, Literal

from pydantic import BaseModel

from smarttel.seestar.commands.common import CommandResponse
from smarttel.seestar.commands.simple import GetTime
from smarttel.seestar.connection import SeestarConnection
from smarttel.seestar.events import EventTypes

U = TypeVar("U")


class SeestarStatus(BaseModel):
    """Seestar status."""
    temp: float | None = None


class ParsedEvent(BaseModel):
    """Parsed event."""
    event: EventTypes


class SeestarClient(BaseModel, arbitrary_types_allowed=True):
    """Seestar client."""
    host: str
    port: int
    connection: SeestarConnection | None = None
    id: int = 1
    is_connected: bool = False
    debug: bool = False
    status: SeestarStatus = SeestarStatus()
    background_task: asyncio.Task | None = None
    recent_events: collections.deque = collections.deque(maxlen=5)

    def __init__(self, host: str, port: int, debug=False):
        super().__init__(host=host, port=port)

        self.debug = debug
        self.connection = SeestarConnection(host=host, port=port)

    async def _heartbeat(self):
        while True:
            if self.is_connected:
                #print(f"Pinging {self}")
                _ = await self.send(GetTime())
            # todo : decrease sleep time to 1 second and, instead, check next heartbeat time
            await asyncio.sleep(11)

    async def connect(self):
        await self.connection.open()
        self.is_connected = True

        self.background_task = asyncio.create_task(self._heartbeat())
        if self.debug:
            print(f"Connected to {self}")

    async def disconnect(self):
        """Disconnect from Seestar."""
        await self.connection.close()
        self.is_connected = False
        if self.debug:
            print(f"Disconnected from {self}")

    async def send(self, data: str | BaseModel):
        # todo : do connected check...
        # todo : set "next heartbeat" time, and then in the heartbeat task, check the value
        if isinstance(data, BaseModel):
            if data.id is None:
                data.id = self.id
                self.id += 1
            data = data.model_dump_json()
        await self.connection.write(data)

    def _handle_event(self, event_str: str):
        """Parse an event."""
        parsed = json.loads(event_str)
        try:
            parser: ParsedEvent = ParsedEvent(event=parsed)
            # print(f"Received event from {self}: {type(parser.event)} {parser}")
            print(f'Received event from {self}: {type(parser.event)}')
            self.recent_events.append(parser.event)
            if parser.event.Event == Literal['PiStatus']:
                pi_status = parser.event
                if pi_status.temp is not None:
                    self.status = pi_status.temp
        except Exception as e:
            print(f"Error while parsing event from {self}: {event_str} {type(e)} {e}")

    async def send_and_recv(self, data: str | BaseModel) -> CommandResponse[U] | None:
        await self.send(data)
        # below is naive...  should change it to wait for the specific command...
        # xxx ugh!
        while self.is_connected:
            response = await self.recv()
            if response is not None:
                return response
        return None

    async def recv(self) -> CommandResponse[U] | None:
        """Receive data from Seestar."""
        response = ""
        try:
            while 'jsonrpc' not in response:
                response = await self.connection.read()
                #if self.debug:
                #    print(f"Received data from {self}: {response}")
                if response is None:
                    await self.disconnect()
                    return None
                if 'Event' in response:
                    # it's an event, so parse it and stash!
                    self._handle_event(response)
                    return None
            return CommandResponse[U](**json.loads(response))
        except Exception as e:
            print(f"Error while receiving data from {self}: {response} {e}")
            raise e

    def __str__(self):
        return f"{self.host}:{self.port}"
