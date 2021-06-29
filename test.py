import datetime
import sys
import time

from wallabag import Wallabag, Entry

wb = Wallabag(
    host="https://app.wallabag.it",
    username="riccardo2@pm.me",
    password="Hate-Glorify9-Sliced",
    client_id="14437_4a8sox90iy4gc440wo8sc04ss4c08s0kgwsgc8444w40kw4wsg",
    client_secret="5l0mm1c6ggkc4o0swwwcokggwg4kw4cs8wkgoog00g8888wwwg"
)

entry: Entry = wb.save_entry(
    url="https://www.fanpage.it/sport/calcio/la-uefa-dice-no-lallianz-arena-non-silluminera-con-i-colori-della-bandiera-arcobaleno/",
    tags=["wallabag bot"],
    published_at=datetime.datetime.now()
)
# wb.edit_entry(13260773, starred=False)
entry.pprint()
sys.exit(1)

wb.get_entries()


time.sleep(3610)

print("REFRESH")

wb.get_entries()

print("DONE")
