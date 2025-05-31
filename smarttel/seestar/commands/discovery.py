"""Seestar discovery commands."""
import asyncio
import json
import socket
import sys
from contextlib import suppress
import click
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Header, Footer, Static, Button, DataTable

from cli.ui import SeestarUI
from smarttel.seestar.client import SeestarClient


def get_network_info():
    """Get local IP and broadcast IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't have to be reachable
        s.connect(('10.255.255.255', 1))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = '127.0.0.1'
    finally:
        s.close()
    
    # Create broadcast IP based on local IP (simple approach)
    ip_parts = local_ip.split('.')
    broadcast_ip = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.255"
    
    return local_ip, broadcast_ip


async def discover_seestars(timeout=10):
    """Discover Seestars using asyncio for asynchronous UDP broadcasting.
    
    Returns:
        list: List of discovered Seestar devices with their information.
    """
    # Broadcast message to send to Seestar

    local_ip, broadcast_ip = get_network_info()
    broadcast_message = json.dumps({"id": 201, "method": "scan_iscope", "name": "iphone", "ip": local_ip}) + "\r\n"
    discovered_devices = []

    # Convert the message to JSON string and then to bytes
    message = broadcast_message.encode('utf-8')

    # Create a UDP socket for broadcasting
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        # Bind to a local address to receive responses
        sock.bind(('0.0.0.0', 0))

        # Create a transport for the socket
        loop = asyncio.get_event_loop()

        # Protocol to handle responses
        class DiscoveryProtocol(asyncio.DatagramProtocol):
            def connection_made(self, transport):
                self.transport = transport

            def datagram_received(self, data, addr):
                print(f"Received response from {addr}")
                try:
                    response = json.loads(data.decode('utf-8'))
                    discovered_devices.append({
                        'address': addr[0],
                        'data': response
                    })
                except json.JSONDecodeError:
                    print(f"Received non-JSON response from {addr}: {data}")

        # Create the protocol and get the transport
        transport, protocol = await loop.create_datagram_endpoint(
            DiscoveryProtocol,
            sock=sock
        )

        port = 4720
        transport.sendto(message, (broadcast_ip, port))
        print(f"Sent discovery message to broadcast:{port}")

        # Wait for responses
        await asyncio.sleep(timeout)  # Listen for specified seconds

        # Close the transport
        transport.close()

    except Exception as e:
        print(f"Error during discovery: {e}")
        sock.close()

    print(f"Discovery complete. Found {len(discovered_devices)} devices.")
    return discovered_devices


class DevicePickerApp(App):
    """Device picker UI for discovered Seestar devices."""
    
    CSS_PATH = "ui.tcss"
    TITLE = "Seestar Device Picker"
    
    def __init__(self, devices):
        super().__init__()
        self.devices = devices
        self.selected_device = None
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        
        with VerticalScroll():
            yield Static("Select a Seestar device to connect:", id="instructions")
            yield DataTable(id="devices-table")
            yield Button("Connect", id="connect-button", disabled=True)
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Set up the UI when the app is mounted."""
        # Set up the devices table
        table = self.query_one("#devices-table")
        table.add_columns("IP Address", "Device Info")
        
        # Add devices to the table
        for i, device in enumerate(self.devices):
            try:
                device_info = json.dumps(device['data'], indent=2)
                table.add_row(device['address'], device_info[:50] + "..." if len(device_info) > 50 else device_info)
            except (KeyError, TypeError):
                table.add_row(device['address'], "Unknown device info")
    
    def on_data_table_row_selected(self, event) -> None:
        """Handle row selection in the devices table."""
        self.selected_device = self.devices[event.row_index]
        self.query_one("#connect-button").disabled = False
    
    def on_button_pressed(self, event) -> None:
        """Handle the Connect button press."""
        if event.button.id == "connect-button" and self.selected_device:
            self.exit(self.selected_device)


async def select_device_and_connect(host=None, port=None):
    """Discover devices and either connect directly or show a picker UI."""
    if host and port:
        # If host and port are provided, connect directly
        app = SeestarUI(host, port)
        app.run()
    else:
        # Discover devices
        print("Discovering Seestar devices...")
        devices = await discover_seestars()
        
        if not devices:
            print("No Seestar devices found. Exiting.")
            return
        
        # Show the device picker UI
        device_picker = DevicePickerApp(devices)
        selected_device = device_picker.run()
        
        if selected_device:
            # Connect to the selected device
            print(f"Connecting to {selected_device['address']}:4700")
            app = SeestarUI(selected_device['address'], 4700)
            app.run()
        else:
            print("No device selected. Exiting.")


@click.command()
@click.option("--host", help="Seestar host address")
@click.option("--port", type=int, default=4700, help="Seestar port (default: 4700)")
def main(host, port):
    """Connect to a Seestar device, with optional device discovery."""
    asyncio.run(select_device_and_connect(host, port))


if __name__ == "__main__":
    main()