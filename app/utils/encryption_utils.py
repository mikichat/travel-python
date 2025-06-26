from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv

load_dotenv()

def get_encryption_key():
    """환경 변수에서 암호화 키를 가져옵니다. 키가 없으면 새로 생성합니다."""
    key = os.getenv('ENCRYPTION_KEY')
    if key is None:
        key = Fernet.generate_key().decode()
        # 개발 환경에서 .env 파일에 저장하거나 사용자에게 출력하여 설정하도록 안내할 수 있습니다.
        print("경고: ENCRYPTION_KEY가 .env 파일에 설정되어 있지 않습니다. 새로운 키가 생성되었습니다. 이 키를 .env 파일에 추가하세요:")
        print(f"ENCRYPTION_KEY={key}")
        # 실제 배포 환경에서는 이 방식으로 키를 생성하고 저장해서는 안 됩니다.
        # 안전한 키 관리 시스템(예: AWS KMS, Azure Key Vault)을 사용해야 합니다.
    return key.encode()

_cipher_suite = None

def _get_cipher_suite():
    global _cipher_suite
    if _cipher_suite is None:
        key = get_encryption_key()
        _cipher_suite = Fernet(key)
    return _cipher_suite

def encrypt_data(data):
    """데이터를 암호화합니다."""
    if not data:
        return None
    cipher_suite = _get_cipher_suite()
    # 문자열을 바이트로 인코딩하여 암호화
    encrypted_data = cipher_suite.encrypt(data.encode('utf-8'))
    return encrypted_data.decode('utf-8')  # 다시 문자열로 디코딩하여 저장

def decrypt_data(encrypted_data):
    """암호화된 데이터를 복호화합니다."""
    if not encrypted_data:
        return None
    cipher_suite = _get_cipher_suite()
    try:
        # 문자열을 바이트로 인코딩하여 복호화
        decrypted_data = cipher_suite.decrypt(encrypted_data.encode('utf-8'))
        return decrypted_data.decode('utf-8')  # 바이트를 문자열로 디코딩
    except Exception as e:
        print(f"복호화 오류: {e}")
        return None 