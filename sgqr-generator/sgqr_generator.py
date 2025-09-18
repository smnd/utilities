#!/usr/bin/env python3
"""
SGQR (Singapore QR Code for E-payments) Generator
Based on SGQR Specifications Version 1.7
"""

import json
import qrcode
from typing import Dict, List, Optional, Any
from datetime import datetime
import binascii

class SGQRGenerator:
    """
    Generates SGQR codes following EMV QR Code Specifications
    with Singapore-specific extensions
    """
    
    TOP_LEVEL_TAG_NAMES = {
        "00": "Payload Format Indicator",
        "01": "Point of Initiation Method",
        "51": "SGQR ID",
        "52": "Merchant Category Code",
        "53": "Transaction Currency",
        "54": "Transaction Amount",
        "55": "Tip or Convenience Indicator",
        "56": "Value of Convenience Fee Fixed",
        "57": "Value of Convenience Fee Percentage",
        "58": "Country Code",
        "59": "Merchant Name",
        "60": "Merchant City",
        "61": "Postal Code",
        "62": "Additional Data Field Template",
        "63": "CRC",
        "64": "Merchant Information - Language Template"
    }

    MERCHANT_ACCOUNT_TAGS = {f"{i:02d}" for i in range(26, 46)}

    SGQR_ID_SUBTAG_NAMES = {
        "00": "SGQR Globally Unique Identifier",
        "01": "SGQR ID Number",
        "02": "SGQR Version",
        "03": "Merchant Postal Code",
        "04": "Merchant Level",
        "05": "Merchant Unit",
        "06": "Miscellaneous",
        "07": "Revision Date"
    }

    ADDITIONAL_DATA_SUBTAG_NAMES = {
        "01": "Bill Number",
        "02": "Mobile Number",
        "03": "Store Label",
        "04": "Loyalty Number",
        "05": "Reference Label",
        "06": "Customer Label",
        "07": "Terminal Label",
        "08": "Purpose of Transaction",
        "09": "Additional Consumer Data Request"
    }

    MERCHANT_LANGUAGE_SUBTAG_NAMES = {
        "00": "Language Preference",
        "01": "Merchant Name - Alternate Language",
        "02": "Merchant City - Alternate Language"
    }

    # CRC parameters for ISO/IEC 13239
    CRC_POLYNOMIAL = 0x1021
    CRC_INIT_VALUE = 0xFFFF
    
    def __init__(self):
        """Initialize the SGQR generator"""
        self.payload = ""
        
    def encode_tlv(self, tag: str, value: str) -> str:
        """
        Encode data in TLV (Tag-Length-Value) format
        
        Args:
            tag: 2-digit tag identifier
            value: The value to encode
            
        Returns:
            Encoded string in format: tag + length + value
        """
        # Ensure tag is 2 digits
        tag = str(tag).zfill(2)
        
        # Calculate length (must be 2 digits)
        length = str(len(value)).zfill(2)
        
        return f"{tag}{length}{value}"
    
    def encode_nested_tlv(self, data_objects: List[Dict[str, str]]) -> str:
        """
        Encode nested data objects for merchant account information
        
        Args:
            data_objects: List of dictionaries with 'id' and 'value' keys
            
        Returns:
            Concatenated TLV encoded string
        """
        result = ""
        for obj in data_objects:
            result += self.encode_tlv(obj['id'], obj['value'])
        return result
    
    def calculate_crc16(self, data: str) -> str:
        """
        Calculate CRC-16 checksum using ISO/IEC 13239
        
        Args:
            data: The payload string (without CRC field)
            
        Returns:
            4-character hexadecimal CRC value (uppercase)
        """
        # Add placeholder for CRC field (6304 means ID=63, Length=04)
        data_with_crc_placeholder = data + "6304"
        
        # Convert string to bytes
        bytes_data = data_with_crc_placeholder.encode('ascii')
        
        # Calculate CRC-16
        crc = self.CRC_INIT_VALUE
        
        for byte in bytes_data:
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ self.CRC_POLYNOMIAL
                else:
                    crc = crc << 1
                crc &= 0xFFFF
                
        # Format as 4-digit uppercase hex
        return format(crc, '04X')
    
    def generate_sgqr_id(self, sgqr_config: Dict[str, Any]) -> str:
        """
        Generate the SGQR ID field (ID "51")
        
        Args:
            sgqr_config: Configuration for SGQR ID components
            
        Returns:
            Encoded SGQR ID field value
        """
        # Build nested data objects for SGQR ID
        data_objects = [
            {"id": "00", "value": "SG.SGQR"},  # Fixed identifier
            {"id": "01", "value": sgqr_config.get("sgqr_number", "250626348124")},  # SGQR number
            {"id": "02", "value": sgqr_config.get("version", "01.0001")},  # Version
            {"id": "03", "value": sgqr_config.get("postal_code", "000000")},  # Postal code
            {"id": "04", "value": sgqr_config.get("level", "01")},  # Floor level
            {"id": "05", "value": sgqr_config.get("unit", "001")},  # Unit number
            {"id": "06", "value": sgqr_config.get("misc", "0000")},  # Miscellaneous
            {"id": "07", "value": sgqr_config.get("revision_date", datetime.now().strftime("%Y%m%d"))}  # Revision date
        ]
        
        return self.encode_nested_tlv(data_objects)
    
    def generate_payment_system(self, payment_system: Dict[str, Any]) -> str:
        """
        Generate payment system merchant account information
        
        Args:
            payment_system: Configuration for a payment system
            
        Returns:
            Encoded payment system data
        """
        data_objects = []
        
        # print(f"Generating payment system: {payment_system}") # Debug statement
        
        # Global Unique Identifier (required)
        data_objects.append({
            "id": "00",
            "value": payment_system["global_identifier"]
        })
        
        # Add additional payment-specific fields
        for field in payment_system.get("fields", []):
            data_objects.append({
                "id": field["id"],
                "value": field["value"]
            })
        
        return self.encode_nested_tlv(data_objects)
    
    def generate_payload(self, config: Dict[str, Any]) -> str:
        """
        Generate the complete SGQR payload string
        
        Args:
            config: Complete configuration dictionary
            
        Returns:
            Complete SGQR payload string with CRC
        """
        payload = ""
        
        # 1. Payload Format Indicator (mandatory, always "01")
        payload += self.encode_tlv("00", "01")
        
        # 2. Point of Initiation Method (11 = static, 12 = dynamic)
        initiation_method = config.get("initiation_method", "11")
        payload += self.encode_tlv("01", initiation_method)
        
        # 3. Payment Systems (IDs 26-50)
        # Process payment systems in order, assigning IDs starting from 26
        next_payment_id = 26
        
        # Handle specific payment systems that might use reserved IDs
        for payment_system in config.get("payment_systems", []):
            # Some systems might specify their preferred ID
            payment_id = payment_system.get("preferred_id", str(next_payment_id))
            
            # Generate the payment system data
            payment_data = self.generate_payment_system(payment_system)
            
            # Add to payload
            payload += self.encode_tlv(payment_id, payment_data)
            
            # Increment for next system (skip if specific ID was used)
            if payment_id == str(next_payment_id):
                next_payment_id += 1
        
        # 4. SGQR ID (ID "51" - mandatory for SGQR)
        sgqr_id_data = self.generate_sgqr_id(config.get("sgqr_id", {}))
        payload += self.encode_tlv("51", sgqr_id_data)
        
        # 5. Merchant Category Code (mandatory)
        mcc = config.get("merchant_category_code", "0000")
        payload += self.encode_tlv("52", mcc)
        
        # 6. Transaction Currency (mandatory, 702 = SGD)
        currency = config.get("currency", "702")
        payload += self.encode_tlv("53", currency)
        
        # 7. Transaction Amount (optional)
        if "amount" in config:
            payload += self.encode_tlv("54", config["amount"])
        
        # 8. Country Code (mandatory, SG for Singapore)
        country = config.get("country_code", "SG")
        payload += self.encode_tlv("58", country)
        
        # 9. Merchant Name (mandatory)
        merchant_name = config.get("merchant_name", "MERCHANT")
        payload += self.encode_tlv("59", merchant_name)
        
        # 10. Merchant City (mandatory)
        merchant_city = config.get("merchant_city", "Singapore")
        payload += self.encode_tlv("60", merchant_city)
        
        # 11. Postal Code (optional)
        if "merchant_postal_code" in config:
            payload += self.encode_tlv("61", config["merchant_postal_code"])
        
        # 12. Additional Data Field Template (optional, IDs 01-09)
        additional_data_config = config.get("additional_data")
        valid_additional_data_ids = {f"{i:02d}" for i in range(1, 10)}
        additional_data_value = ""

        if isinstance(additional_data_config, dict):
            for field_id in sorted(additional_data_config.keys()):
                normalized_id = str(field_id).zfill(2)
                if normalized_id not in valid_additional_data_ids:
                    continue
                field_value = additional_data_config[field_id]
                if field_value is None or field_value == "":
                    continue
                additional_data_value += self.encode_tlv(normalized_id, str(field_value))
        elif isinstance(additional_data_config, list):
            for field in additional_data_config:
                field_id = str(field.get("id", "")).zfill(2)
                if field_id not in valid_additional_data_ids:
                    continue
                field_value = field.get("value")
                if field_value is None or field_value == "":
                    continue
                additional_data_value += self.encode_tlv(field_id, str(field_value))

        if additional_data_value:
            payload += self.encode_tlv("62", additional_data_value)

        # 13. Merchant Information - Language Template (ID "64")
        merchant_language_objects = [
            {"id": "00", "value": "EN"},
            {"id": "01", "value": config.get("merchant_name", "MERCHANT")}
        ]
        payload += self.encode_tlv("64", self.encode_nested_tlv(merchant_language_objects))

        # 14. Calculate and append CRC
        crc = self.calculate_crc16(payload)
        payload += self.encode_tlv("63", crc)
        
        return payload
    
    def generate_qr_code(self, payload: str, output_file: str = "sgqr.png"):
        """
        Generate QR code image from payload
        
        Args:
            payload: SGQR payload string
            output_file: Output filename for QR code image
        """
        qr = qrcode.QRCode(
            version=None,  # Let it auto-determine size
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        
        qr.add_data(payload)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(output_file)
        
        return output_file
    
    def parse_payload(self, payload: str, parent_tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Parse SGQR payload string back to structured format
        (Useful for validation and debugging)
        
        Args:
            payload: SGQR payload string
            parent_tag: Optional tag of the parent structure for context
            
        Returns:
            List of parsed data objects
        """
        result = []
        i = 0
        
        while i < len(payload):
            if i + 4 > len(payload):
                break
                
            # Extract tag and length
            tag = payload[i:i+2]
            length = int(payload[i+2:i+4])
            
            # Extract value
            value_start = i + 4
            value_end = value_start + length
            
            if value_end > len(payload):
                break
                
            value = payload[value_start:value_end]
            
            # Store the parsed object
            obj = {
                "id": tag,
                "name": self.get_tag_name(tag, parent_tag),
                "length": str(length).zfill(2),
                "value": value
            }
            
            # Parse nested objects for certain tags
            if tag in self.MERCHANT_ACCOUNT_TAGS or tag in {"51", "62", "64"}:
                # These contain nested TLV data
                obj["dataObjects"] = self.parse_payload(value, parent_tag=tag)
            
            result.append(obj)
            
            # Move to next object
            i = value_end
            
        return result

    def get_tag_name(self, tag: str, parent_tag: Optional[str] = None) -> str:
        """Return descriptive name for a tag using context-specific mappings."""
        if parent_tag is None:
            if tag in self.TOP_LEVEL_TAG_NAMES:
                return self.TOP_LEVEL_TAG_NAMES[tag]
            if tag in self.MERCHANT_ACCOUNT_TAGS:
                return f"Merchant Account Information ({tag})"
            return f"Unknown Tag {tag}"

        if parent_tag in self.MERCHANT_ACCOUNT_TAGS:
            if tag == "00":
                return "Global Unique Identifier"
            return f"Payment System Specific Data ({tag})"

        if parent_tag == "51":
            return self.SGQR_ID_SUBTAG_NAMES.get(tag, f"SGQR ID Data ({tag})")

        if parent_tag == "62":
            return self.ADDITIONAL_DATA_SUBTAG_NAMES.get(tag, f"Additional Data ({tag})")

        if parent_tag == "64":
            return self.MERCHANT_LANGUAGE_SUBTAG_NAMES.get(tag, f"Merchant Information - Language ({tag})")

        return self.TOP_LEVEL_TAG_NAMES.get(tag, f"Unknown Tag {tag}")


def main():
    """Main function to demonstrate SGQR generation"""
    
    # Load configuration from JSON file
    with open("sgqr_config.json", "r") as f:
        config = json.load(f)
    
    # Create generator instance
    generator = SGQRGenerator()
    
    # Generate payload
    payload = generator.generate_payload(config)
    
    print(f"Generated SGQR Payload:")
    print(f"{payload}")
    print(f"\nPayload Length: {len(payload)} characters")
    
    # Generate QR code
    output_file = config.get("output_file", "sgqr.png")
    generator.generate_qr_code(payload, output_file)
    print(f"\nQR Code saved to: {output_file}")
    
    # Parse and display the payload structure
    print(f"\nParsed Structure:")
    parsed = generator.parse_payload(payload)
    print(json.dumps(parsed, indent=2))
    
    return payload


if __name__ == "__main__":
    main()
