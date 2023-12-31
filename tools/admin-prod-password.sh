#!/bin/sh
psql molb -c "UPDATE client SET password_hash = '\$5\$rounds=535000\$XIxMCiAt.LsUh2.g\$FUesK3jqrRJni7IsPS6aunC60ZDsv3fiN9rsruc0jT9' WHERE login = 'admin'"
