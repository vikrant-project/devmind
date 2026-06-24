from devmind.memory.embeddings import VectorStore
from devmind.memory.long_term import LongTermMemory
def test_tfidf_fallback(tmp_path):
    db = tmp_path/"m.db"; LongTermMemory(db).close()
    vs = VectorStore(db, router=None)
    vs.add("projects","p1","fastapi todo list with sqlite")
    vs.add("projects","p2","discord bot with slash commands")
    res = vs.search("fastapi todo", "projects")
    assert res and res[0]["id"] == "p1"
