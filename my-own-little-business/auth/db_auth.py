from aiohttp_security.abc import AbstractAuthorizationPolicy
from passlib.hash import sha256_crypt


class DBAuthorizationPolicy(AbstractAuthorizationPolicy):
    def __init__(self, db_pool):
        self.db_pool = db_pool

    async def authorized_userid(self, identity):
        async with self.db_pool.acquire() as conn:
            q = "SELECT COUNT(*) FROM client WHERE login = $1 AND confirmed AND NOT disabled"
            res = await conn.fetchval(q, identity, column=0)
            if res:
                return identity
            else:
                return None

    async def permits(self, identity, permission, context=None):
        if identity is None:
            return False

        async with self.db_pool.acquire() as conn:
            q = "SELECT super_user FROM client WHERE login = $1 AND confirmed AND NOT disabled"
            client = await conn.fetchrow(q, identity)
            if client is not None:
                if client["super_user"]:
                    return True
                if permission == "client":
                    return True
            return False


async def check_credentials(db_pool, username, password):
    async with db_pool.acquire() as conn:
        q = "SELECT password_hash FROM client WHERE login = $1 AND confirmed AND NOT disabled"
        client = await conn.fetchrow(q, username)
    if client is not None:
        hash_ = client["password_hash"]
        return sha256_crypt.verify(password, hash_)
    return False
