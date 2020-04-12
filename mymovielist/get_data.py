import sqlite3
import pickle

conn = sqlite3.connect('site.db')
c = conn.cursor()

c.execute('SELECT * FROM movies')
data = c.fetchall()
for row in data:
    print(f"User {row[5]}")
    if row[1] is not None:
        print(f"    {pickle.loads(row[1])}")
    else:
        print(f"    {row[1]}")
    if row[2] is not None:
        print(f"    {pickle.loads(row[2])}")
    else:
        print(f"    {row[2]}")
    if row[3] is not None:
        print(f"    {pickle.loads(row[3])}")
    else:
        print(f"    {row[3]}")
    if row[4] is not None:
        print(f"    {pickle.loads(row[4])}")
    else:
        print(f"{row[0]} -> {row[4]}")
c.close
conn.close()