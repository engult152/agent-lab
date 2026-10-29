import main

main._load_vectors()
qv = main.emb_client.embeddings.create(model=main.EMB_MODEL, input=["工具跑不起来"]).data[0].embedding
print("段落数:", len(main._vectors))
for n, i, p, v in sorted(main._vectors, key=lambda x: -main._cos(qv, x[3])):
    print(round(main._cos(qv, v), 3), n, i, p[:50].replace(chr(10), " "))
