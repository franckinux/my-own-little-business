from sqlalchemy import and_ as sa_and
from sqlalchemy import not_ as sa_not
from sqlalchemy import func
from sqlalchemy.sql import select

from aiohttp_security.abc import AbstractAuthorizationPolicy
from passlib.hash import sha256_crypt

from model import Client


class DBAuthorizationPolicy(AbstractAuthorizationPolicy):
    def __init__(self, db_engine):
        self.db_engine = db_engine

    async def authorized_userid(self, identity):
        async with self.db_engine.acquire() as conn:
            where = sa_and(Client.__table__.c.login == identity,
                           sa_not(Client.__table__.c.disabled))
            query = select([func.count()]).select_from(Client.__table__).where(where).as_scalar()
            res = await conn.scalar(query)
            if res:
                return identity
            else:
                return None

    async def permits(self, identity, permission, context=None):
        if identity is None:
            return False

        async with self.db_engine.acquire() as conn:
            where = sa_and(Client.__table__.c.login == identity,
                           sa_not(Client.__table__.c.disabled))
            query = select([Client.__table__.c.super_user]).where(where)
            res = await conn.execute(query)
            client = await res.fetchone()
            if client is not None:
                if client.super_user:
                    return True
                if permission == "client":
                    return True
            return False


async def check_credentials(db_engine, username, password):
    async with db_engine.acquire() as conn:
        where = sa_and(Client.__table__.c.login == username,
                       sa_not(Client.__table__.c.disabled))
        query = select([Client.__table__.c.password_hash]).where(where)
        res = await conn.execute(query)
        client = await res.fetchone()
        if client is not None:
            hash_ = client.password_hash
            return sha256_crypt.verify(password, hash_)
    return False
