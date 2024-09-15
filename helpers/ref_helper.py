import uuid
import base64

def generate_referral_token(user_id):
    user_id_str = str(user_id)
    token_uuid = str(uuid.uuid4())
    base64_user_id = base64.urlsafe_b64encode(user_id_str.encode('utf-8')).decode('utf-8')
    return f"{token_uuid}{base64_user_id}"


def generate_referral_link(user_id):
    referral_token = generate_referral_token(user_id)
    ref_link = f"https://t.me/WeatherGuesser_bot?start={referral_token}"
    return ref_link

def decode_user_id_from_token(referral_token):
    try:
        token_uuid = referral_token[:36]  # First 36 characters for UUID
        base64_user_id = referral_token[36:]  # The rest is the Base64-encoded user ID
        user_id = base64.urlsafe_b64decode(base64_user_id).decode('utf-8')
        return user_id
    except (ValueError, base64.binascii.Error) as e:
        print(f"Error decoding referral token: {e}")
        return None

