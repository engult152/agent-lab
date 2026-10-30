import main, store

try:
    for r in store._rows("SELECT owner, name, length(content) FROM files"):
        print(r)
finally:
    if store._client is not None:
        store._client.close()
