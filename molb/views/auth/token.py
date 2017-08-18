from itsdangerous import TimedJSONWebSignatureSerializer as Serializer


def generate_token(secret_key, expiration=3600, **token):
    s = Serializer(secret_key, expiration)
    return s.dumps(token).decode("ascii")


def get_token_data(token, secret_key):
    s = Serializer(secret_key)
    return s.loads(token)
