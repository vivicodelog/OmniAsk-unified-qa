"""
BM25 —— 关键词检索的打分算法（手写，无第三方依赖）。

选 BM25 而非 TF-IDF 的原因：BM25 加了文档长度归一化，
长文档不会因为词频高而虚高，短标题类文本的权重更合理。

rrf_fusion —— Reciprocal Rank Fusion：把多个排序结果融合成一个排序。
它不关心各路结果的绝对分数（向量余弦分和 BM25 分不可比），
只关心「相对排名」，天然适配混合检索。
"""
import math


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.docs = docs
        self.k1 = k1
        self.b = b
        self.n = len(docs)
        self.doc_len = [len(d) for d in docs]
        self.avgdl = (sum(self.doc_len) / self.n) if self.n else 1.0
        # df[t] = 包含词 t 的文档数；idf 用 BM25 平滑版，保证非负
        self.df: dict[str, int] = {}
        for doc in docs:
            for t in set(doc):
                self.df[t] = self.df.get(t, 0) + 1
        self.idf: dict[str, float] = {
            t: math.log((self.n - f + 0.5) / (f + 0.5) + 1.0)
            for t, f in self.df.items()
        }

    def scores(self, query: list[str]) -> list[float]:
        result: list[float] = []
        for doc, dl in zip(self.docs, self.doc_len):
            tf: dict[str, int] = {}
            for t in doc:
                tf[t] = tf.get(t, 0) + 1
            s = 0.0
            for q in query:
                if q not in self.idf:      # 词不在任何文档，跳过
                    continue
                f = tf.get(q, 0)
                # 长度归一化：dl/avgdl 越大（文档越长）分母越大，抑制长文档
                denom = f + self.k1 * (1.0 - self.b + self.b * dl / self.avgdl)
                s += self.idf[q] * (f * (self.k1 + 1.0)) / denom
            result.append(s)
        return result


def rrf_fusion(rankings: list[list[int]], k: int = 60, top_k: int | None = None) -> list[int]:
    """融合多个「按相关度降序的下标列表」，返回融合后的下标列表。

    RRF score = Σ 1/(k + rank)，rank 从 1 起。rank 越靠前贡献越大，
    在多个列表都出现的块分数累加更高。k=60 是学界常用默认值。
    """
    score: dict[int, float] = {}
    for ranking in rankings:
        for rank, idx in enumerate(ranking, start=1):
            score[idx] = score.get(idx, 0) + 1.0 / (k + rank)
    fused = sorted(score, key=lambda i: score[i], reverse=True)
    return fused if top_k is None else fused[:top_k]
