import json
import os
import logging
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

FALLBACK_KNOWLEDGE = {
    "chengdu": {
        "spots": "成都核心景点：大熊猫繁育研究基地(门票55)、武侯祠(门票50)、杜甫草堂(门票20)、宽窄巷子(免费)、锦里(免费)、春熙路/太古里(免费)、青城山(门票80)、都江堰(门票80)、人民公园(免费)、文殊院(免费)",
        "food": "成都必吃美食：火锅(推荐小龙坎、蜀大侠)、串串(推荐钢管厂五区)、担担面、龙抄手、钟水饺、甜水面、兔头、冒菜、肥肠粉、蛋烘糕",
        "tips": "成都旅行Tips：1.地铁覆盖主要景点 2.春秋季最佳 3.带胃药防肠胃不适 4.熊猫基地建议早上8点前到 5.武侯祠+锦里可安排半天",
    },
    "xian": {
        "spots": "西安核心景点：兵马俑(门票120)、华清宫(门票120)、大雁塔(登塔25)、古城墙(门票54)、回民街(免费)、大唐不夜城(免费)、钟鼓楼(联票50)、陕西历史博物馆(免费预约)、华山(门票160)",
        "food": "西安必吃美食：肉夹馍、凉皮、羊肉泡馍、biangbiang面、胡辣汤、灌汤包、甑糕、镜糕、酸梅汤",
        "tips": "西安旅行Tips：1.兵马俑在临潼区需坐公交/打车约1.5h 2.华山建议一天往返(西上北下) 3.城墙骑行约2小时 4.回民街物价偏高建议去洒金桥",
    },
}


class KnowledgeService:
    def __init__(self):
        self._client = None
        self._collection = None
        self._initialized = False

    def _init_chroma(self):
        if self._initialized:
            return
        try:
            persist_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                settings.chroma_persist_dir,
            )
            self._client = chromadb.PersistentClient(
                path=persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name="travel_knowledge",
                metadata={"hnsw:space": "cosine"},
            )
            self._initialized = True
            logger.info(f"Chroma initialized, documents count: {self._collection.count()}")
        except Exception as e:
            logger.warning(f"Chroma init failed, will use fallback: {e}")
            self._initialized = False

    def retrieve(self, query: str, city: str | None = None, top_k: int = 5) -> list[str]:
        self._init_chroma()

        if self._initialized and self._collection.count() > 0:
            try:
                where_filter = {"city": city} if city else None
                results = self._collection.query(
                    query_texts=[query],
                    n_results=min(top_k, self._collection.count()),
                    where=where_filter,
                )
                if results and results["documents"] and results["documents"][0]:
                    logger.info(f"RAG retrieved {len(results['documents'][0])} docs for: {query[:50]}")
                    return results["documents"][0]
            except Exception as e:
                logger.warning(f"RAG retrieval failed, falling back: {e}")

        return self._fallback(city)

    def _fallback(self, city: str | None = None) -> list[str]:
        logger.info(f"Using fallback knowledge for city: {city}")
        if city and city in FALLBACK_KNOWLEDGE:
            kb = FALLBACK_KNOWLEDGE[city]
            return [kb["spots"], kb["food"], kb["tips"]]

        all_docs = []
        for city_kb in FALLBACK_KNOWLEDGE.values():
            all_docs.extend([city_kb["spots"], city_kb["food"], city_kb["tips"]])
        return all_docs

    def get_context(self, query: str, city: str | None = None, top_k: int = 5) -> str:
        docs = self.retrieve(query, city, top_k)
        return "\n\n---\n\n".join(docs)


knowledge_service = KnowledgeService()
