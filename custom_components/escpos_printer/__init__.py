"""ESC/POS Printer integration for Home Assistant."""
import asyncio
import logging
import socket
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

import voluptuous as vol
from escpos.printer import Network

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

DOMAIN = "escpos_printer"
CONF_DISCOVERY_ENABLED = "discovery_enabled"
CONF_DISCOVERY_TIMEOUT = "discovery_timeout"

DEFAULT_PORT = 9100
DEFAULT_DISCOVERY_TIMEOUT = 5

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_DISCOVERY_ENABLED, default=True): cv.boolean,
                vol.Optional(CONF_DISCOVERY_TIMEOUT, default=DEFAULT_DISCOVERY_TIMEOUT): cv.positive_int,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

SERVICE_PRINT_TEXT = "print_text"
SERVICE_PRINT_SIMPLE = "print_simple"
SERVICE_DISCOVER_PRINTERS = "discover_printers"

PRINT_TEXT_SCHEMA = vol.Schema(
    {
        vol.Required("printer"): cv.string,
        vol.Required("text"): cv.string,
        vol.Optional("headline"): cv.string,
    }
)

PRINT_SIMPLE_SCHEMA = vol.Schema(
    {
        vol.Required("text"): cv.string,
        vol.Optional("printer"): cv.string,
    }
)

DISCOVER_PRINTERS_SCHEMA = vol.Schema({})


class PrinterManager:
    """Manages ESC/POS printers and their connections."""

    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self.printers: Dict[str, Dict] = {}
        self.discovered_printers: List[Dict] = []

    def add_printer(self, name: str, host: str, port: int = DEFAULT_PORT) -> bool:
        """Add a new printer."""
        try:
            # Test connection
            printer = Network(host, port=port)
            printer.text("")  # Test connection
            printer.close()

            self.printers[name] = {
                "host": host,
                "port": port,
                "name": name,
            }
            _LOGGER.info(f"Added printer: {name} at {host}:{port}")
            return True
        except Exception as e:
            _LOGGER.error(f"Failed to add printer {name}: {e}")
            return False

    def remove_printer(self, name: str) -> bool:
        """Remove a printer."""
        if name in self.printers:
            del self.printers[name]
            _LOGGER.info(f"Removed printer: {name}")
            return True
        return False

    def print_text(self, printer_name: str, text: str, headline: str = None) -> bool:
        """Print text to a specific printer."""
        if printer_name not in self.printers:
            _LOGGER.error(f"Printer '{printer_name}' not found")
            return False

        try:
            printer_config = self.printers[printer_name]
            printer = Network(printer_config["host"], port=printer_config["port"])

            # Print headline if provided
            if headline:
                printer.set(double_width=True, double_height=True, align="center", bold=True)
                printer.text(f"{headline}\n\n")
                printer.set(double_width=False, double_height=False, align="left", bold=False)

            # Print main text
            printer.text(f"{text}\n\n")

            # Cut paper
            printer.cut()
            printer.close()

            _LOGGER.info(f"Successfully printed to {printer_name}")
            return True
        except Exception as e:
            _LOGGER.error(f"Failed to print to {printer_name}: {e}")
            return False

    def get_printer_status(self, printer_name: str) -> Dict:
        """Get status of a specific printer."""
        if printer_name not in self.printers:
            return {"status": "not_found"}

        try:
            printer_config = self.printers[printer_name]
            printer = Network(printer_config["host"], port=printer_config["port"])
            printer.text("")  # Test connection
            printer.close()
            return {"status": "online", "printer": printer_config}
        except Exception as e:
            return {"status": "offline", "error": str(e), "printer": printer_config}

    def discover_printers(self, timeout: int = DEFAULT_DISCOVERY_TIMEOUT) -> List[Dict]:
        """Discover ESC/POS printers on the network."""
        _LOGGER.info("Starting printer discovery...")
        discovered = []

        try:
            # Get local IP to determine network range
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()

            # Extract network prefix (assuming /24)
            network_prefix = ".".join(local_ip.split(".")[:-1])
            _LOGGER.info(f"Scanning network: {network_prefix}.0/24")

            # Common ESC/POS printer ports
            ports = [9100, 9101, 9102]

            def scan_host(ip):
                for port in ports:
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(1)
                        result = sock.connect_ex((ip, port))
                        sock.close()

                        if result == 0:
                            # Try to connect with python-escpos to verify it's a printer
                            try:
                                printer = Network(ip, port=port)
                                printer.text("")  # Test connection
                                printer.close()

                                discovered.append(
                                    {
                                        "host": ip,
                                        "port": port,
                                        "name": f"Printer at {ip}:{port}",
                                        "status": "discovered",
                                    }
                                )
                                _LOGGER.info(f"Discovered printer at {ip}:{port}")
                                break
                            except Exception as e:
                                _LOGGER.debug(f"Port {port} open at {ip} but not a printer: {e}")
                    except Exception as e:
                        _LOGGER.debug(f"Error scanning {ip}:{port}: {e}")

            # Scan network in parallel
            threads = []
            for i in range(1, 255):
                ip = f"{network_prefix}.{i}"
                thread = threading.Thread(target=scan_host, args=(ip,))
                thread.start()
                threads.append(thread)

                # Limit concurrent threads
                if len(threads) >= 50:
                    for t in threads:
                        t.join()
                    threads = []

            # Wait for remaining threads
            for t in threads:
                t.join()

        except Exception as e:
            _LOGGER.error(f"Error during discovery: {e}")

        self.discovered_printers = discovered
        _LOGGER.info(f"Discovery complete. Found {len(discovered)} printers")
        return discovered


class PrinterEntity(Entity):
    """Representation of a printer entity."""

    def __init__(self, printer_manager: PrinterManager, printer_name: str):
        self._printer_manager = printer_manager
        self._printer_name = printer_name
        self._state = "unknown"

    @property
    def name(self):
        """Return the name of the printer."""
        return f"Printer {self._printer_name}"

    @property
    def state(self):
        """Return the state of the printer."""
        return self._state

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    def update(self):
        """Update the printer status."""
        status = self._printer_manager.get_printer_status(self._printer_name)
        self._state = status["status"]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the ESC/POS Printer component."""
    if DOMAIN not in config:
        return True

    config_data = config[DOMAIN]
    printer_manager = PrinterManager(hass)

    # Store the printer manager in hass data
    hass.data[DOMAIN] = {
        "printer_manager": printer_manager,
        "config": config_data,
    }

    # Set up services
    async def print_text_service(call: ServiceCall) -> None:
        """Service to print text."""
        printer = call.data.get("printer")
        text = call.data.get("text")
        headline = call.data.get("headline")

        if not printer or not text:
            raise HomeAssistantError("Printer name and text are required")

        success = printer_manager.print_text(printer, text, headline)
        if not success:
            raise HomeAssistantError("Failed to print text")

    async def print_simple_service(call: ServiceCall) -> None:
        """Service to print simple text."""
        text = call.data.get("text", "")
        printer = call.data.get("printer")

        if not text:
            raise HomeAssistantError("Text is required")

        if not printer and printer_manager.printers:
            # Use first available printer
            printer = list(printer_manager.printers.keys())[0]
        elif not printer:
            raise HomeAssistantError("No printer configured")

        success = printer_manager.print_text(printer, text)
        if not success:
            raise HomeAssistantError("Failed to print text")

    async def discover_printers_service(call: ServiceCall) -> None:
        """Service to discover printers."""
        timeout = config_data.get(CONF_DISCOVERY_TIMEOUT, DEFAULT_DISCOVERY_TIMEOUT)
        discovered = printer_manager.discover_printers(timeout)
        _LOGGER.info(f"Discovery complete. Found {len(discovered)} printers")

    # Register services
    hass.services.async_register(DOMAIN, SERVICE_PRINT_TEXT, print_text_service, schema=PRINT_TEXT_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_PRINT_SIMPLE, print_simple_service, schema=PRINT_SIMPLE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_DISCOVER_PRINTERS, discover_printers_service, schema=DISCOVER_PRINTERS_SCHEMA)

    # Initial discovery if enabled
    if config_data.get(CONF_DISCOVERY_ENABLED, True):
        _LOGGER.info("Performing initial printer discovery...")
        await hass.async_add_executor_job(printer_manager.discover_printers)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    """Set up ESC/POS Printer from a config entry."""
    # This would be used for config flow entries
    return True


async def async_unload_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    """Unload a config entry."""
    # This would be used for config flow entries
    return True 