import sqlite3

con = sqlite3.connect("price_cache/tcgtracking_cache.sqlite")
cur = con.cursor()

for row in cur.execute("""
select name
from tcgtracking_sets
where lower(name) like '%trium%'
   or lower(name) like '%undaunt%'
   or lower(name) like '%unleash%'
order by name
"""):
    print(row[0])

con.close()