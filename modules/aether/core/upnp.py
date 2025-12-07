
import socket
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

class UPnPManager:
    """
    Manages Universal Plug and Play (UPnP) to automatically forward ports on the router.
    This allows Aether to be reachable from WAN without manual port forwarding.
    """
    def __init__(self):
        self.gateway_url = None
        self.service_url = None
        self.local_ip = None
        
    def discover(self):
        """Find the Gateway using SSDP."""
        SSDP_ADDR = "239.255.255.250"
        SSDP_PORT = 1900
        SSDP_MX = 2
        SSDP_ST = "urn:schemas-upnp-org:service:WANIPConnection:1"

        ssdpRequest = "M-SEARCH * HTTP/1.1\r\n" + \
                      "HOST: {}:{}\r\n".format(SSDP_ADDR, SSDP_PORT) + \
                      "MAN: \"ssdp:discover\"\r\n" + \
                      "MX: {}\r\n".format(SSDP_MX) + \
                      "ST: {}\r\n".format(SSDP_ST) + "\r\n"

        # Try to find the correct interface by connecting to a public DNS
        try:
            temp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            temp_sock.connect(("8.8.8.8", 80))
            self.local_ip = temp_sock.getsockname()[0]
            temp_sock.close()
        except:
            self.local_ip = socket.gethostbyname(socket.gethostname())

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(3)
        
        # Bind to the specific local IP to ensure we use the correct interface
        try:
            sock.bind((self.local_ip, 0))
        except:
            pass # Fallback to default
            
        try:
            sock.sendto(ssdpRequest.encode(), (SSDP_ADDR, SSDP_PORT))
            
            while True:  # Read all responses
                try:
                    data, addr = sock.recvfrom(4096)
                    # Use the first valid response
                    response = data.decode()
                    location = None
                    for line in response.split('\r\n'):
                        if line.lower().startswith('location:'):
                            location = line.split(':', 1)[1].strip()
                            break
                    
                    if location:
                        self.gateway_url = location
                        self._parse_desc(location)
                        return True
                except socket.timeout:
                    break
        except Exception as e:
            print(f"[UPnP] Discovery Failed: {e}")
        finally:
            sock.close()
            
        return False

    def _get_local_ip(self, target_ip):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((target_ip, 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return socket.gethostbyname(socket.gethostname())

    def _parse_desc(self, url):
        try:
            # Fetch XML description
            resp = urllib.request.urlopen(url, timeout=3)
            data = resp.read()
            
            # Robust XML Parsing (Namespace Agnostic)
            try:
                root = ET.fromstring(data)
                
                control_url = None
                # Iterate recursively over all elements
                for node in root.iter():
                    # Check if this node is a 'service' container
                    if node.tag.lower().endswith("service"):
                        s_type = None
                        c_url = None
                        
                        # Check children for serviceType and controlURL
                        for child in node:
                            if child.tag.lower().endswith("servicetype"):
                                s_type = child.text
                            elif child.tag.lower().endswith("controlurl"):
                                c_url = child.text
                        
                        # Match WANIPConnection
                        if s_type and "WANIPConnection:1" in s_type and c_url:
                            control_url = c_url
                            break
                
                if control_url:
                    # Construct full URL
                    parse = urllib.parse.urlparse(url)
                    base = f"{parse.scheme}://{parse.netloc}"
                    if not control_url.startswith("/"):
                        control_url = "/" + control_url
                    self.service_url = base + control_url
                    print(f"[UPnP] Service URL found: {self.service_url}")
                    return

            except Exception as xml_e:
                print(f"[UPnP] XML Error: {xml_e}")

            # Fallback: Simple String Search (Last Resort)
            # Some old routers have really broken XML that ET rejects
            content = data.decode()
            if "WANIPConnection:1" in content:
                parts = content.split("WANIPConnection:1")
                if len(parts) > 1:
                    after = parts[1]
                    if "<controlURL>" in after:
                        ctrl = after.split("<controlURL>")[1].split("</controlURL>")[0]
                        
                        parse = urllib.parse.urlparse(url)
                        base = f"{parse.scheme}://{parse.netloc}"
                        if not ctrl.startswith("/"):
                            ctrl = "/" + ctrl
                        self.service_url = base + ctrl
                        print(f"[UPnP] Service URL found (Fallback): {self.service_url}")

        except Exception as e:
            print(f"[UPnP] Descriptor Fetch Error: {e}")

    def add_port_mapping(self, external_port, internal_port, protocol="TCP", lease_duration=0, description="Aether P2P"):
        if not self.service_url or not self.local_ip:
            print("[UPnP] Cannot add mapping: Service or Local IP not found.")
            return False

        # Clean, minimized XML to avoid parsing issues on strict routers
        soap_body = (
            '<?xml version="1.0"?>'
            '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
            '<s:Body>'
            '<u:AddPortMapping xmlns:u="urn:schemas-upnp-org:service:WANIPConnection:1">'
            '<NewRemoteHost></NewRemoteHost>'
            f'<NewExternalPort>{external_port}</NewExternalPort>'
            f'<NewProtocol>{protocol}</NewProtocol>'
            f'<NewInternalPort>{internal_port}</NewInternalPort>'
            f'<NewInternalClient>{self.local_ip}</NewInternalClient>'
            '<NewEnabled>1</NewEnabled>'
            f'<NewPortMappingDescription>{description}</NewPortMappingDescription>'
            f'<NewLeaseDuration>{lease_duration}</NewLeaseDuration>'
            '</u:AddPortMapping>'
            '</s:Body>'
            '</s:Envelope>'
        )

        headers = {
            'SOAPAction': '"urn:schemas-upnp-org:service:WANIPConnection:1#AddPortMapping"',
            'Content-Type': 'text/xml; charset="utf-8"',
            'Content-Length': str(len(soap_body))
        }

        try:
            req = urllib.request.Request(self.service_url, data=soap_body.encode(), headers=headers)
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    print(f"[UPnP] Successfully mapped {protocol} {external_port} -> {self.local_ip}:{internal_port}")
                    return True
        except urllib.error.HTTPError as e:
            # Read detailed SOAP Fault
            error_content = e.read().decode()
            print(f"[UPnP] AddPortMapping Failed (HTTP {e.code}): {error_content}")
            
            # Simple Fallback: Try without LeaseDuration (some old routers hate it)
            if "LeaseDuration" in error_content or e.code == 500:
                 return self._add_port_mapping_fallback(external_port, internal_port, protocol, description)
                 
        except Exception as e:
            print(f"[UPnP] AddPortMapping Failed: {e}")
            
        return False

    def _add_port_mapping_fallback(self, external_port, internal_port, protocol, description):
        """Fallback method for older routers (No LeaseDuration)."""
        print("[UPnP] Retrying with Fallback Strategy (No LeaseDuration)...")
        soap_body = (
            '<?xml version="1.0"?>'
            '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
            '<s:Body>'
            '<u:AddPortMapping xmlns:u="urn:schemas-upnp-org:service:WANIPConnection:1">'
            '<NewRemoteHost></NewRemoteHost>'
            f'<NewExternalPort>{external_port}</NewExternalPort>'
            f'<NewProtocol>{protocol}</NewProtocol>'
            f'<NewInternalPort>{internal_port}</NewInternalPort>'
            f'<NewInternalClient>{self.local_ip}</NewInternalClient>'
            '<NewEnabled>1</NewEnabled>'
            f'<NewPortMappingDescription>{description}</NewPortMappingDescription>'
            '</u:AddPortMapping>'
            '</s:Body>'
            '</s:Envelope>'
        )
        
        headers = {
            'SOAPAction': '"urn:schemas-upnp-org:service:WANIPConnection:1#AddPortMapping"',
            'Content-Type': 'text/xml; charset="utf-8"',
            'Content-Length': str(len(soap_body))
        }

        try:
             req = urllib.request.Request(self.service_url, data=soap_body.encode(), headers=headers)
             with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    print(f"[UPnP] Fallback Success! Mapped {protocol} {external_port} -> {self.local_ip}:{internal_port}")
                    return True
        except Exception as e:
             print(f"[UPnP] Fallback Failed: {e}")
             
        return False
