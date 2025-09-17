# SGQR Generator Documentation

## Overview

This SGQR (Singapore QR Code for E-payments) generator creates payment QR codes following the EMV QR Code Specifications with Singapore-specific extensions as defined in SGQR Specifications Version 1.7.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```python
python sgqr_generator.py
```

The script will:

1. Read configuration from `sgqr_config.json`
2. Generate the SGQR payload string
3. Create a QR code image
4. Display the parsed structure for verification

## Configuration Structure

The JSON configuration file contains the following sections:

### Basic Merchant Information

- `merchant_name`: Business name (max 25 characters)
- `merchant_city`: City name (typically "Singapore")
- `merchant_postal_code`: 6-digit postal code
- `merchant_category_code`: ISO 18245 MCC code (e.g., "5814" for restaurants)
- `country_code`: ISO 3166-1 alpha-2 code ("SG" for Singapore)
- `currency`: ISO 4217 currency code ("702" for SGD)
- `initiation_method`: "11" for static QR, "12" for dynamic

### SGQR ID Components

Singapore-specific identifier containing:

- `sgqr_number`: Unique 12-character ID assigned by repository
- `version`: Format version (e.g., "01.0001")
- `postal_code`: Location postal code
- `level`: Floor level (e.g., "01", "B1")
- `unit`: Unit number
- `misc`: Terminal/counter ID
- `revision_date`: YYYYMMDD format

### Payment Systems

Array of payment system configurations, each containing:

- `name`: Display name (for reference)
- `global_identifier`: Unique identifier (reverse domain, AID, or UUID)
- `preferred_id`: Optional specific ID (26-50)
- `fields`: Array of system-specific fields with `id` and `value`

### Additional Data (Optional)

For bill payments and additional information:

- `id`: Field identifier (01-99)
- `value`: Field value

## Design Decisions & Assumptions

### 1. **TLV Encoding**

- All data follows Tag-Length-Value format
- Tags are 2 digits, lengths are 2 digits
- Nested TLV for complex structures (payment systems, SGQR ID)

### 2. **Payment System IDs**

- IDs 26-50 allocated on first-come basis
- Some systems can specify preferred IDs (e.g., PayNow uses 36)
- Automatic sequential assignment when not specified

### 3. **CRC Calculation**

- Uses ISO/IEC 13239 standard
- Polynomial: 0x1021, Initial value: 0xFFFF
- Always the last field (ID 63)

### 4. **Field Requirements**

- **Mandatory fields**: Format indicator, SGQR ID, MCC, currency, country, merchant name/city
- **Optional fields**: Postal code, transaction amount, additional data
- **Conditional fields**: Payment systems (at least one recommended)

### 5. **Data Validation**

- Length limits enforced per specification
- Character set: ASCII alphanumeric and special characters
- No Unicode support in base specification

### 6. **Default Values**

- Currency: SGD (702)
- Country: SG
- Initiation method: Static (11)
- MCC: 0000 (unspecified)

## Common Payment Systems

### NETS

```json
{
  "global_identifier": "SG.COM.NETS",
  "fields": [
    {"id": "01", "value": "QR metadata"},
    {"id": "02", "value": "Merchant ID"},
    {"id": "03", "value": "Terminal ID"},
    {"id": "99", "value": "Signature"}
  ]
}
```

### PayNow

```json
{
  "global_identifier": "SG.PAYNOW",
  "fields": [
    {"id": "01", "value": "0/1/2"},  // Proxy type
    {"id": "02", "value": "Proxy value"},
    {"id": "03", "value": "0/1"}  // Editable amount
  ]
}
```

### GrabPay

```json
{
  "global_identifier": "com.grab",
  "fields": [
    {"id": "01", "value": "Merchant ID"}
  ]
}
```

## Validation

To validate generated QR codes:

1. Compare with sample outputs in the test files
2. Use the `parse_payload()` method to verify structure
3. Scan with Singapore payment apps for end-to-end testing

## Limitations

1. **Static QR Only**: Dynamic QR with transaction-specific data requires backend integration
2. **No Encryption**: Payment credentials should use secure channels
3. **CRC Only**: No digital signatures in base implementation
4. **Size Limits**: QR payload should stay under 512 characters for reliable scanning

## Testing

The included sample files demonstrate:

- Multiple payment systems in single QR
- Proper TLV encoding
- Correct CRC calculation
- SGQR ID structure

## Error Handling

The generator includes:

- Length validation
- CRC verification
- TLV parsing validation
- Character set checking

## Security Notes

1. Never include sensitive payment credentials directly
2. Use HTTPS URLs for payment callbacks
3. Validate all merchant data before generation
4. Implement rate limiting for production use

## Compliance

This implementation follows:

- EMV QR Code Specifications (Merchant-Presented Mode) v1.0
- SGQR Specifications v1.7
- ISO standards: 18245 (MCC), 4217 (Currency), 3166-1 (Country)

## Support

For SGQR registration and compliance:

- Contact the SGQR Centralised Repository
- Refer to official MAS/IMDA documentation

// NETS
{"global_identifier": "SG.COM.NETS", "fields": [...]}

// PayNow  
{"global_identifier": "SG.PAYNOW", "fields": [...]}

// GrabPay
{"global_identifier": "com.grab", "fields": [...]}

// Alipay
{"global_identifier": "com.alipay", "fields": [...]}

// WeChat Pay
{"global_identifier": "COM.QQ.WEIXIN.PAY", "fields": [...]}

// Fave
{"global_identifier": "com.myfave", "fields": [...]}
