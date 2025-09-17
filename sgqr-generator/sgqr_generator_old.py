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
        
        # 12. Additional Data Field Template (optional)
        if "additional_data" in config:
            additional_data = ""
            for field in config["additional_data"]:
                additional_data += self.encode_tlv(field["id"], field["value"])
            if additional_data:
                payload += self.encode_tlv("62", additional_data)
        
        # 13. Calculate and append CRC
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
    
    def get_field_name(self, tag: str, parent_tag: str = None) -> str:
        """
        Get human-readable name for a field ID
        
        Args:
            tag: The field ID
            parent_tag: Parent field ID for nested fields
            
        Returns:
            Human-readable field name
        """
        # Root level field names
        root_fields = {
            "00": "Payload Format Indicator",
            "01": "Point of Initiation Method",
            "02": "Visa",
            "04": "Mastercard", 
            "11": "American Express ID 11",
            "12": "American Express ID 12",
            "15": "UnionPay",
            "51": "Merchant Account Information",
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
            "64": "Merchant Information—Language Template"
        }
        
        # Payment system fields (26-50)
        if 26 <= int(tag) <= 50:
            if parent_tag is None:
                return "Merchant Account Information"
        
        # Nested field names
        if parent_tag == "51":  # SGQR ID sub-fields
            sgqr_fields = {
                "00": "Unique Identifier",
                "01": "SGQR ID Number",
                "02": "Version",
                "03": "Postal Code",
                "04": "Level Number",
                "05": "Unit Number",
                "06": "Miscellaneous",
                "07": "New Version Date"
            }
            return sgqr_fields.get(tag, "Payment network specific")
        
        # Payment system nested fields
        if parent_tag and 26 <= int(parent_tag) <= 50:
            payment_fields = {
                "00": "Globally Unique Identifier",
                "01": "Payment network specific",
                "02": "Payment network specific",
                "03": "Payment network specific",
                "04": "Payment network specific",
                "99": "Payment network specific"
            }
            return payment_fields.get(tag, "Payment network specific")
        
        # Additional data fields
        if parent_tag == "62":
            additional_fields = {
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
            return additional_fields.get(tag, "Payment System Specific")
        
        return root_fields.get(tag, "Unknown Field")
    
    def parse_payload(self, payload: str, parent_tag: str = None) -> List[Dict[str, Any]]:
        """
        Parse SGQR payload string back to structured format
        (Useful for validation and debugging)
        
        Args:
            payload: SGQR payload string
            parent_tag: Parent field ID for nested parsing
            
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
            
            # Store the parsed object with name
            obj = {
                "id": tag,
                "name": self.get_field_name(tag, parent_tag),
                "length": str(length).zfill(2),
                "value": value
            }
            
            # Add comment for specific fields
            if tag == "53":
                obj["comment"] = "3-digit numeric representation of currency according to ISO 4217. USD is 840, SGD is 702."
            elif tag == "52":
                obj["comment"] = "As defined by ISO 18245."
            elif tag == "58":
                obj["comment"] = "As defined by ISO 3166-1 alpha 2."
            elif tag == "63":
                obj["comment"] = "Shall be the last data object in QR code. Checksum calculated according to ISO/IEC 13239 using polynomial 1021 (hex) and initial value FFFF (hex)."
            elif tag == "00":
                obj["comment"] = "Shall be the 1st data object in QR code. Shall contain value of 01."
            elif tag == "01":
                obj["comment"] = "Value of 11 used when same QR code used for more than 1 transaction. Value of 12 used when a new QR code is shown for each transaction."
            
            # Parse nested objects for certain tags
            if tag in ["26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "37", "38", "39", "40", "41", "42", "43", "44", "45", "46", "47", "48", "49", "50"]:
                # Payment system fields - these contain nested TLV data
                obj["comment"] = "Templates reserved for additional payment networks."
                obj["dataObjects"] = self.parse_payload(value, tag)
            elif tag == "51":
                # SGQR ID field
                obj["comment"] = "The SGQR ID is used to identify each SGQR label and is fixed as Data Objects ID \"51\" and is only generated and modified by the SGQR Centralised Repository."
                obj["dataObjects"] = self.parse_payload(value, tag)
            elif tag == "62":
                # Additional data field
                obj["dataObjects"] = self.parse_payload(value, tag)
            
            result.append(obj)
            
            # Move to next object
            i = value_end
            
        return result


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
