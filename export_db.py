import sqlite3
import pandas as pd

conn = sqlite3.connect("braveeve.db")

df = pd.read_sql_query(
    "SELECT * FROM responses",
    conn
)

df.to_csv(
    "braveeve_responses.csv",
    index=False
)

conn.close()