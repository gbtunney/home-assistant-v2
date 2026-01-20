# ESP32 Bruce CYD 2432S028 — Raw Image‑Derived Product Spec

> **Source:** Itemized strictly from provided product screenshots and photos. No external assumptions.

---

## Product Identification

* **Product Name (as listed):** ESP32 Bruce CYD / ESP32 Bruce CYD 2432S028
* **Board Family / Ecosystem:** ESP32 Cheap Yellow Display (CYD)
* **Firmware (pre‑flashed):** ESP32‑Bruce v1.9.1
* **Primary Intent (per listing):**

  * Network / wireless security testing
  * ESP32 development & experimentation
  * Red‑team / penetration‑testing learning

---

## Core Compute

* **MCU:** ESP32‑WROOM‑32
* **Wireless Capabilities:**

  * Wi‑Fi
  * Bluetooth / BLE

---

## Display

* **Display Type:** TFT Touchscreen
* **Diagonal Size:** **2.8 inches**
* **Resolution:** 240 × 380 pixels
* **Driver IC:** ST7789
* **Touch Input:** Yes (touchscreen indicated in listing)

---

## Physical Dimensions (assembled, from annotated photo)

* **Overall Footprint:** ~85 mm × 60 mm
* **Overall Thickness:** ~14 mm
* **Enclosure:** Clear acrylic case, screw‑assembled

---

## Power & Connectivity

* **USB Ports:**

  * USB‑C
  * Micro‑USB

* **Power Sources Supported:**

  * Laptop USB port
  * Phone charger
  * Power bank

* **Battery:** Not included

---

## Storage

* **Micro‑SD / TF Card Slot:** Present
* **SD Card Included:** No
* **Operational Note:** Device functions without SD card, but data saving and some features require one

---

## On‑Board Interfaces & Components (as labeled in images)

* **Buttons:**

  * RESET
  * BOOT

* **Indicators & Output:**

  * RGB LED
  * Speaker / speaker connector

* **Connectors / Headers:**

  * Extended IO header
  * Temperature & humidity interface header
  * 4‑pin 1.25 mm power supply connector
  * SOP16 labeled footprint

---

## External Module Support (explicitly listed)

Supported via IO headers (modules not included):

* Sub‑GHz RF: CC1101
* NFC: PN532
* GPS: ATGM336H / NEO‑6M
* IR modules
* NRF24 modules
* Generic RF modules
* External speaker

---

## Firmware / Software Notes

* **Firmware Name:** ESP32‑Bruce
* **Project Repository:** [https://github.com/pr3y/Bruce](https://github.com/pr3y/Bruce)
* **Update File Mentioned:** `Bruce‑CYD‑2USB.bin`
* **Board Compatibility:** Cheap Yellow Display (CYD) ecosystem
* **Alternate Firmware Mentioned:** NMMiner (license referenced; not pre‑installed)

---

## Functional / Listing Notes

* Micro‑SD card required for saving work and enabling some features
* Development / learning board (explicitly stated)
* External RF / NFC / GPS modules not included

---

## Materials & Build

* **PCB Color:** Yellow (CYD standard)
* **Case Material:** Acrylic
* **Assembly:** Pre‑assembled

---

## Typical Application (as listed)

* Internet of Things (IoT)
* Wireless experimentation
* ESP32 development with integrated display
