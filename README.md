# ESP32 UWB Positioning System

A comprehensive Ultra-Wideband (UWB) positioning system implementation using ESP32 and DW3000 modules. This project enables accurate distance measurement and position tracking using multiple anchors and tags.

This project was developed using [Windsurf](https://codeium.com/windsurf), the world's first agentic IDE, which provides an integrated development environment with AI assistance for efficient coding and project management.

## Features

### Hardware Components
- ESP32 microcontroller
- DW3000 UWB module
- Multiple anchor nodes and tag nodes

### Core Functionality
- **Two-Way Ranging**
  - Accurate distance measurement
  - Time of Flight (ToF) calculation
  - Support for multiple anchors (up to 10)

- **Position System**
  - Multi-anchor positioning
  - Real-time distance tracking
  - Position calculation using trilateration
  - Minimum 2 anchors required for operation

- **Network Communication**
  - WiFi connectivity (optional)
  - UDP broadcast support
  - JSON-formatted data output
  - Rate-limited broadcasts (100ms interval)

### Data Management
- **Anchor Data Structure**
  ```json
  {
      "tag": "T1",
      "anchors": [
          {"id":"A1","distance":1.23,"tof":0.00123},
          {"id":"A2","distance":2.34,"tof":0.00234}
      ]
  }
  ```

- **Validation Features**
  - Maximum valid distance: 8.0 meters
  - Anchor data timeout: 5 seconds
  - Automatic cleanup of invalid data

### Visualization Tools
- Real-time position plotting
- Anchor position display
- Tag movement trail
- Distance measurements visualization

### Simulation Environment
- Tag movement simulator
- Configurable movement patterns
- Measurement noise simulation
- UDP broadcast simulation

## Visualization Demo
![UWB Position Tracking Demo](images/demo.jpg)
*Simulation visualization showing real-time tag tracking with three anchors. The blue squares represent fixed anchor positions, the red dot shows the current tag position, and the red trail indicates the tag's movement history. This demo was generated using our Python-based simulation tools, demonstrating the circular movement pattern with real-time distance calculations and position triangulation.*

## Getting Started

### Hardware Setup
1. Flash the anchor code to ESP32 modules designated as anchors
2. Flash the tag code to ESP32 module designated as tag
3. Position anchors in your target area
4. Power up the system

### Software Requirements
```bash
pip install -r python/requirements.txt
```

### Testing Without Hardware
1. Start the visualization tool:
```bash
python python/uwb_position_display.py
```

2. Run the simulator (in a separate terminal):
```bash
# For circular movement pattern
python python/uwb_tag_simulator.py --movement circle

# For random movement pattern
python python/uwb_tag_simulator.py --movement random
```

## Configuration Parameters

### Hardware Settings
- **Anchor Configuration**
  - Maximum anchors: 10
  - Minimum anchors for position: 2
  - Data timeout: 5000ms
  - Maximum valid distance: 8.0m

### Network Settings
- UDP broadcast port: 12345
- Broadcast IP: 255.255.255.255
- Broadcast interval: 100ms

### Visualization Settings
- Update interval: 100ms
- Trail history: 50 points
- Display range: 9m x 7m

## Development

### Development Environment
- Windsurf IDE for integrated development
- Arduino IDE for ESP32 firmware
- Python 3.x for visualization tools

### Project Structure
- `/range/range_rx/`: Tag implementation
- `/range/range_tx/`: Anchor implementation
- `/python/`: Visualization and simulation tools

### Building and Flashing
1. Use Arduino IDE for ESP32 development
2. Select appropriate board settings
3. Install required libraries
4. Flash to devices

## Contributing
Contributions are welcome! Please feel free to submit pull requests.

## References
- [ESP32 UWB Indoor Positioning Test](https://www.instructables.com/ESP32-UWB-Indoor-Positioning-Test/) - Basic implementation guide
- [Makerfabs ESP32 UWB Indoor Positioning](https://github.com/Makerfabs/Makerfabs-ESP32-UWB/tree/main/example/IndoorPositioning) - Reference implementation
- [Makerfabs ESP32 UWB DW3000](https://github.com/Makerfabs/Makerfabs-ESP32-UWB-DW3000) - Hardware documentation and examples

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
