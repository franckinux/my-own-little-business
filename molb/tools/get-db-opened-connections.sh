#!/bin/bash
psql molb -c "SELECT COUNT(*) FROM pg_stat_activity WHERE client_addr = '127.0.0.1'"
