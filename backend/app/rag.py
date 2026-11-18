import hashlib
import math
import re
import threading

import chromadb
from sqlalchemy.orm import Session

from .config import settings
from .models import KBArticle

STOP = set("""a an the is are was were be to of and or in on at for it its this that with from by as my your our
i me you we they he she do does did can could would should will not no yes please pls help po ba ang ng sa ko mo ka mga what how why who when where keep long much many redacted card charged working works problem problems issue issues unable cant won doesn isn
yung ung na lang ay at ako namin natin kasi pero daw raw naman din rin may meron walang hindi di get got""".split())

GLOSSARY = {
    "nalock": "locked account unlock failed login",
    "naka-lock": "locked account unlock failed login",
    "nakalock": "locked account unlock failed login",
    "na-lock": "locked account unlock failed login",
    "lock": "locked account unlock",
    "locked": "locked account unlock failed login",
    "lockout": "locked account unlock failed login",
    "nakalimutan": "forgot password reset",
    "forgot": "forgot password reset",
    "expired": "password reset expire",
    "bagal": "slow frozen",
    "mabagal": "slow frozen",
    "lag": "slow frozen",
    "laggy": "slow frozen",
    "freeze": "slow frozen",
    "hang": "slow frozen",
    "tunog": "audio sound",
    "sound": "audio sound",
    "mic": "microphone audio headset",
    "microphone": "microphone audio headset",
    "nanakaw": "stolen lost laptop",
    "ninakaw": "stolen lost laptop",
    "nawala": "lost laptop",
    "stolen": "stolen lost laptop",
    "tawag": "calls call",
    "naputol": "dropping calls",
    "putol": "dropping calls",
    "internet": "internet wifi home network",
    "wifi": "internet wifi home network",
    "wfh": "work home internet network",
    "disconnect": "disconnect reconnect gateway",
    "disconnects": "disconnect reconnect gateway",
    "disconnecting": "disconnect reconnect gateway",
    "speed": "mbps bandwidth download upload",
    "required": "requirements minimum",
    "requirements": "requirements minimum",
    "pass": "password",
    "login": "login sign password",
    "mfa": "mfa authenticator prompt",
    "otp": "mfa authenticator code",
}

_lock = threading.Lock()
_client = None


def tokens(text: str):
    raw = re.findall(r"[a-z0-9][a-z0-9\-\.]*", text.lower())
    out = []
    for t in raw:
        t = t.strip("-.")
        if not t or t in STOP:
            continue
        out.append(t)
        if len(t) > 4 and t.endswith("s") and not t.endswith("ss"):
            out.append(t[:-1])
        if t.endswith("ing") and len(t) > 5:
            out.append(t[:-3])
    return out


def expand(text: str):
    base = tokens(text)
    extra = []
    for t in base:
        if t in GLOSSARY:
            extra.extend(tokens(GLOSSARY[t]))
    return base + extra


def hash_embed(text: str, dim: int = 256):
    vec = [0.0] * dim
    toks = tokens(text)
    grams = toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]
    for g in grams:
        h = int(hashlib.md5(g.encode()).hexdigest(), 16)
        vec[h % dim] += 1.0 if (h >> 20) % 2 == 0 else -1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def backend_name():
    return "openai" if settings.openai_api_key else "local"


def embed(texts):
    if settings.openai_api_key:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=settings.openai_api_key)
            res = client.embeddings.create(model=settings.embedding_model, input=texts)
            return [d.embedding for d in res.data]
        except Exception:
            pass
    return [hash_embed(t) for t in texts]


def collection():
    global _client
    with _lock:
        if _client is None:
            _client = chromadb.PersistentClient(path=settings.chroma_path)
        return _client.get_or_create_collection(f"kb_{backend_name()}", metadata={"hnsw:space": "cosine"})


def split_sections(body: str):
    parts = re.split(r"^## +(.+)$", body, flags=re.M)
    sections = []
    if parts[0].strip():
        sections.append(("Overview", parts[0].strip()))
    for i in range(1, len(parts), 2):
        sections.append((parts[i].strip(), parts[i + 1].strip()))
    return sections


def index_all(db: Session):
    global _client
    with _lock:
        if _client is None:
            _client = chromadb.PersistentClient(path=settings.chroma_path)
    try:
        _client.delete_collection(f"kb_{backend_name()}")
    except Exception:
        pass
    col = collection()
    ids, docs, metas = [], [], []
    for art in db.query(KBArticle).all():
        for n, (section, content) in enumerate(split_sections(art.body)):
            ids.append(f"{art.id}-{n}")
            docs.append(f"{art.title}. {section}. {content}")
            metas.append({
                "kb_id": art.kb_id, "version": art.version, "title": art.title, "section": section,
                "status": art.status, "category": art.category, "content": content,
            })
    if ids:
        vectors = embed(docs)
        col.add(ids=ids, documents=docs, metadatas=metas, embeddings=vectors)
    return len(ids)


def ensure_index(db: Session):
    if collection().count() == 0:
        index_all(db)


def search(query: str, k: int = 3, include_inactive: bool = False):
    col = collection()
    if col.count() == 0:
        return []
    qvec = embed([query])[0]
    res = col.query(query_embeddings=[qvec], n_results=min(24, col.count()),
                    include=["documents", "metadatas", "distances"])
    qtoks = set(expand(query))
    hits = []
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        dtoks = set(tokens(doc))
        kw = len(qtoks & dtoks) / len(qtoks) if qtoks else 0.0
        vec = max(0.0, 1.0 - dist)
        ttoks = set(tokens(meta["title"]))
        title_hit = len(qtoks & ttoks) / max(1, len(ttoks))
        boost = {"Steps": 0.06, "Summary": 0.04, "Common Error Codes": 0.03}.get(meta["section"], 0.0)
        score = 0.4 * min(1.0, vec * 2.2) + 0.6 * min(1.0, kw * 1.3) + 0.12 * title_hit + boost
        score = min(1.0, score)
        hits.append({**meta, "score": round(score, 2), "vector": round(vec, 2), "keyword": round(kw, 2)})
    hits.sort(key=lambda h: h["score"], reverse=True)
    active = [h for h in hits if h["status"] == "active"][:k]
    if not include_inactive:
        return active
    filtered = [h for h in hits if h["status"] != "active"][:1]
    return active, filtered
