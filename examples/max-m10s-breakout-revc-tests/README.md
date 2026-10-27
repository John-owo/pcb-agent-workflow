# MAX-M10S Rev C Bench Test Procedure

This is the **bench test record** for [max-m10s-breakout-revc](../max-m10s-breakout-revc/README.md): the power-up and functional test procedure, results and errata after the boards arrive. The example package itself is a release package and does not hold this content; for terminology see [CONTEXT.md](../../CONTEXT.md).

- **Status: not yet tested.** The boards are still in transit.
- **Results:** [results.md](results.md)
- **Errata:** none so far. Design problems found during testing will be listed at the bottom of this page, along with their fixes.

## Roles

- The physical boards, power supply and measurement instruments are operated only by one owner (the owner of the boards).
- The agent prepares the procedure, organizes the data the owner reports, and updates `results.md`; it does not operate hardware.

## Pass criteria

Each of the two assembled boards must **individually** complete steps 3–7 below for the bench test to pass. Steps 1 and 2 are prerequisites for power-up; if they fail, do not power up. Step 8 is optional.

| Step | Item | Pass |
|---|---|---|
| 3 | 3.3 V power-up | Current does not hit the current limit, no overheating, value within a reasonable range of the datasheet current table |
| 4 | UART | NMEA with correct checksums received at 9600 8N1, and UBX queries sent get a response |
| 5 | Outdoor fix | Obtains a 3D fix; all three TTFF values recorded (no threshold, for record and comparison only) |
| 6 | PPS | After fix, TP6 shows a 1 Hz pulse and the PPS LED blinks along with it |
| 7 | I2C | ACK at address 0x42, data can be read |

## Privacy

NMEA and UBX data after a fix contain **latitude and longitude**, i.e. the test location.

- Do not commit raw logs to the repo.
- `results.md` records only fix status, satellite count, max C/N0 and TTFF; describe the location only in terms like "open outdoor area".
- Keep screenshots only in a private folder on your own computer; do not commit them to the repo. Public records always use text descriptions.

## What you need

- Adjustable power supply that can be set to 3.3 V with a current limit
- Multimeter
- USB-UART adapter with 3.3 V logic (do not use a 5 V one)
- Passive GNSS antenna, 50 Ω, with a connector compatible with MHF I (I-PEX 20279)
- Optional: oscilloscope or logic analyzer (to measure PPS), a 3.3 V I2C host (e.g. a 3.3 V MCU dev board or USB-I2C adapter)
- Optional: u-center 2, or any serial terminal

## Assumptions for this board

Per the example README, keep these points in mind before testing:

- **3.3 V only.** Neither the supply nor the logic is 5 V tolerant.
- **The board does not power the antenna.** Use a passive antenna; an active antenna will not be powered either.
- **No backup supply** (V_BCKP unconnected). After every full power-down and power-up, the module has no saved ephemeris or time, so every TTFF you measure is a cold start TTFF.
- **A blinking PPS LED does not mean a fix.** Use NMEA to determine fix status.
- **No signal line may be live while the board is unpowered.** The USB-UART TX and the I2C host's pull-ups or outputs will all back-feed through the IO pins into the unpowered module. The MAX-M10S datasheet specifies that IO must not be driven while powered down, with a maximum input voltage of V_IO + 0.3 V; the example schematic also notes that host signals must be disconnected before removing GNSS power. So always: **connect GND first, power up the board, then connect signal lines; before any power-down, first unplug every signal line connected at the time.**
- Header pins, from the antenna end down:
  - J2: 3V3 / GND / TX / RX / PPS / EXTINT
  - J3: GND / SCL / SDA / RESET_N / SAFEBOOT_N / GND

## Steps

### 1. Visual inspection (unpowered)

- Check around U1, D1 (0.4 mm pitch, very small gap between the two pads) and J1 for solder bridges or misalignment.
- Check the orientation of D2, D3, Q1 and U1 against the example's `manufacturing/assembly-orientation.pdf`.
- J2 and J3 headers inserted from the board bottom and soldered on the top side, pin order as above.
- Record: any anomalies, which board, which designator.

### 2. Short-circuit check (unpowered)

- Measure the resistance from TP1 (3V3) to TP2 (GND) with the multimeter. C3 is 10 µF, so the reading will climb from low; as long as it does not stay near 0 Ω, it is not a short.
- Also measure 3V3 to TX, RX, SDA and SCL to confirm none is shorted directly to the supply.
- Record: the final settled reading.

### 3. First power-up

1. Set the supply to 3.3 V first, with a 100 mA current limit. This value is for protection, not a pass criterion.
2. Connect 3V3 and GND on J2, and **do not yet connect** any signal lines other than the antenna.
3. After power-up, watch the current and the PWR LED (D2). If the current hits the limit, power off immediately and go back to steps 1 and 2.
4. Wait 10 seconds and record the current; hold the back of your hand near U1 to confirm it is not noticeably hot.
5. Compare against the current table in the MAX-M10S datasheet (acquisition and tracking states). The two LEDs each have 2.2 kΩ in series, about 1 mA combined; nearly all the rest is the module itself.

### 4. UART

1. Power up the board as in step 3. Connect only GND of the USB-UART at first.
2. After confirming the board is powered, connect the signal lines: module TX (pin 3 of J2 counting from the antenna end) → adapter RX, module RX (pin 4) → adapter TX. Before connecting, check the pinout once more with the multimeter or schematic PDF.
3. Set the terminal to 9600 8N1. Within a few seconds you should see NMEA sentences starting with `$G...`.
4. Verify checksums: use u-center 2 (which flags checksum errors), or another tool that can check NMEA checksums. To compute by hand, XOR each character between `$` and `*`; the result must equal the two hex digits after `*`. No garbled characters on screen does not mean checksums are correct; if not verified, record "not verified".
5. Test the RX direction: send a UBX-MON-VER query with u-center 2; you should receive a version reply.
6. Record: sentence types seen, whether checksums verified (or "not verified"), whether MON-VER responded.
7. To power down, first unplug all signal lines (UART TX and RX, I2C SDA and SCL, and any other external signal lines; GND may stay connected), then turn off the supply.

### 5. Outdoor fix and TTFF

1. Connect the passive antenna and go outdoors to an open spot with a wide view of the sky.
2. First unplug all signal lines (UART TX and RX, I2C SDA and SCL, and any other external signal lines; GND may stay connected), then fully power down for at least 10 seconds. Power up and start timing; reconnect the signal lines after confirming the board is powered.
3. Time until the first 3D fix: GGA fix quality greater than 0, **and** GSA navMode equal to 3. RMC status A may also be a 2D fix and cannot be taken as a 3D fix.
4. Record: TTFF, number of satellites in use, max C/N0 in GSV.
5. Repeat 3 times per board.

Just compare TTFF with the datasheet cold start figure; it is not a pass threshold. The passive antenna, antenna placement and surrounding obstructions all affect the result, so record the antenna model and placement.

### 6. PPS

1. After a fix, measure TP6 (PPS) with an oscilloscope or logic analyzer.
2. Confirm it is 1 Hz and record the pulse width. The PPS LED (D3) should blink along with it.
3. Without an oscilloscope, at least confirm D3 blinks at 1 Hz after a fix, and note "visual only" in the record.

### 7. I2C

1. Power up the board first, and connect only GND of the I2C host at first. The host must use 3.3 V logic.
2. After confirming the board is powered, connect SDA and SCL to J3. The board already has 4.7 kΩ pull-ups (R4, R5); if the host also has pull-ups, confirm they go to 3.3 V.
3. Scan I2C; you should see an ACK at **0x42**.
4. Read registers 0xFD and 0xFE (number of bytes available, 0xFD is the high byte), then read the data stream from 0xFF; you should get NMEA or UBX content.
5. Record: whether ACK appears, the number of bytes read, whether the data parses.
6. To power down, first unplug all signal lines (UART TX and RX, I2C SDA and SCL, and any other external signal lines; GND may stay connected), then turn off the supply.

### 8. Control pins (optional)

- Briefly pull RESET_N low and release it; NMEA should stop and then restart.
- **Do not touch SAFEBOOT_N** unless you know what you want to do in safe boot mode.

## Errata

None so far.

When testing finds a design problem, list it here in order: symptom, which board, suspected cause, evidence, fix (e.g. part swap, jumper wire, or what to change in the next revision). The example package itself is not changed; a new version goes in a separate folder.
