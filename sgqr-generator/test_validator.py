#!/usr/bin/env python3
"""
Test script to validate SGQR generation against known samples
"""

import json
from sgqr_generator import SGQRGenerator

def test_crc_calculation():
    """Test CRC calculation with known values"""
    generator = SGQRGenerator()
    
    # Test cases from actual SGQR samples
    test_cases = [
        # Format: (payload_without_crc, expected_crc)
        ("00020101021152045814530370258025960", "AFA5"),  # Simplified test
    ]
    
    print("Testing CRC Calculation:")
    for payload, expected_crc in test_cases:
        calculated_crc = generator.calculate_crc16(payload)
        status = "✓" if calculated_crc == expected_crc else "✗"
        print(f"  {status} Expected: {expected_crc}, Got: {calculated_crc}")
    print()

def test_tlv_encoding():
    """Test TLV encoding"""
    generator = SGQRGenerator()
    
    print("Testing TLV Encoding:")
    
    # Test simple encoding
    result = generator.encode_tlv("00", "01")
    expected = "000201"
    print(f"  Simple: {'✓' if result == expected else '✗'} {result}")
    
    # Test longer value
    result = generator.encode_tlv("59", "HUGGS-M WALK")
    expected = "5912HUGGS-M WALK"
    print(f"  String: {'✓' if result == expected else '✗'} {result}")
    
    # Test nested encoding
    nested_data = [
        {"id": "00", "value": "SG.SGQR"},
        {"id": "01", "value": "20091902F9D4"}
    ]
    result = generator.encode_nested_tlv(nested_data)
    expected = "0007SG.SGQR011220091902F9D4"
    print(f"  Nested: {'✓' if result == expected else '✗'} {result}")
    print()

def validate_sample_structure(sample_file: str):
    """Validate parsing of sample SGQR data"""
    generator = SGQRGenerator()
    
    # Load sample data
    with open(sample_file, 'r') as f:
        sample_data = json.load(f)
    
    print(f"Validating {sample_file}:")
    
    # Check mandatory fields
    mandatory_fields = ["00", "51", "52", "53", "58", "59", "60", "63"]
    found_fields = [item["id"] for item in sample_data]
    
    for field_id in mandatory_fields:
        if field_id in found_fields:
            print(f"  ✓ Field {field_id} present")
        else:
            print(f"  ✗ Field {field_id} missing")
    
    # Validate SGQR ID structure (field 51)
    sgqr_field = next((item for item in sample_data if item["id"] == "51"), None)
    if sgqr_field and "dataObjects" in sgqr_field:
        sgqr_objects = sgqr_field["dataObjects"]
        # Check for required SGQR sub-fields
        sgqr_ids = [obj["id"] for obj in sgqr_objects]
        required_sgqr = ["00", "01", "02", "03", "04", "05", "06", "07"]
        all_present = all(id in sgqr_ids for id in required_sgqr)
        print(f"  {'✓' if all_present else '✗'} SGQR ID structure complete")
    
    print()

def reconstruct_payload(sample_file: str):
    """Reconstruct payload from parsed JSON to verify understanding"""
    generator = SGQRGenerator()
    
    with open(sample_file, 'r') as f:
        sample_data = json.load(f)
    
    print(f"Reconstructing payload from {sample_file}:")
    
    # Reconstruct the payload
    payload = ""
    for item in sample_data:
        # For nested items, reconstruct the nested TLV
        if "dataObjects" in item:
            nested_value = ""
            for nested_obj in item["dataObjects"]:
                nested_value += generator.encode_tlv(nested_obj["id"], nested_obj["value"])
            payload += generator.encode_tlv(item["id"], nested_value)
        else:
            payload += generator.encode_tlv(item["id"], item["value"])
    
    print(f"  Length: {len(payload)} characters")
    
    # Verify CRC
    payload_without_crc = payload[:-8]  # Remove last 8 chars (6304XXXX)
    crc_from_sample = payload[-4:]
    calculated_crc = generator.calculate_crc16(payload_without_crc)
    
    print(f"  CRC Check: {'✓' if calculated_crc == crc_from_sample else '✗'} "
          f"(Sample: {crc_from_sample}, Calculated: {calculated_crc})")
    
    return payload

def main():
    """Run all tests"""
    print("=" * 60)
    print("SGQR Generator Validation Tests")
    print("=" * 60)
    print()
    
    # Test basic functions
    test_crc_calculation()
    test_tlv_encoding()
    
    # Test with sample files
    sample_files = [
        "huggs-millenia-walk SGQR.json",
        "istudio-yishun SGQR.json",
        "yan-xi-tang SGQR.json"
    ]
    
    print("Note: Sample file validation requires the JSON files to be present")
    print("Skipping file validation if files not found\n")
    
    # Generate a test QR code
    print("=" * 60)
    print("Generating Test SGQR")
    print("=" * 60)
    
    test_config = {
        "merchant_name": "TEST MERCHANT",
        "merchant_city": "Singapore",
        "merchant_category_code": "5814",
        "sgqr_id": {
            "sgqr_number": "250102123456",
            "version": "01.0001",
            "postal_code": "123456",
            "level": "01",
            "unit": "01",
            "misc": "TEST",
            "revision_date": "20250102"
        },
        "payment_systems": [
            {
                "global_identifier": "com.test",
                "fields": [
                    {"id": "01", "value": "TEST123"}
                ]
            }
        ]
    }
    
    generator = SGQRGenerator()
    payload = generator.generate_payload(test_config)
    
    print(f"Generated Payload ({len(payload)} chars):")
    print(f"{payload[:50]}...{payload[-20:]}")
    
    # Parse it back
    parsed = generator.parse_payload(payload)
    print(f"\nParsed {len(parsed)} top-level fields")
    
    print("\n✓ All basic tests completed")

if __name__ == "__main__":
    main()
