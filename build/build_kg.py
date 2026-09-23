import os
import sys
import time
from typing import List, Dict

# 将当前目录和项目根目录加入 sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.extend([CURRENT_DIR, PROJECT_DIR])

from neo4j_client import Neo4jClient
from data_cleaner import DataCleaner


class KGBuilder:
    """
    农作物病虫害知识图谱（CropDP-KG）自动化构建与批量入库程序
    """

    def __init__(self, batch_size: int = 500):
        self.client = Neo4jClient()
        self.cleaner = DataCleaner()
        self.batch_size = batch_size

    def create_constraints_and_indexes(self):
        """第一步：创建唯一性约束与索引"""
        print("\n[Step 1/9] 创建唯一性约束与索引...")
        constraints = [
            "CREATE CONSTRAINT disease_name_uq IF NOT EXISTS FOR (d:Disease) REQUIRE d.name IS UNIQUE",
            "CREATE CONSTRAINT pest_name_uq IF NOT EXISTS FOR (p:Pest) REQUIRE p.name IS UNIQUE",
            "CREATE CONSTRAINT crop_name_uq IF NOT EXISTS FOR (c:Crop) REQUIRE c.name IS UNIQUE",
            "CREATE CONSTRAINT symptom_name_uq IF NOT EXISTS FOR (s:Symptom) REQUIRE s.name IS UNIQUE",
            "CREATE CONSTRAINT part_name_uq IF NOT EXISTS FOR (pt:Part) REQUIRE pt.name IS UNIQUE",
            "CREATE CONSTRAINT condition_name_uq IF NOT EXISTS FOR (cd:Condition) REQUIRE cd.name IS UNIQUE",
            "CREATE CONSTRAINT region_name_uq IF NOT EXISTS FOR (r:Region) REQUIRE r.name IS UNIQUE",
            "CREATE CONSTRAINT temp_val_uq IF NOT EXISTS FOR (t:Temperature) REQUIRE t.val IS UNIQUE",
        ]
        indexes = [
            "CREATE INDEX disease_latin_idx IF NOT EXISTS FOR (d:Disease) ON (d.latin_name)",
            "CREATE INDEX pest_latin_idx IF NOT EXISTS FOR (p:Pest) ON (p.latin_name)",
        ]

        for stmt in constraints + indexes:
            try:
                self.client.execute_write(stmt)
            except Exception as e:
                print(f"  - 提示: {stmt} -> {e}")
        print("✔ 约束与索引配置完成！")

    def _batch_write(self, cypher: str, data: List[Dict], desc: str):
        """分批参数化批量执行 Cypher"""
        total = len(data)
        if total == 0:
            return
        t0 = time.time()
        for i in range(0, total, self.batch_size):
            batch = data[i : i + self.batch_size]
            self.client.execute_write(cypher, {"batch": batch})
        cost = time.time() - t0
        print(f"✔ {desc}: 共导入 {total} 条数据，耗时 {cost:.2f} 秒")

    def import_crop_relations(self):
        """第二步：导入病虫害与作物的危害关系"""
        print("\n[Step 2/9] 导入 [危害] 寄主作物关系...")
        records = self.cleaner.load_crop_relations()
        disease_records = [r for r in records if r["entity_type"] == "Disease"]
        pest_records = [r for r in records if r["entity_type"] == "Pest"]

        cypher_disease = """
        UNWIND $batch AS row
        MERGE (d:Disease {name: row.entity_name})
        ON CREATE SET d.latin_name = row.latin_name
        ON MATCH SET d.latin_name = CASE WHEN d.latin_name IS NULL OR d.latin_name = '' THEN row.latin_name ELSE d.latin_name END

        MERGE (c:Crop {name: row.crop_name})
        ON CREATE SET c.english_name = row.crop_eng

        MERGE (d)-[r:DAMAGE]->(c)
        SET r.relation = row.relation
        """

        cypher_pest = """
        UNWIND $batch AS row
        MERGE (p:Pest {name: row.entity_name})
        ON CREATE SET p.latin_name = row.latin_name
        ON MATCH SET p.latin_name = CASE WHEN p.latin_name IS NULL OR p.latin_name = '' THEN row.latin_name ELSE p.latin_name END

        MERGE (c:Crop {name: row.crop_name})
        ON CREATE SET c.english_name = row.crop_eng

        MERGE (p)-[r:DAMAGE]->(c)
        SET r.relation = row.relation
        """

        self._batch_write(cypher_disease, disease_records, "病害-危害-作物")
        self._batch_write(cypher_pest, pest_records, "害虫-危害-作物")

    def import_sym_relations(self):
        """第三步：导入症状关系"""
        print("\n[Step 3/9] 导入 [存在症状] 关系...")
        records = self.cleaner.load_sym_relations()
        disease_records = [r for r in records if r["entity_type"] == "Disease"]
        pest_records = [r for r in records if r["entity_type"] == "Pest"]

        cypher_disease = """
        UNWIND $batch AS row
        MERGE (d:Disease {name: row.entity_name})
        ON CREATE SET d.latin_name = row.latin_name
        ON MATCH SET d.latin_name = CASE WHEN d.latin_name IS NULL OR d.latin_name = '' THEN row.latin_name ELSE d.latin_name END

        MERGE (s:Symptom {name: row.sym_name})
        ON CREATE SET s.english_desc = row.sym_eng

        MERGE (d)-[r:MANIFEST_AS]->(s)
        SET r.relation = row.relation
        """

        cypher_pest = """
        UNWIND $batch AS row
        MERGE (p:Pest {name: row.entity_name})
        ON CREATE SET p.latin_name = row.latin_name
        ON MATCH SET p.latin_name = CASE WHEN p.latin_name IS NULL OR p.latin_name = '' THEN row.latin_name ELSE p.latin_name END

        MERGE (s:Symptom {name: row.sym_name})
        ON CREATE SET s.english_desc = row.sym_eng

        MERGE (p)-[r:MANIFEST_AS]->(s)
        SET r.relation = row.relation
        """

        self._batch_write(cypher_disease, disease_records, "病害-存在症状")
        self._batch_write(cypher_pest, pest_records, "害虫-存在症状")

    def import_con_relations(self):
        """第四步：导入发病条件诱因关系"""
        print("\n[Step 4/9] 导入 [适宜发生条件] 关系...")
        records = self.cleaner.load_con_relations()
        disease_records = [r for r in records if r["entity_type"] == "Disease"]
        pest_records = [r for r in records if r["entity_type"] == "Pest"]

        cypher_disease = """
        UNWIND $batch AS row
        MERGE (d:Disease {name: row.entity_name})
        ON CREATE SET d.latin_name = row.latin_name
        ON MATCH SET d.latin_name = CASE WHEN d.latin_name IS NULL OR d.latin_name = '' THEN row.latin_name ELSE d.latin_name END

        MERGE (c:Condition {name: row.condition_name})
        ON CREATE SET c.english_desc = row.condition_eng

        MERGE (d)-[r:OCCUR_CONDITION]->(c)
        SET r.relation = row.relation
        """

        cypher_pest = """
        UNWIND $batch AS row
        MERGE (p:Pest {name: row.entity_name})
        ON CREATE SET p.latin_name = row.latin_name
        ON MATCH SET p.latin_name = CASE WHEN p.latin_name IS NULL OR p.latin_name = '' THEN row.latin_name ELSE p.latin_name END

        MERGE (c:Condition {name: row.condition_name})
        ON CREATE SET c.english_desc = row.condition_eng

        MERGE (p)-[r:OCCUR_CONDITION]->(c)
        SET r.relation = row.relation
        """

        self._batch_write(cypher_disease, disease_records, "病害-发生条件")
        self._batch_write(cypher_pest, pest_records, "害虫-发生条件")

    def import_area_relations(self):
        """第五步：导入主要分布区域关系"""
        print("\n[Step 5/9] 导入 [主要发生地] 关系...")
        records = self.cleaner.load_area_relations()
        disease_records = [r for r in records if r["entity_type"] == "Disease"]
        pest_records = [r for r in records if r["entity_type"] == "Pest"]

        cypher_disease = """
        UNWIND $batch AS row
        MERGE (d:Disease {name: row.entity_name})
        ON CREATE SET d.latin_name = row.latin_name
        ON MATCH SET d.latin_name = CASE WHEN d.latin_name IS NULL OR d.latin_name = '' THEN row.latin_name ELSE d.latin_name END

        MERGE (reg:Region {name: row.region_name})
        ON CREATE SET reg.english_name = row.region_eng

        MERGE (d)-[r:DISTRIBUTED_IN]->(reg)
        SET r.relation = row.relation
        """

        cypher_pest = """
        UNWIND $batch AS row
        MERGE (p:Pest {name: row.entity_name})
        ON CREATE SET p.latin_name = row.latin_name
        ON MATCH SET p.latin_name = CASE WHEN p.latin_name IS NULL OR p.latin_name = '' THEN row.latin_name ELSE p.latin_name END

        MERGE (reg:Region {name: row.region_name})
        ON CREATE SET reg.english_name = row.region_eng

        MERGE (p)-[r:DISTRIBUTED_IN]->(reg)
        SET r.relation = row.relation
        """

        self._batch_write(cypher_disease, disease_records, "病害-主要发生地")
        self._batch_write(cypher_pest, pest_records, "害虫-主要发生地")

    def import_part_relations(self):
        """第六步：导入危害部位关系"""
        print("\n[Step 6/9] 导入 [危害部位] 关系...")
        records = self.cleaner.load_part_relations()
        disease_records = [r for r in records if r["entity_type"] == "Disease"]
        pest_records = [r for r in records if r["entity_type"] == "Pest"]

        cypher_disease = """
        UNWIND $batch AS row
        MERGE (d:Disease {name: row.entity_name})
        ON CREATE SET d.latin_name = row.latin_name
        ON MATCH SET d.latin_name = CASE WHEN d.latin_name IS NULL OR d.latin_name = '' THEN row.latin_name ELSE d.latin_name END

        MERGE (pt:Part {name: row.part_name})
        ON CREATE SET pt.english_name = row.part_eng

        MERGE (d)-[r:INFLICT_PART]->(pt)
        SET r.relation = row.relation
        """

        cypher_pest = """
        UNWIND $batch AS row
        MERGE (p:Pest {name: row.entity_name})
        ON CREATE SET p.latin_name = row.latin_name
        ON MATCH SET p.latin_name = CASE WHEN p.latin_name IS NULL OR p.latin_name = '' THEN row.latin_name ELSE p.latin_name END

        MERGE (pt:Part {name: row.part_name})
        ON CREATE SET pt.english_name = row.part_eng

        MERGE (p)-[r:INFLICT_PART]->(pt)
        SET r.relation = row.relation
        """

        self._batch_write(cypher_disease, disease_records, "病害-危害部位")
        self._batch_write(cypher_pest, pest_records, "害虫-危害部位")

    def import_tem_relations(self):
        """第七步：导入发病适宜温度关系"""
        print("\n[Step 7/9] 导入 [温度为] 适宜温度关系...")
        records = self.cleaner.load_tem_relations()
        disease_records = [r for r in records if r["entity_type"] == "Disease"]
        pest_records = [r for r in records if r["entity_type"] == "Pest"]

        cypher_disease = """
        UNWIND $batch AS row
        MERGE (d:Disease {name: row.entity_name})
        ON CREATE SET d.latin_name = row.latin_name
        ON MATCH SET d.latin_name = CASE WHEN d.latin_name IS NULL OR d.latin_name = '' THEN row.latin_name ELSE d.latin_name END

        MERGE (t:Temperature {val: row.temp_val})

        MERGE (d)-[r:OPTIMAL_TEMP]->(t)
        SET r.relation = row.relation
        """

        cypher_pest = """
        UNWIND $batch AS row
        MERGE (p:Pest {name: row.entity_name})
        ON CREATE SET p.latin_name = row.latin_name
        ON MATCH SET p.latin_name = CASE WHEN p.latin_name IS NULL OR p.latin_name = '' THEN row.latin_name ELSE p.latin_name END

        MERGE (t:Temperature {val: row.temp_val})

        MERGE (p)-[r:OPTIMAL_TEMP]->(t)
        SET r.relation = row.relation
        """

        self._batch_write(cypher_disease, disease_records, "病害-适宜温度")
        self._batch_write(cypher_pest, pest_records, "害虫-适宜温度")

    def enrich_english_mappings(self):
        """第八步：补齐中英文实体映射与别名属性"""
        print("\n[Step 8/9] 融合英文名称与别名属性...")
        records = self.cleaner.load_eng_mappings()

        cypher_enrich = """
        UNWIND $batch AS row
        MATCH (n) WHERE (n:Disease OR n:Pest) AND n.name = row.entity_name
        SET n.english_name = row.english_name,
            n.aliases = row.aliases
        """
        self._batch_write(cypher_enrich, records, "英文别名属性融合")

    def build_inverse_relations(self):
        """第九步：生成作物易感病虫害的逆向查询关系 [AFFECTED_BY]"""
        print("\n[Step 9/9] 生成 [易感/易发] 逆向关系 (Crop -> Disease/Pest)...")
        t0 = time.time()
        cypher_inv = """
        MATCH (stress)-[:DAMAGE]->(c:Crop)
        WHERE stress:Disease OR stress:Pest
        MERGE (c)-[r:AFFECTED_BY]->(stress)
        SET r.relation = '受害于'
        RETURN count(r) AS created_count
        """
        res = self.client.execute_write(cypher_inv)
        cost = time.time() - t0
        count = res[0]["created_count"] if res else 0
        print(f"✔ 逆向索引构建完成: 共创建/确认 {count} 条 AFFECTED_BY 关系，耗时 {cost:.2f} 秒")

    def run_all(self):
        """执行完整构建流水线"""
        print("=" * 60)
        print("正在启动农作物病虫害知识图谱（CropDP-KG）全量构建与入库...")
        print(f"目标数据库: {self.client.database} (URI: {self.client.uri})")
        print("=" * 60)
        start_time = time.time()

        try:
            self.create_constraints_and_indexes()
            self.import_crop_relations()
            self.import_sym_relations()
            self.import_con_relations()
            self.import_area_relations()
            self.import_part_relations()
            self.import_tem_relations()
            self.enrich_english_mappings()
            self.build_inverse_relations()

            total_cost = time.time() - start_time
            print("\n" + "=" * 60)
            print(f"🎉 图谱构建入库全流程顺利完成！总耗时: {total_cost:.2f} 秒")
            print("=" * 60)
        finally:
            self.client.close()


if __name__ == "__main__":
    builder = KGBuilder(batch_size=500)
    builder.run_all()
