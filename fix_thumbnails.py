import psycopg2

conn = psycopg2.connect("postgresql://neondb_owner:npg_TE0NKq7cybUL@ep-round-sky-axhqcmbx.c-4.us-east-2.aws.neon.tech/neondb?sslmode=require")
conn.autocommit = True
cur = conn.cursor()
cur.execute("UPDATE design_templates SET thumbnail_url = '/assets/Poster.png' WHERE name = 'Campaign Poster';")
cur.execute("UPDATE design_templates SET thumbnail_url = '/assets/poster2.png' WHERE name = 'Campaign Pamphlet';")
cur.execute("UPDATE design_templates SET thumbnail_url = '/assets/Id Card.png' WHERE name = 'Candidate ID Card';")
cur.execute("UPDATE design_templates SET thumbnail_url = '/assets/holdings.png' WHERE name = 'Campaign Banner';")
cur.execute("SELECT name, thumbnail_url FROM design_templates;")
print("Updated design_templates:", cur.fetchall())
cur.close()
conn.close()
