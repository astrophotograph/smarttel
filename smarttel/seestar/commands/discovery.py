"""Seestar discovery commands."""
import asyncio
import json
import socket

async def discover_seestars():
    """Discover Seestars using asyncio for asynchronous UDP broadcasting.
    
    Returns:
        list: List of discovered Seestar devices with their information.
    """
    broadcast_message = {"id": 1, "method": "scan_iscope", "params": ""}
    discovered_devices = []
    
    # Convert the message to JSON string and then to bytes
    message = json.dumps(broadcast_message).encode('utf-8')
    
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
        
        # Send broadcast
        broadcast_address = '<broadcast>'
        port = 4720
        transport.sendto(message, (broadcast_address, port))
        print(f"Sent discovery message to broadcast:{port}")
        
        # Wait for responses
        await asyncio.sleep(10)  # Listen for 10 seconds
        
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