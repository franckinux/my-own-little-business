from itsdangerous import URLSafeTimedSerializer as Serializer


def generate_token(secret_key, **token):
    s = Serializer(secret_key)
    return s.dumps(token)


def get_token_data(token, secret_key, expiration=86400):
    s = Serializer(secret_key)
    return s.loads(token, max_age=expiration)
