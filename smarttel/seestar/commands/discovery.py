"""Seestar discovery commands."""
import asyncio
import json
import socket

import netifaces


def get_network_info():
    """Get primary interface IP and broadcast address."""
    gateways = netifaces.gateways()
    if 'default' in gateways and netifaces.AF_INET in gateways['default']:
        interface = gateways['default'][netifaces.AF_INET][1]
        addrs = netifaces.ifaddresses(interface)
        if netifaces.AF_INET in addrs:
            ip = addrs[netifaces.AF_INET][0]['addr']
            netmask = addrs[netifaces.AF_INET][0]['netmask']
            network = int(''.join(['%02x' % int(x) for x in ip.split('.')]), 16) & int(
                ''.join(['%02x' % int(x) for x in netmask.split('.')]), 16)
            broadcast = socket.inet_ntoa(network.to_bytes(4, byteorder='big'))
            return ip, broadcast
    return '0.0.0.0', '255.255.255.255'


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
        await asyncio.sleep(timeout)  # Listen for 10 seconds

        # Close the transport
        transport.close()

    except Exception as e:
        print(f"Error during discovery: {e}")
        sock.close()

    print(f"Discovery complete. Found {len(discovered_devices)} devices.")
    return discovered_devices


async def main():
    """Run discovery as a standalone script."""
    discovered = await discover_seestars()
    for device in discovered:
        print(f"Device at {device['address']}: {device['data']}")


if __name__ == "__main__":
    # Run discovery if script is executed directly
    asyncio.run(main())
