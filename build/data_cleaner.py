import os
import csv
import json
import re
from typing import Dict, List, Set, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(BASE_DIR, "Dataset")


class DataCleaner:
    """
    农作物病虫害知识图谱数据清洗与实体对齐处理器
    """

    def __init__(self, dataset_dir: str = DATASET_DIR):
        self.dataset_dir = dataset_dir
        self.known_diseases: Set[str] = set()
        self.known_pests: Set[str] = set()
        self._load_known_entities_from_ner()

        # 害虫与病害关键词启发式规则
        self.pest_keywords = [
            "蛾", "蚜", "象甲", "蚧", "蝶", "螨", "蝉", "夜蛾", "尺蠖", "天牛",
            "潜叶蝇", "跳甲", "蓟马", "蝽", "金龟", "蝼蛄", "卷叶", "螟", "甲",
            "虱", "蝇", "毛虫", "飞虱", "叶蝉", "食心虫", "红蜘蛛", "盲蝽", "线虫"
        ]
        self.disease_keywords = [
            "病", "枯", "腐", "瘟", "斑", "霉", "穿孔", "溃疡", "疮痂", "流胶",
            "白粉", "黑粉", "煤污", "坏死", "花叶", "缩叶", "锈病", "青枯", "软腐",
            "灰霉", "疫病", "炭疽", "立枯", "猝倒", "畸形"
        ]

    def _load_known_entities_from_ner(self):
        """从 named entity.csv 中抽取金标准实体"""
        ner_path = os.path.join(self.dataset_dir, "named entity.csv")
        if not os.path.exists(ner_path):
            return

        with open(ner_path, mode="r", encoding="utf-8-sig", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                label_str = row.get("label", "").strip()
                if not label_str:
                    continue
                try:
                    labels = json.loads(label_str)
                    for item in labels:
                        text = item.get("text", "").strip()
                        if not text:
                            continue
                        tag_list = item.get("labels", [])
                        if "Disease" in tag_list:
                            self.known_diseases.add(text)
                        if "Pest" in tag_list:
                            self.known_pests.add(text)
                except Exception:
                    pass

    @staticmethod
    def clean_text(text: str) -> str:
        """清洗字符串：去除前后空白、不可见字符和多余引号"""
        if not text:
            return ""
        text = text.strip().strip('"').strip("'").strip()
        # 清理多余控制字符
        text = re.sub(r"[\r\n\t]+", " ", text)
        return text

    def infer_entity_type(self, entity_name: str) -> str:
        """
        推断头实体属于 Disease (病害) 还是 Pest (虫害)
        """
        name = self.clean_text(entity_name)
        if not name:
            return "Disease"

        # 1. 优先比对金标准集合
        if name in self.known_pests:
            return "Pest"
        if name in self.known_diseases:
            return "Disease"

        # 2. 匹配规则引擎（先匹配特征明确的害虫词缀）
        for kw in self.pest_keywords:
            if kw in name:
                return "Pest"

        for kw in self.disease_keywords:
            if kw in name:
                return "Disease"

        # 3. 兜底策略：农作物病害在库中占绝大多数
        return "Disease"

    def read_csv_rows(self, filename: str, is_utf8: bool = False) -> List[Dict[str, str]]:
        """安全读取 CSV 文件，根据文件特性指定编码"""
        path = os.path.join(self.dataset_dir, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"文件未找到: {path}")

        encoding = "utf-8-sig" if is_utf8 else "gb18030"
        rows = []
        with open(path, mode="r", encoding=encoding, errors="replace") as f:
            reader = csv.DictReader(f)
            for r in reader:
                # 清洗所有字段值
                cleaned_row = {self.clean_text(k): self.clean_text(v) for k, v in r.items() if k is not None}
                rows.append(cleaned_row)
        return rows

    def load_crop_relations(self) -> List[Dict]:
        """加载 relationcrop.csv (UTF-8-SIG)"""
        raw_rows = self.read_csv_rows("relationcrop.csv", is_utf8=True)
        results = []
        for r in raw_rows:
            entity_name = r.get("Chinese entity name", "")
            crop_name = r.get("Chinese crop name", "")
            if not entity_name or not crop_name:
                continue

            results.append({
                "entity_name": entity_name,
                "entity_type": self.infer_entity_type(entity_name),
                "latin_name": r.get("entity binomial scientific name", ""),
                "crop_name": crop_name,
                "crop_eng": r.get("English crop name", ""),
                "relation": r.get("Chinese relation", "危害") or "危害"
            })
        return results

    def load_sym_relations(self) -> List[Dict]:
        """加载 relationsym.csv (GB18030)"""
        raw_rows = self.read_csv_rows("relationsym.csv", is_utf8=False)
        results = []
        for r in raw_rows:
            entity_name = r.get("Chinese entity name", "")
            sym_name = r.get("Chinese sym", "")
            if not entity_name or not sym_name:
                continue

            results.append({
                "entity_name": entity_name,
                "entity_type": self.infer_entity_type(entity_name),
                "latin_name": r.get("entity binomial scientific name", ""),
                "sym_name": sym_name,
                "sym_eng": r.get("English sym", ""),
                "relation": r.get("Chinese relation", "存在症状") or "存在症状"
            })
        return results

    def load_con_relations(self) -> List[Dict]:
        """加载 relationcon.csv (GB18030)"""
        raw_rows = self.read_csv_rows("relationcon.csv", is_utf8=False)
        results = []
        for r in raw_rows:
            entity_name = r.get("Chinese entity name", "")
            cond_name = r.get("Chinese condition", "")
            if not entity_name or not cond_name:
                continue

            results.append({
                "entity_name": entity_name,
                "entity_type": self.infer_entity_type(entity_name),
                "latin_name": r.get("entity binomial scientific name", ""),
                "condition_name": cond_name,
                "condition_eng": r.get("English condition", ""),
                "relation": r.get("Chinese relation", "适宜发生条件") or "适宜发生条件"
            })
        return results

    def load_area_relations(self) -> List[Dict]:
        """加载 relationarea.csv (GB18030)"""
        raw_rows = self.read_csv_rows("relationarea.csv", is_utf8=False)
        results = []
        for r in raw_rows:
            entity_name = r.get("Chinese entity name", "")
            region_name = r.get("Chinese region", "")
            if not entity_name or not region_name:
                continue

            results.append({
                "entity_name": entity_name,
                "entity_type": self.infer_entity_type(entity_name),
                "latin_name": r.get("entity binomial scientific name", ""),
                "region_name": region_name,
                "region_eng": r.get("English region", ""),
                "relation": r.get("Chinese relation", "主要发生地") or "主要发生地"
            })
        return results

    def load_part_relations(self) -> List[Dict]:
        """加载 relationpart.csv (GB18030)"""
        raw_rows = self.read_csv_rows("relationpart.csv", is_utf8=False)
        results = []
        for r in raw_rows:
            entity_name = r.get("Chinese entity name", "")
            part_name = r.get("Chinese part", "")
            if not entity_name or not part_name:
                continue

            results.append({
                "entity_name": entity_name,
                "entity_type": self.infer_entity_type(entity_name),
                "latin_name": r.get("entity binomial scientific name", ""),
                "part_name": part_name,
                "part_eng": r.get("English part", ""),
                "relation": r.get("Chinese relation", "危害部位") or "危害部位"
            })
        return results

    def load_tem_relations(self) -> List[Dict]:
        """加载 relationtem.csv (GB18030)"""
        raw_rows = self.read_csv_rows("relationtem.csv", is_utf8=False)
        results = []
        for r in raw_rows:
            entity_name = r.get("Chinese entity name", "")
            tem_val = r.get("tem", "")
            if not entity_name or not tem_val:
                continue

            results.append({
                "entity_name": entity_name,
                "entity_type": self.infer_entity_type(entity_name),
                "latin_name": r.get("entity binomial scientific name", ""),
                "temp_val": tem_val,
                "relation": r.get("Chinese relation", "温度为") or "温度为"
            })
        return results

    def load_eng_mappings(self) -> List[Dict]:
        """加载 relationEng.csv (GB18030)，解析主英文名与别名列表"""
        raw_rows = self.read_csv_rows("relationEng.csv", is_utf8=False)
        results = []
        for r in raw_rows:
            entity_name = r.get("Entity", "")
            eng_str = r.get("English entity", "")
            if not entity_name or not eng_str:
                continue

            # 支持按逗号或分号分隔多个英文别名
            parts = [p.strip() for p in re.split(r"[,，;；]", eng_str) if p.strip()]
            primary_eng = parts[0] if parts else ""
            aliases = parts[1:] if len(parts) > 1 else []

            results.append({
                "entity_name": entity_name,
                "english_name": primary_eng,
                "aliases": aliases
            })
        return results
