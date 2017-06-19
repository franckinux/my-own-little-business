import os
import sys

from sqlalchemy import create_engine
import sqlalchemy as sa
from sqlalchemy.engine.url import URL

from model import Base
from utils import read_configuration_file


if __name__ == "__main__":
    config = read_configuration_file()
    if not config:
        sys.exit(1)
    config = config["database"]
    config["password"] = os.getenv("PG_PASS", "") or config["password"]

    connection_infos = {
        "drivername": "postgres",
        "host": config["host"],
        "port": config["port"],
        "username": config["username"],
        "password": config["password"],
        "database": config["database"]
    }
    dsn = str(URL(**connection_infos))

    engine = create_engine(dsn, echo=True)
    try:
        Base.metadata.create_all(engine)
    except:
        sys.stderr.write("cannot connect to database\n")
        sys.exit(2)
    finally:
        engine.dispose()
