import base64
from app.core.encryption import (
    encrypt_field,
    decrypt_field,
    EncryptionError,
)


def test_encrypt_decrypt_roundtrip():
    print("\n=== TEST 1: Encrypt / Decrypt Roundtrip ===")
    sensitive_memory = "User secret context: Personal preference is high-level summary only."
    print(f"Original Plaintext: '{sensitive_memory}'")

    ciphertext_b64 = encrypt_field(sensitive_memory)
    print(f"Encrypted Ciphertext (B64 len={len(ciphertext_b64)}): '{ciphertext_b64[:40]}...'")

    # Ensure plaintext is not visible in ciphertext string
    assert sensitive_memory not in ciphertext_b64
    assert "User secret context" not in ciphertext_b64

    decrypted = decrypt_field(ciphertext_b64)
    print(f"Decrypted Plaintext: '{decrypted}'")
    assert decrypted == sensitive_memory
    print("[OK] Roundtrip encryption/decryption PASSED!")


def test_nonce_uniqueness():
    print("\n=== TEST 2: IV/Nonce Uniqueness ===")
    same_text = "Identical secret string"
    cipher_1 = encrypt_field(same_text)
    cipher_2 = encrypt_field(same_text)

    print(f"Ciphertext 1: {cipher_1[:30]}...")
    print(f"Ciphertext 2: {cipher_2[:30]}...")
    assert cipher_1 != cipher_2, (
        "Random IV must produce distinct ciphertexts for identical plaintext"
    )
    assert decrypt_field(cipher_1) == same_text
    assert decrypt_field(cipher_2) == same_text
    print("[OK] Nonce uniqueness PASSED!")


def test_tampered_ciphertext_fails():
    print("\n=== TEST 3: Tampered Ciphertext Failure (GCM Auth Tag Verification) ===")
    original_text = "Sensitive financial bank data payload"
    ciphertext_b64 = encrypt_field(original_text)

    # Decode bytes, mutate 1 byte, re-encode
    raw_bytes = bytearray(base64.b64decode(ciphertext_b64))
    raw_bytes[-1] ^= 0xFF  # Flip bits in authentication tag
    tampered_b64 = base64.b64encode(bytes(raw_bytes)).decode("utf-8")

    try:
        decrypt_field(tampered_b64)
        assert False, "Expected EncryptionError was NOT raised for tampered payload!"
    except EncryptionError as e:
        print(f"[OK] Caught EncryptionError on tampered payload as expected: '{e}'")
        assert "tampered" in str(e).lower() or "decryption failed" in str(e).lower()


def test_invalid_or_short_payload():
    print("\n=== TEST 4: Invalid or Truncated Payload ===")
    invalid_b64 = "short_invalid_data"

    try:
        decrypt_field(invalid_b64)
        assert False, "Expected EncryptionError was NOT raised for truncated payload!"
    except EncryptionError as e:
        print(f"[OK] Caught EncryptionError on truncated payload as expected: '{e}'")


def main():
    test_encrypt_decrypt_roundtrip()
    test_nonce_uniqueness()
    test_tampered_ciphertext_fails()
    test_invalid_or_short_payload()
    print("\n==========================================")
    print(" ALL AES-256-GCM ENCRYPTION TESTS PASSED! ")
    print("==========================================")


if __name__ == "__main__":
    main()
