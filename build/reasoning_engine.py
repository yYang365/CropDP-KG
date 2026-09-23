import os
import sys
import time
from typing import List, Dict, Any, Optional

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.extend([CURRENT_DIR, PROJECT_DIR])

from neo4j_client import Neo4jClient


class KGReasoningEngine:
    """
    农作物病虫害知识图谱（CropDP-KG）知识融合与推理引擎
    提供：
    1. 症状-部位拓扑重构推理 (Symptom -> LOCATED_IN -> Part)
    2. 同寄主病虫害共发/共侵染拓扑推理 (Disease/Pest -> CO_OCCURS_WITH -> Disease/Pest)
    3. 基于图拓扑交集与加权相似度的病虫害智能诊断算法
    """

    def __init__(self):
        self.client = Neo4jClient()

    def infer_located_in_relations(self) -> int:
        """
        推理规则 1：症状-部位器官拓扑重构
        若病害同时连接了部位 Part 与症状 Symptom，且症状名称中包含该部位核心词，
        则推导建立 (Symptom)-[:LOCATED_IN]->(Part) 关系。
        """
        print("\n[推理 1/2] 正在执行 [症状-部位器官拓扑重构] (Symptom -> LOCATED_IN -> Part)...")
        t0 = time.time()

        # 部位词与症状词的关联模式映射
        part_keyword_rules = [
            ("果实", ["果", "幼果", "病果", "僵果", "果面", "果皮", "果肉", "果尖"]),
            ("叶片", ["叶", "嫩叶", "新叶", "病叶", "托叶", "叶柄", "叶背", "叶面", "叶尖", "叶脉"]),
            ("枝干", ["枝", "干", "新梢", "树干", "主干", "树皮", "枝梢", "嫩枝", "枝组", "枝条"]),
            ("根系", ["根", "根颈", "须根", "主根"]),
            ("花器", ["花", "花瓣", "柱头", "花蕾", "花序", "花梗", "花芽"]),
            ("植株", ["全株", "植株", "全树", "树体", "幼树"]),
        ]

        total_created = 0
        for part_name, keywords in part_keyword_rules:
            cypher = """
            MATCH (pt:Part {name: $part_name})<-[:INFLICT_PART]-(stress)-[:MANIFEST_AS]->(s:Symptom)
            WHERE any(kw IN $keywords WHERE s.name CONTAINS kw)
            MERGE (s)-[r:LOCATED_IN]->(pt)
            ON CREATE SET r.relation = '发生于部位', r.inferred = true, r.created_at = datetime()
            RETURN count(r) AS cnt
            """
            res = self.client.execute_write(cypher, {"part_name": part_name, "keywords": keywords})
            cnt = res[0]["cnt"] if res else 0
            total_created += cnt

        cost = time.time() - t0
        print(f"✔ 症状-器官部位拓扑推理完成: 共创建/确认 {total_created} 条 [LOCATED_IN] 关系，耗时 {cost:.2f} 秒")
        return total_created

    def infer_co_occurrence_relations(self, min_shared_crops: int = 1) -> int:
        """
        推理规则 2：同寄主/共侵染病虫害拓扑推理
        挖掘危害相同作物且在相似部位为害的病害/害虫关联网络，
        推导建立 (stress1)-[:CO_OCCURS_WITH {shared_crops: [...], weight: n}]->(stress2)
        """
        print("\n[推理 2/2] 正在执行 [共发/共侵染病虫害关联推理] (CO_OCCURS_WITH)...")
        t0 = time.time()

        cypher = """
        MATCH (s1)-[:DAMAGE]->(c:Crop)<-[:DAMAGE]-(s2)
        WHERE elementId(s1) < elementId(s2) AND (s1:Disease OR s1:Pest) AND (s2:Disease OR s2:Pest)
        WITH s1, s2, collect(DISTINCT c.name) AS shared_crops, count(DISTINCT c) AS shared_count
        WHERE shared_count >= $min_shared_crops
        MERGE (s1)-[r:CO_OCCURS_WITH]-(s2)
        SET r.weight = shared_count,
            r.shared_crops = shared_crops,
            r.relation = '同寄主共发',
            r.inferred = true
        RETURN count(r) AS cnt
        """
        res = self.client.execute_write(cypher, {"min_shared_crops": min_shared_crops})
        cnt = res[0]["cnt"] if res else 0
        cost = time.time() - t0
        print(f"✔ 共发病虫害推理完成: 共建立/确认 {cnt} 条 [CO_OCCURS_WITH] 关系，耗时 {cost:.2f} 秒")
        return cnt

    def diagnose(
        self,
        crop_name: str,
        part_name: Optional[str] = None,
        symptom_keywords: Optional[List[str]] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        多跳图路径辅助诊断推理算法
        :param crop_name: 寄主农作物名称（如“桃树”或“草莓”）
        :param part_name: 受害部位（如“叶片”或“果实”，可选）
        :param symptom_keywords: 观察到的症状关键词列表（如 ["褐斑", "穿孔", "凹陷"]）
        :param top_k: 返回排名前 K 的可能病虫害
        :return: 诊断结果候选列表（包含置信度得分、拉丁学名、匹配与未匹配症状、诱发条件等）
        """
        symptom_keywords = symptom_keywords or []
        cypher = """
        MATCH (c:Crop {name: $crop_name})<-[:DAMAGE]-(stress)
        WHERE stress:Disease OR stress:Pest

        // 部位匹配（若指定了部位则要求命中或优先加分）
        OPTIONAL MATCH (stress)-[:INFLICT_PART]->(pt:Part)
        WITH stress, c, collect(DISTINCT pt.name) AS parts

        // 症状匹配
        OPTIONAL MATCH (stress)-[:MANIFEST_AS]->(s:Symptom)
        WITH stress, c, parts, collect(DISTINCT s.name) AS symptoms

        // 发生条件提取
        OPTIONAL MATCH (stress)-[:OCCUR_CONDITION]->(cd:Condition)
        WITH stress, c, parts, symptoms, collect(DISTINCT cd.name) AS conditions

        RETURN stress.name AS name,
               labels(stress)[0] AS type,
               stress.latin_name AS latin_name,
               stress.english_name AS english_name,
               parts,
               symptoms,
               conditions
        """

        raw_candidates = self.client.execute_query(cypher, {"crop_name": crop_name})
        if not raw_candidates:
            # 尝试做作物模糊匹配（例如用户输入“草莓”，库中有“草莓”或“草莓果实”）
            cypher_fuzzy = """
            MATCH (c:Crop)<-[:DAMAGE]-(stress)
            WHERE (stress:Disease OR stress:Pest) AND c.name CONTAINS $crop_name
            WITH stress, c, collect(DISTINCT c.name) AS matched_crops
            OPTIONAL MATCH (stress)-[:INFLICT_PART]->(pt:Part)
            OPTIONAL MATCH (stress)-[:MANIFEST_AS]->(s:Symptom)
            OPTIONAL MATCH (stress)-[:OCCUR_CONDITION]->(cd:Condition)
            RETURN stress.name AS name,
                   labels(stress)[0] AS type,
                   stress.latin_name AS latin_name,
                   stress.english_name AS english_name,
                   collect(DISTINCT pt.name) AS parts,
                   collect(DISTINCT s.name) AS symptoms,
                   collect(DISTINCT cd.name) AS conditions
            """
            raw_candidates = self.client.execute_query(cypher_fuzzy, {"crop_name": crop_name})

        results = []
        for item in raw_candidates:
            parts = item.get("parts") or []
            symptoms = item.get("symptoms") or []
            conditions = item.get("conditions") or []

            # 1. 部位得分
            part_matched = False
            part_score = 0.0
            if part_name:
                if part_name in parts or any(part_name in p for p in parts):
                    part_matched = True
                    part_score = 1.0
            else:
                part_score = 0.5  # 未指定部位给予中立分

            # 2. 症状匹配得分 (Jaccard 语义重叠与关键词命中)
            matched_symptoms = []
            if symptom_keywords:
                for kw in symptom_keywords:
                    kw_clean = kw.strip()
                    if not kw_clean:
                        continue
                    for sym in symptoms:
                        if kw_clean in sym:
                            if sym not in matched_symptoms:
                                matched_symptoms.append(sym)

                sym_match_ratio = len(matched_symptoms) / max(len(symptom_keywords), 1)
            else:
                sym_match_ratio = 0.5

            # 综合可信度得分计算公式: 症状权重 0.65 + 部位权重 0.35
            confidence = (sym_match_ratio * 0.65) + (part_score * 0.35)
            confidence_pct = round(min(confidence, 1.0) * 100, 1)

            results.append({
                "name": item.get("name"),
                "type": item.get("type"),
                "latin_name": item.get("latin_name") or "未记录",
                "english_name": item.get("english_name") or "未记录",
                "confidence_score": confidence_pct,
                "part_matched": part_matched,
                "parts": parts,
                "matched_symptoms": matched_symptoms,
                "sample_symptoms": symptoms[:6],
                "conditions": conditions[:4]
            })

        # 按置信度排序
        results.sort(key=lambda x: x["confidence_score"], reverse=True)
        return results[:top_k]

    def run_all_inference(self):
        """执行图谱知识推理并持久化回库"""
        print("=" * 60)
        print("正在启动农作物病虫害图谱知识融合与拓扑推理...")
        print(f"目标数据库: {self.client.database}")
        print("=" * 60)

        loc_cnt = self.infer_located_in_relations()
        co_cnt = self.infer_co_occurrence_relations(min_shared_crops=2)

        print("\n" + "=" * 60)
        print(f"🎉 知识融合推理全部执行完成！累计生成新关系: {loc_cnt + co_cnt} 条")
        print("=" * 60)


if __name__ == "__main__":
    engine = KGReasoningEngine()
    engine.run_all_inference()

    # 运行一次智能诊断算法示例
    print("\n🔍 智能诊断推理算法示例测试:")
    demo_res = engine.diagnose(
        crop_name="桃树",
        part_name="果实",
        symptom_keywords=["水渍状", "凹陷", "红褐色", "小粒点"]
    )
    for i, r in enumerate(demo_res, 1):
        print(f"  Top {i}: [{r['type']}] {r['name']} (置信度: {r['confidence_score']}%) | 拉丁学名: {r['latin_name']}")
        print(f"         命中症状: {r['matched_symptoms']}")
        print(f"         诱发条件: {r['conditions']}")
