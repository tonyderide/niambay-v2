"""WebSocket server for Niam-Bay daemon."""

import asyncio
import json
from datetime import datetime, timezone

import websockets


class NiamBayServer:
    """WebSocket server that broadcasts events to connected clients."""

    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: set = set()
        self._message_handler = None

    def on_message(self, handler):
        """Register an async handler for incoming client messages."""
        self._message_handler = handler

    @staticmethod
    def format_event(event_type: str, data: dict) -> str:
        """Format an event as a JSON string with type, data, and timestamp."""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return json.dumps(event)

    async def broadcast(self, event_type: str, data: dict):
        """Send an event to all connected clients, removing dead ones."""
        if not self.clients:
            return
        message = self.format_event(event_type, data)
        dead = set()
        for client in self.clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                dead.add(client)
        self.clients -= dead

    async def _handler(self, websocket):
        """Manage a single client's lifecycle."""
        self.clients.add(websocket)
        try:
            async for raw in websocket:
                try:
                    message = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if self._message_handler:
                    await self._message_handler(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)

    async def start(self):
        """Run the WebSocket server forever."""
        async with websockets.serve(self._handler, self.host, self.port):
            await asyncio.Future()  # run forever
