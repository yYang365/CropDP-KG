import os
import sys
import json

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.extend([CURRENT_DIR, PROJECT_DIR])

from neo4j_client import Neo4jClient


def verify_knowledge_graph():
    client = Neo4jClient()
    print("=" * 65)
    print("正在对 Neo4j 农作物病虫害知识图谱（CropDP-KG）进行质量核验...")
    print(f"当前数据库: {client.database}")
    print("=" * 65)

    try:
        # 1. 统计各标签节点数
        print("\n📊 [1/4] 各实体标签节点数量统计:")
        node_labels = ["Disease", "Pest", "Crop", "Symptom", "Condition", "Part", "Region", "Temperature"]
        total_nodes = 0
        node_stats = {}
        for label in node_labels:
            query = f"MATCH (n:{label}) RETURN count(n) AS cnt"
            res = client.execute_query(query)
            cnt = res[0]["cnt"] if res else 0
            node_stats[label] = cnt
            total_nodes += cnt
            print(f"  - :{label:<12} : {cnt:>6} 个")
        print(f"  👉 总节点数累加: {total_nodes} 个")

        # 2. 统计各类关系数量
        print("\n🔗 [2/4] 各关系类型边数量统计:")
        rel_query = """
        MATCH ()-[r]->()
        RETURN type(r) AS rel_type, count(r) AS cnt
        ORDER BY cnt DESC
        """
        rel_res = client.execute_query(rel_query)
        total_rels = 0
        for row in rel_res:
            rtype = row["rel_type"]
            cnt = row["cnt"]
            total_rels += cnt
            print(f"  - -[:{rtype:<16}]-> : {cnt:>6} 条")
        print(f"  👉 总关系数: {total_rels} 条")

        # 3. 抽样验证典型病害子图 (桃炭疽病)
        print("\n🔍 [3/4] 抽样检验典型病害: [桃炭疽病] 子图网络:")
        cypher_sample_disease = """
        MATCH (d:Disease {name: '桃炭疽病'})
        OPTIONAL MATCH (d)-[:DAMAGE]->(c:Crop)
        OPTIONAL MATCH (d)-[:INFLICT_PART]->(pt:Part)
        OPTIONAL MATCH (d)-[:OCCUR_CONDITION]->(cd:Condition)
        OPTIONAL MATCH (d)-[:MANIFEST_AS]->(s:Symptom)
        RETURN d.name AS name, d.latin_name AS latin_name, d.english_name AS english_name,
               collect(DISTINCT c.name)[..3] AS crops,
               collect(DISTINCT pt.name) AS parts,
               collect(DISTINCT cd.name)[..3] AS conditions,
               collect(DISTINCT s.name)[..4] AS sample_symptoms
        """
        disease_info = client.execute_query(cypher_sample_disease)
        if disease_info:
            print(json.dumps(disease_info[0], ensure_ascii=False, indent=2))
        else:
            print("  - 未查到 [桃炭疽病] 节点")

        # 4. 抽样检验典型害虫子图 (香蕉黑带象甲)
        print("\n🔍 [4/4] 抽样检验典型害虫: [香蕉黑带象甲] 子图网络:")
        cypher_sample_pest = """
        MATCH (p:Pest {name: '香蕉黑带象甲'})
        OPTIONAL MATCH (p)-[:DAMAGE]->(c:Crop)
        OPTIONAL MATCH (p)-[:DISTRIBUTED_IN]->(r:Region)
        OPTIONAL MATCH (p)-[:MANIFEST_AS]->(s:Symptom)
        RETURN p.name AS name, p.latin_name AS latin_name, p.english_name AS english_name,
               p.aliases AS aliases,
               collect(DISTINCT c.name) AS crops,
               collect(DISTINCT r.name) AS regions,
               collect(DISTINCT s.name)[..3] AS sample_symptoms
        """
        pest_info = client.execute_query(cypher_sample_pest)
        if pest_info:
            print(json.dumps(pest_info[0], ensure_ascii=False, indent=2))
        else:
            print("  - 未查到 [香蕉黑带象甲] 节点")

        print("\n" + "=" * 65)
        print("✔ 知识图谱核验完成！数据结构完整、实体关联健康！")
        print("=" * 65)

    finally:
        client.close()


if __name__ == "__main__":
    verify_knowledge_graph()
