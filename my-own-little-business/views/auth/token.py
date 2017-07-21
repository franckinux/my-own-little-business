from itsdangerous import TimedJSONWebSignatureSerializer as Serializer


def generate_confirmation_token(id_, secret_key, expiration=3600):
    s = Serializer(secret_key, expiration)
    return s.dumps({"confirm": id_}).decode("ascii")


def get_id_from_token(token, secret_key):
    s = Serializer(secret_key)
    data = s.loads(token)
    return data["confirm"]
