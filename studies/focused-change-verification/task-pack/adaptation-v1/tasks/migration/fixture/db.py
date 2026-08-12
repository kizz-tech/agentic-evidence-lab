import sqlite3


def create_v1(connection: sqlite3.Connection) -> None:
    connection.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, total INTEGER NOT NULL)")
    connection.execute("INSERT INTO orders (total) VALUES (100), (250)")
    connection.commit()

