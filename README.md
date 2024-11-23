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
  - Maximum valid distance: 8.0 meters
  - Anchor data timeout: 5 seconds

- **Network Communication**
  - Optional WiFi connectivity (can be enabled when needed)
  - UDP broadcast support (when WiFi enabled)
  - JSON-formatted data output
  - Rate-limited broadcasts (100ms interval)

### Data Management
- **System Parameters**
  - Maximum anchors: 10
  - Minimum anchors for positioning: 2
  - Maximum valid distance: 8.0 meters
  - Anchor data timeout: 5 seconds
  - UDP broadcast interval: 100ms
  - JSON buffer size: 512 bytes (for multiple anchors)

- **Tag/Anchor Configuration**
  ```cpp
  // Tag Configuration (in range_rx.ino)
  const uint8_t TAG_ADDR[] = { 'T', '1' };      // Tag Address

  // Anchor Configuration (in range_rx.ino)
  #define NUM_ANCHORS 3  // Number of anchors
  static const char ANCHOR_LIST[NUM_ANCHORS][2] = {
      {'A', '1'},  // Anchor 1
      {'A', '2'},  // Anchor 2
      {'A', '3'}   // Anchor 3
  };
  ```

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
- Interactive Web Visualization ([Live Demo](https://kunyi.github.io/esp32-uwb-positioning-system/))
  - Real-time anchor and tag position display
  - Configurable positioning methods (2/3/many anchors)
  - Dynamic range visualization
  - Position error estimation

### Simulation Environment
- Tag movement simulator
- Configurable movement patterns
- Measurement noise simulation
- UDP broadcast simulation

## Quick Start Guide

### 1. Hardware Requirements
- 2-5+ ESP32 boards with DW3000 UWB modules (1 for tag, others for anchors)
- USB cables for programming
- Power supply for anchors (battery or USB)
- Computer for development and visualization

#### Positioning Capabilities by Number of Anchors:
| Anchors | Capabilities | Limitations |
|---------|-------------|-------------|
| 2 | - Distance measurement only<br>- Two possible positions (circle intersection) | - Cannot determine unique position<br>- Limited to 1D measurements |
| 3 | - Basic 2D positioning<br>- Distance triangulation | - Possible ambiguity in position<br>- Limited accuracy |
| 4 | - Full 2D/3D positioning<br>- Unique position determination<br>- Height measurement possible if anchors not coplanar | - Requires careful anchor placement<br>- Minimum setup for 3D |
| 5+ | - Enhanced 2D/3D positioning<br>- Redundant measurements<br>- Improved accuracy and reliability | - Increased system complexity<br>- Requires more calibration |

For optimal results, we recommend:
- Basic Distance Testing: 2 anchors
- 2D Positioning: 3-4 anchors (4 for better accuracy)
- 3D Positioning: 4+ anchors (non-coplanar arrangement)

Important Notes:
- For 3D positioning, at least 4 anchors must not be in the same plane
- Additional anchors (5+) provide redundancy and improve accuracy
- Anchor placement geometry affects positioning accuracy
- Consider using more anchors in challenging environments (obstacles, interference)

### 2. Software Setup
1. Install Required Software:
   ```bash
   # Install Python dependencies
   pip install -r python/requirements.txt

   # Install Arduino IDE
   # Download from: https://www.arduino.cc/en/software
   ```

2. Arduino IDE Configuration:
   - Install ESP32 board support
     1. Open Arduino IDE
     2. Go to `File > Preferences`
     3. Add to Additional Board Manager URLs:
        ```
        https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
        ```
     4. Go to `Tools > Board > Boards Manager`
     5. Search for "esp32" and install

### 3. Hardware Setup
1. Anchor Placement:
   - Place anchors in a triangle formation
   - Recommended height: 1.5-2 meters from ground
   - Keep clear line of sight between anchors
   - Example layout:
     * Anchor 1 (A1): (0, 0) - Origin point
     * Anchor 2 (A2): (8m, 0) - Along X-axis
     * Anchor 3 (A3): (4m, 6m) - Triangle top

2. Power and Connections:
   - Connect each ESP32 to power source
   - Ensure stable power supply
   - Keep USB cables away from UWB antennas

### 4. System Configuration
1. Configure Anchors:
   ```cpp
   // In range_tx.ino
   const uint8_t ANCHOR_ADDR[] = { 'A', '1' };   // Change for each anchor (A1, A2, A3, etc.)
   ```

2. Configure Tag:
   ```cpp
   // In range_rx.ino
   const uint8_t TAG_ADDR[] = { 'T', '1' };  // Tag Address
   // Configure anchor list
   #define NUM_ANCHORS 3  // Set number of anchors
   static const char ANCHOR_LIST[NUM_ANCHORS][2] = {
       {'A', '1'},  // Anchor 1
       {'A', '2'},  // Anchor 2
       {'A', '3'}   // Anchor 3
   };
   ```

3. WiFi Settings (Optional):
   ```cpp
   #define ENABLE_WIFI        // Comment out to disable WiFi
   #define WIFI_SSID "YourSSID"
   #define WIFI_PASS "YourPassword"
   ```

### 5. Flashing Instructions
1. Flash Anchors:
   - Open `range/range_tx/range_tx.ino`
   - Select correct board and port in Arduino IDE
   - Upload to each anchor (remember to change ANCHOR_ID)

2. Flash Tag:
   - Open `range/range_rx/range_rx.ino`
   - Select correct board and port
   - Upload to tag device

### 6. Testing the System
1. Start Basic Test:
   - Power up all anchors
   - Power up tag
   - Check Serial Monitor (115200 baud)
   - Verify distance measurements appear

2. Run Visualization:
   ```bash
   # Terminal 1: Start visualization
   python python/uwb_position_display.py

   # Optional - Terminal 2: Run simulator for testing
   python python/uwb_tag_simulator.py --movement circle
   ```

### 7. Troubleshooting Guide
Common Issues:
1. No distance readings:
   - Check power connections
   - Verify anchor IDs are unique
   - Ensure clear line of sight

2. Inaccurate positions:
   - Verify anchor positions match configuration
   - Check for interference sources
   - Ensure minimum 2 anchors are active

3. WiFi connection fails:
   - Verify WiFi credentials
   - Check network visibility
   - Ensure correct network settings

### 8. Operation Tips
- Keep tag antenna vertical for best results
- Avoid metal objects between devices
- Regular calibration recommended
- Monitor battery levels on portable units
- Keep firmware updated

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
