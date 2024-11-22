#include "dw3000.h"

// WiFi Feature Flag - Uncomment to enable WiFi functionality
//#define ENABLE_WIFI

#ifdef ENABLE_WIFI
#include <WiFi.h>
#include <WiFiUdp.h>

/* WiFi Credentials */
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

/* UDP Broadcast Settings */
WiFiUDP udp;
const int UDP_PORT = 12345;  // Choose a UDP port
const IPAddress BROADCAST_IP(255, 255, 255, 255);  // Broadcast address
#endif

/* Position System Settings */
#define MAX_ANCHORS 10          // Maximum number of anchors to track
#define MIN_ANCHORS_TO_SEND 2   // Minimum anchors required for position calculation
#define ANCHOR_DATA_TIMEOUT 5000 // Timeout for anchor data in milliseconds
#define MAX_VALID_DISTANCE 8.0   // Maximum valid distance in meters
#define UDP_BROADCAST_INTERVAL 100 // Minimum interval between UDP broadcasts (ms)

/* Anchor Data Structure */
struct AnchorData {
    char id[2];        // Anchor ID (2 chars)
    double distance;   // Measured distance
    double tof;       // Time of flight
    unsigned long timestamp; // Last update timestamp
    bool active;      // Whether this anchor is active
};

/* Global Variables for Position System */
static AnchorData anchorArray[MAX_ANCHORS];
static int activeAnchors = 0;
static unsigned long lastBroadcastTime = 0;  // Last UDP broadcast timestamp

/* RX for Tag */
#define PAN_ID    (0xCA, 0xDE)
#define TAG_SRC   ('T', '1')
#define TAG_DST   ('A', 'L')

#define PIN_RST 27
#define PIN_IRQ 34
#define PIN_SS 4

#define RNG_DELAY_MS 1000
#define TX_ANT_DLY 16385
#define RX_ANT_DLY 16385
#define ALL_MSG_COMMON_LEN (5)
#define ALL_MSG_SN_IDX 2
#define RESP_MSG_SRC_IDX (5)
#define RESP_MSG_SRC_LEN (2)
#define RESP_MSG_DST_IDX (7)
#define RESP_MSG_DST_LEN (2)
#define RESP_MSG_POLL_RX_TS_IDX 10
#define RESP_MSG_RESP_TX_TS_IDX 14
#define RESP_MSG_TS_LEN 4
#define POLL_TX_TO_RESP_RX_DLY_UUS 240
#define RESP_RX_TIMEOUT_UUS 400

/* JSON buffer size */
#define JSON_BUFFER_SIZE 128

/* Default communication configuration. We use default non-STS DW mode. */
static dwt_config_t config = {
    5,                /* Channel number. */
    DWT_PLEN_128,     /* Preamble length. Used in TX only. */
    DWT_PAC8,         /* Preamble acquisition chunk size. Used in RX only. */
    9,                /* TX preamble code. Used in TX only. */
    9,                /* RX preamble code. Used in RX only. */
    1,                /* 0 to use standard 8 symbol SFD, 1 to use non-standard 8 symbol, 2 for non-standard 16 symbol SFD and 3 for 4z 8 symbol SDF type */
    DWT_BR_6M8,       /* Data rate. */
    DWT_PHRMODE_STD,  /* PHY header mode. */
    DWT_PHRRATE_STD,  /* PHY header rate. */
    (129 + 8 - 8),    /* SFD timeout (preamble length + 1 + SFD length - PAC size). Used in RX only. */
    DWT_STS_MODE_OFF, /* STS disabled */
    DWT_STS_LEN_64,   /* STS length see allowed values in Enum dwt_sts_lengths_e */
    DWT_PDOA_M0       /* PDOA mode off */
};

static uint8_t tx_poll_msg[] = {0x41, 0x88, 0, PAN_ID, TAG_SRC, TAG_DST, 0xE0, 0, 0};
static uint8_t rx_resp_msg[] = {0x41, 0x88, 0, PAN_ID, TAG_DST, TAG_SRC, 0xE1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
static uint8_t frame_seq_nb = 0;
static uint8_t rx_buffer[20];
static uint32_t status_reg = 0;
static double tof;
static double distance;
extern dwt_txconfig_t txconfig_options;

static bool isExpectedFrame(const uint8_t *frame, const uint32_t len);

void setup()
{
  UART_init();

#ifdef ENABLE_WIFI
  // Initialize WiFi
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("Connected to WiFi network with IP Address: ");
  Serial.println(WiFi.localIP());

  // Start UDP
  udp.begin(UDP_PORT);
#endif

  spiBegin(PIN_IRQ, PIN_RST);
  spiSelect(PIN_SS);

  delay(2); // Time needed for DW3000 to start up (transition from INIT_RC to IDLE_RC, or could wait for SPIRDY event)

  while (!dwt_checkidlerc()) // Need to make sure DW IC is in IDLE_RC before proceeding
  {
    UART_puts("IDLE FAILED\r\n");
    while (1)
      ;
  }

  if (dwt_initialise(DWT_DW_INIT) == DWT_ERROR)
  {
    UART_puts("INIT FAILED\r\n");
    while (1)
      ;
  }

  // Enabling LEDs here for debug so that for each TX the D1 LED will flash on DW3000 red eval-shield boards.
  dwt_setleds(DWT_LEDS_ENABLE | DWT_LEDS_INIT_BLINK);

  /* Configure DW IC. See NOTE 6 below. */
  if (dwt_configure(&config)) // if the dwt_configure returns DWT_ERROR either the PLL or RX calibration has failed the host should reset the device
  {
    UART_puts("CONFIG FAILED\r\n");
    while (1)
      ;
  }

  /* Configure the TX spectrum parameters (power, PG delay and PG count) */
  dwt_configuretxrf(&txconfig_options);

  /* Apply default antenna delay value. See NOTE 2 below. */
  dwt_setrxantennadelay(RX_ANT_DLY);
  dwt_settxantennadelay(TX_ANT_DLY);

  /* Set expected response's delay and timeout. See NOTE 1 and 5 below.
   * As this example only handles one incoming frame with always the same delay and timeout, those values can be set here once for all. */
  dwt_setrxaftertxdelay(POLL_TX_TO_RESP_RX_DLY_UUS);
  dwt_setrxtimeout(RESP_RX_TIMEOUT_UUS);

  /* Next can enable TX/RX states output on GPIOs 5 and 6 to help debug, and also TX/RX LEDs
   * Note, in real low power applications the LEDs should not be used. */
  dwt_setlnapamode(DWT_LNA_ENABLE | DWT_PA_ENABLE);

  Serial.println("Range RX");
  Serial.println("Setup over........");

  // Initialize anchor array
  for (int i = 0; i < MAX_ANCHORS; i++) {
    anchorArray[i].active = false;
  }
}

void loop()
{
  /* Write frame data to DW IC and prepare transmission. See NOTE 7 below. */
  tx_poll_msg[ALL_MSG_SN_IDX] = frame_seq_nb;
  dwt_write32bitreg(SYS_STATUS_ID, SYS_STATUS_TXFRS_BIT_MASK);
  dwt_writetxdata(sizeof(tx_poll_msg), tx_poll_msg, 0); /* Zero offset in TX buffer. */
  dwt_writetxfctrl(sizeof(tx_poll_msg), 0, 1);          /* Zero offset in TX buffer, ranging. */

  /* Start transmission, indicating that a response is expected so that reception is enabled automatically after the frame is sent and the delay
   * set by dwt_setrxaftertxdelay() has elapsed. */
  dwt_starttx(DWT_START_TX_IMMEDIATE | DWT_RESPONSE_EXPECTED);

  /* We assume that the transmission is achieved correctly, poll for reception of a frame or error/timeout. See NOTE 8 below. */
  while (!((status_reg = dwt_read32bitreg(SYS_STATUS_ID)) & (SYS_STATUS_RXFCG_BIT_MASK | SYS_STATUS_ALL_RX_TO | SYS_STATUS_ALL_RX_ERR)))
  {
  };

  /* Increment frame sequence number after transmission of the poll message (modulo 256). */
  frame_seq_nb++;

  if (status_reg & SYS_STATUS_RXFCG_BIT_MASK)
  {
    uint32_t frame_len;

    /* Clear good RX frame event in the DW IC status register. */
    dwt_write32bitreg(SYS_STATUS_ID, SYS_STATUS_RXFCG_BIT_MASK);

    /* A frame has been received, read it into the local buffer. */
    frame_len = dwt_read32bitreg(RX_FINFO_ID) & RXFLEN_MASK;
    if (frame_len <= sizeof(rx_buffer))
    {
      dwt_readrxdata(rx_buffer, frame_len, 0);

      /* Check that the frame is the expected response from the companion "SS TWR responder" example.
       * As the sequence number field of the frame is not relevant, it is cleared to simplify the validation of the frame. */
      rx_buffer[ALL_MSG_SN_IDX] = 0;
      if (isExpectedFrame(rx_buffer, frame_len))
      {
        uint32_t poll_tx_ts, resp_rx_ts, poll_rx_ts, resp_tx_ts;
        int32_t rtd_init, rtd_resp;
        float clockOffsetRatio;

        /* Retrieve poll transmission and response reception timestamps. See NOTE 9 below. */
        poll_tx_ts = dwt_readtxtimestamplo32();
        resp_rx_ts = dwt_readrxtimestamplo32();

        /* Read carrier integrator value and calculate clock offset ratio. See NOTE 11 below. */
        clockOffsetRatio = ((float)dwt_readclockoffset()) / (uint32_t)(1 << 26);

        /* Get timestamps embedded in response message. */
        resp_msg_get_ts(&rx_buffer[RESP_MSG_POLL_RX_TS_IDX], &poll_rx_ts);
        resp_msg_get_ts(&rx_buffer[RESP_MSG_RESP_TX_TS_IDX], &resp_tx_ts);

        /* Compute time of flight and distance, using clock offset ratio to correct for differing local and remote clock rates */
        rtd_init = resp_rx_ts - poll_tx_ts;
        rtd_resp = resp_tx_ts - poll_rx_ts;

        tof = ((rtd_init - rtd_resp * (1 - clockOffsetRatio)) / 2.0) * DWT_TIME_UNITS;
        distance = tof * SPEED_OF_LIGHT;
        char name[3] = { 0 };
        memcpy(name, rx_buffer + RESP_MSG_SRC_IDX, RESP_MSG_SRC_LEN);

        /* Display computed distance on LCD. */
        char dist_str[32];
        snprintf(dist_str, sizeof(dist_str), "A:%s, DIST: %3.2f m", name, distance);
        test_run_info((unsigned char *)dist_str);

        /* Update anchor data */
        updateAnchorData(name, distance, tof);

        /* Clean up invalid anchors */
        cleanupInvalidAnchors();

        /* If we have enough anchors, send position data */
        if (activeAnchors >= MIN_ANCHORS_TO_SEND) {
            char jsonBuffer[JSON_BUFFER_SIZE];
            formatPositionDataToJson(jsonBuffer, JSON_BUFFER_SIZE);
            Serial.println(jsonBuffer);  // Serial output without rate limiting
#ifdef ENABLE_WIFI
            broadcastUDP(jsonBuffer);    // UDP broadcast with rate limiting
#endif
        }
      }
    }
  }
  else
  {
    /* Clear RX error/timeout events in the DW IC status register. */
    dwt_write32bitreg(SYS_STATUS_ID, SYS_STATUS_ALL_RX_TO | SYS_STATUS_ALL_RX_ERR);
  }

  /* Execute a delay between ranging exchanges. */
  Sleep(RNG_DELAY_MS);
}

/* check PAN and DST ID */
static bool isExpectedFrame(const uint8_t *frame, const uint32_t len) {
    if (len < (RESP_MSG_DST_IDX +RESP_MSG_DST_LEN))
      return false;

    return ((memcmp(frame, rx_resp_msg, 5) == 0) &&
      (memcmp(frame + RESP_MSG_DST_IDX,
        rx_resp_msg + RESP_MSG_DST_IDX, RESP_MSG_DST_LEN) == 0)) ? true : false;
}

/* Function to convert all anchor data to JSON string */
void formatPositionDataToJson(char* jsonBuffer, size_t bufferSize) {
    // Start the JSON object with tag ID
    char tagId[3] = {TAG_SRC, 0};  // Convert TAG_SRC macro to string
    snprintf(jsonBuffer, bufferSize, "{\"tag\":\"%s\",\"anchors\":[", tagId);
    
    // Add each active anchor's data
    bool firstAnchor = true;
    for (int i = 0; i < MAX_ANCHORS; i++) {
        if (anchorArray[i].active) {
            // Check if the anchor data is still valid
            if (millis() - anchorArray[i].timestamp <= ANCHOR_DATA_TIMEOUT) {
                // Add comma if not first anchor
                if (!firstAnchor) {
                    strlcat(jsonBuffer, ",", bufferSize);
                }
                
                // Create anchor data JSON
                char anchorJson[64];
                snprintf(anchorJson, sizeof(anchorJson),
                        "{\"id\":\"%c%c\",\"distance\":%.2f,\"tof\":%.2f}",
                        anchorArray[i].id[0], anchorArray[i].id[1],
                        anchorArray[i].distance, anchorArray[i].tof);
                
                strlcat(jsonBuffer, anchorJson, bufferSize);
                firstAnchor = false;
            } else {
                // Mark inactive if timeout
                anchorArray[i].active = false;
                activeAnchors--;
            }
        }
    }
    
    // Close the JSON array and object
    strlcat(jsonBuffer, "]}", bufferSize);
}

/* Function to update anchor data */
void updateAnchorData(const char* anchorId, double distance, double tof) {
    // Check if distance is valid
    if (distance > MAX_VALID_DISTANCE) {
        Serial.printf("Anchor %c%c distance %.2f m exceeds maximum valid distance\n", 
                     anchorId[0], anchorId[1], distance);
        return;  // Skip updating if distance is too large
    }

    // Try to find existing anchor
    for (int i = 0; i < MAX_ANCHORS; i++) {
        if (anchorArray[i].active && 
            anchorArray[i].id[0] == anchorId[0] && 
            anchorArray[i].id[1] == anchorId[1]) {
            // Update existing anchor
            anchorArray[i].distance = distance;
            anchorArray[i].tof = tof;
            anchorArray[i].timestamp = millis();
            return;
        }
    }
    
    // Find empty slot for new anchor
    for (int i = 0; i < MAX_ANCHORS; i++) {
        if (!anchorArray[i].active) {
            // Add new anchor
            anchorArray[i].id[0] = anchorId[0];
            anchorArray[i].id[1] = anchorId[1];
            anchorArray[i].distance = distance;
            anchorArray[i].tof = tof;
            anchorArray[i].timestamp = millis();
            anchorArray[i].active = true;
            activeAnchors++;
            Serial.printf("New anchor %c%c added, distance: %.2f m\n", 
                         anchorId[0], anchorId[1], distance);
            return;
        }
    }
}

/* Function to check and remove invalid anchors */
void cleanupInvalidAnchors() {
    for (int i = 0; i < MAX_ANCHORS; i++) {
        if (anchorArray[i].active) {
            // Check timeout
            if (millis() - anchorArray[i].timestamp > ANCHOR_DATA_TIMEOUT) {
                Serial.printf("Anchor %c%c removed due to timeout\n", 
                            anchorArray[i].id[0], anchorArray[i].id[1]);
                anchorArray[i].active = false;
                activeAnchors--;
            }
            // Check distance
            else if (anchorArray[i].distance > MAX_VALID_DISTANCE) {
                Serial.printf("Anchor %c%c removed due to invalid distance: %.2f m\n", 
                            anchorArray[i].id[0], anchorArray[i].id[1], 
                            anchorArray[i].distance);
                anchorArray[i].active = false;
                activeAnchors--;
            }
        }
    }
}

/* Function to convert ranging data to JSON string */
void formatRangingDataToJson(char* jsonBuffer, size_t bufferSize, const char* anchorName, double distance, double tof) {
    snprintf(jsonBuffer, bufferSize,
             "{\"anchor\":\"%s\",\"distance\":%.2f,\"tof\":%.2f}",
             anchorName, distance, tof);
}

/* Function to broadcast UDP with rate limiting */
void broadcastUDP(const char* jsonData) {
#ifdef ENABLE_WIFI
    unsigned long currentTime = millis();
    if (WiFi.status() == WL_CONNECTED && 
        (currentTime - lastBroadcastTime >= UDP_BROADCAST_INTERVAL)) {
        udp.beginPacket(BROADCAST_IP, UDP_PORT);
        udp.write((const uint8_t*)jsonData, strlen(jsonData));
        udp.endPacket();
        lastBroadcastTime = currentTime;
    }
#endif
}
