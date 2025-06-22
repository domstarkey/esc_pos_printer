# Home Assistant ESC/POS Printer Integration

A Home Assistant integration that provides printer discovery and text printing services for ESC/POS compatible network printers.

## Features

- **Automatic Printer Discovery**: Scans your network for ESC/POS printers
- **Manual Printer Configuration**: Add printers by IP address and port
- **Text Printing Service**: Print text with optional headlines
- **Printer Status Monitoring**: Check if printers are online/offline
- **Native Home Assistant Integration**: Runs directly in Home Assistant

## Installation

### Method 1: Manual Installation

1. Download this repository
2. Copy the `custom_components/escpos_printer` folder to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant
4. Add the integration to your `configuration.yaml`

### Method 2: HACS (Home Assistant Community Store)

1. Install HACS if you haven't already
2. Add this repository as a custom repository in HACS
3. Install the integration through HACS
4. Add the integration to your `configuration.yaml`

## Configuration

### Basic Configuration

Add this to your `configuration.yaml`:

```yaml
escpos_printer:
  discovery_enabled: true
  discovery_timeout: 5
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `discovery_enabled` | boolean | `true` | Enable automatic printer discovery on startup |
| `discovery_timeout` | integer | `5` | Timeout for printer discovery in seconds |

## Usage

### Services

The integration provides three services:

#### Print Text

```yaml
service: escpos_printer.print_text
data:
  printer: "Kitchen Printer"
  text: "Hello, World!"
  headline: "Important Message"
```

#### Print Simple Text

```yaml
service: escpos_printer.print_simple
data:
  text: "Simple text to print"
  printer: "Kitchen Printer"  # Optional, uses default if not specified
```

#### Discover Printers

```yaml
service: escpos_printer.discover_printers
data: {}
```

### Adding Printers

Printers are added programmatically through the integration. You can:

1. Use the discovery service to find printers on your network
2. Add printers manually by calling the service with printer details
3. Check the Home Assistant logs for discovered printers

## Examples

### Print a daily message

```yaml
automation:
  - alias: "Print Daily Message"
    trigger:
      platform: time
      at: "08:00:00"
    action:
      - service: escpos_printer.print_text
        data:
          printer: "Kitchen Printer"
          headline: "Good Morning!"
          text: "Today is {{ now().strftime('%A, %B %d, %Y') }}"
```

### Print when motion is detected

```yaml
automation:
  - alias: "Print Motion Alert"
    trigger:
      platform: state
      entity_id: binary_sensor.motion_sensor
      to: "on"
    action:
      - service: escpos_printer.print_text
        data:
          printer: "Office Printer"
          headline: "Motion Detected"
          text: "Motion detected at {{ now().strftime('%H:%M:%S') }}"
```

### Print sensor data

```yaml
automation:
  - alias: "Print Temperature Report"
    trigger:
      platform: time
      at: "12:00:00"
    action:
      - service: escpos_printer.print_text
        data:
          printer: "Kitchen Printer"
          headline: "Temperature Report"
          text: |
            Living Room: {{ states('sensor.living_room_temperature') }}°C
            Bedroom: {{ states('sensor.bedroom_temperature') }}°C
            Kitchen: {{ states('sensor.kitchen_temperature') }}°C
```

### Print simple message

```yaml
script:
  print_simple_message:
    alias: "Print Simple Message"
    sequence:
      - service: escpos_printer.print_simple
        data:
          text: "Hello from Home Assistant!"
```

### Discover printers

```yaml
script:
  discover_printers:
    alias: "Discover Printers"
    sequence:
      - service: escpos_printer.discover_printers
```

## Troubleshooting

### Integration Not Loading

1. Check that the `custom_components/escpos_printer` folder is in the correct location
2. Verify the `manifest.json` file is present and valid
3. Check Home Assistant logs for any errors
4. Restart Home Assistant after installation

### Printer Not Found

1. Check that the printer is powered on and connected to the network
2. Verify the IP address and port are correct
3. Ensure the printer supports ESC/POS protocol
4. Run the discovery service to find printers

### Print Jobs Fail

1. Verify printer IP and port
2. Check printer is online
3. Check Home Assistant logs for errors
4. Test printer connectivity manually

### Discovery Issues

1. Discovery scans the local network (192.168.x.x, 10.x.x.x, etc.)
2. Some printers may not respond to discovery probes
3. Check firewall settings
4. Try manual configuration if discovery fails

## Supported Printers

This integration works with any ESC/POS compatible network printer, including:

- Thermal receipt printers
- Label printers
- POS printers
- Any printer supporting ESC/POS commands over TCP/IP

## Development

### Requirements

- `python-escpos==3.1`

### Local Development

1. Clone this repository
2. Copy to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant
4. Check logs for any errors

## License

This project is licensed under the MIT License. 