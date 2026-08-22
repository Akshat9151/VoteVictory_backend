import psycopg2
conn = psycopg2.connect('postgresql://neondb_owner:npg_TE0NKq7cybUL@ep-round-sky-axhqcmbx.c-4.us-east-2.aws.neon.tech/neondb?sslmode=require')
conn.autocommit = True
cur = conn.cursor()
cur.execute("DELETE FROM users WHERE email = 'bakshiakshat05@gmail.com';")
print("User cleared for fresh signup test!")
cur.close()
conn.close()
