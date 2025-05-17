import json
from typing import TypeVar, Literal

from pydantic import BaseModel

from smarttel.seestar.commands.common import CommandResponse
from smarttel.seestar.connection import SeestarConnection
from smarttel.seestar.events import EventTypes

U = TypeVar("U")


class SeestarStatus(BaseModel):
    """Seestar status."""
    temp: float | None = None


class ParsedEvent(BaseModel):
    """Parsed event."""
    event: EventTypes


class SeestarClient(BaseModel):
    """Seestar client."""
    host: str
    port: int
    connection: SeestarConnection | None = None
    id: int = 1
    debug: bool = False
    status: SeestarStatus = SeestarStatus()

    def __init__(self, host: str, port: int, debug=False):
        super().__init__(host=host, port=port)

        self.debug = debug
        self.connection = SeestarConnection(host=host, port=port)

    async def connect(self):
        await self.connection.open()
        if self.debug:
            print(f"Connected to {self}")

    async def disconnect(self):
        """Disconnect from Seestar."""
        await self.connection.close()
        if self.debug:
            print(f"Disconnected from {self}")

    async def send(self, data: str | BaseModel):
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
            #print(f"Received event from {self}: {type(parser.event)} {parser}")
            print(f'Received event from {self}: {type(parser.event)}')
            if parser.event.Event == Literal['PiStatus']:
                pi_status = parser.event
                if pi_status.temp is not None:
                    self.status = pi_status.temp
        except Exception as e:
            print(f"Error while parsing event from {self}: {event_str} {type(e)} {e}")

    async def send_and_recv(self, data: str | BaseModel) -> CommandResponse[U]:
        await self.send(data)
        # below is naive...  should change it to wait for the specific command...
        return await self.recv()

    async def recv(self) -> CommandResponse[U] | None:
        """Receive data from Seestar."""
        response = ""
        try:
            while 'jsonrpc' not in response:
                response = await self.connection.read()
                # if self.debug:
                #    print(f"Received data from {self}: {response}")
                if 'Event' in response:
                    # it's an event, so parse it and stash!
                    self._handle_event(response)
            return CommandResponse[U](**json.loads(response))
        except Exception as e:
            print(f"Error while receiving data from {self}: {response} {e}")
            raise e

    def __str__(self):
        return f"{self.host}:{self.port}"
