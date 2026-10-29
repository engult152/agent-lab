import main

main._load_vectors()
for q in ["墓地 耳环 白雾 装置 凭依技", "麻痹 追踪弹 光球 爱情 二阶段"]:
    qv = main.emb_client.embeddings.create(model=main.EMB_MODEL, input=[q]).data[0].embedding
    r = sorted(main._vectors, key=lambda v: -main._cos(qv, v[3]))
    print("==", q)
    for n, i, p, v in r[:5]:
        print("  ", round(main._cos(qv, v), 3), n, i, p[:50].replace("\n", " "))
