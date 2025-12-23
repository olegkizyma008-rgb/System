from __future__ import annotations


def test_chromadb_persistent_client_smoke(tmp_path):
    chroma_dir = tmp_path / "chroma"
    chroma_dir.mkdir(parents=True, exist_ok=True)

    import chromadb

    client = chromadb.PersistentClient(path=str(chroma_dir))
    col = client.get_or_create_collection("smoke")

    col.add(documents=["hello world"], ids=["1"], metadatas=[{"k": "v"}])
    res = col.query(query_texts=["hello"], n_results=1)

    assert res["ids"][0][0] == "1"
