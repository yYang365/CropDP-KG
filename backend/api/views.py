import os
import sys
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

# 加入项目与 build 目录以便引用 client 和 reasoning_engine
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.extend([BASE_DIR, os.path.join(BASE_DIR, "build")])

from neo4j_client import Neo4jClient
from reasoning_engine import KGReasoningEngine


class GraphStatsView(APIView):
    """
    获取知识图谱统计概览：各标签节点计数与各类型关系计数
    """
    def get(self, request):
        client = Neo4jClient()
        try:
            labels = ["Disease", "Pest", "Crop", "Symptom", "Condition", "Part", "Region", "Temperature"]
            node_counts = {}
            total_nodes = 0
            for label in labels:
                res = client.execute_query(f"MATCH (n:{label}) RETURN count(n) AS cnt")
                cnt = res[0]["cnt"] if res else 0
                node_counts[label] = cnt
                total_nodes += cnt

            rel_res = client.execute_query("MATCH ()-[r]->() RETURN type(r) AS rel_type, count(r) AS cnt ORDER BY cnt DESC")
            rel_counts = {row["rel_type"]: row["cnt"] for row in rel_res}
            total_rels = sum(rel_counts.values())

            return Response({
                "code": 200,
                "data": {
                    "total_nodes": total_nodes,
                    "total_relationships": total_rels,
                    "node_counts": node_counts,
                    "rel_counts": rel_counts,
                }
            })
        except Exception as e:
            return Response({"code": 500, "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            client.close()


class GraphMetaView(APIView):
    """
    获取知识图谱元数据（常见作物列表、器官部位列表等）
    """
    def get(self, request):
        client = Neo4jClient()
        try:
            # 热门/常见作物（按受害病虫害数量排序）
            crop_res = client.execute_query("""
                MATCH (c:Crop)<-[:DAMAGE]-(stress)
                RETURN c.name AS name, c.english_name AS english_name, count(stress) AS stress_count
                ORDER BY stress_count DESC LIMIT 50
            """)
            crops = [r["name"] for r in crop_res]

            # 所有受害器官部位
            part_res = client.execute_query("MATCH (p:Part) RETURN p.name AS name ORDER BY name")
            parts = [r["name"] for r in part_res]

            # 常用典型症状标签推荐
            sym_res = client.execute_query("""
                MATCH (s:Symptom)<-[:MANIFEST_AS]-(stress)
                WITH s, count(stress) AS cnt
                WHERE size(s.name) <= 6 AND cnt > 5
                RETURN s.name AS name ORDER BY cnt DESC LIMIT 30
            """)
            common_symptoms = [r["name"] for r in sym_res]

            return Response({
                "code": 200,
                "data": {
                    "crops": crops,
                    "parts": parts,
                    "common_symptoms": common_symptoms
                }
            })
        except Exception as e:
            return Response({"code": 500, "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            client.close()


class GraphSearchView(APIView):
    """
    全局实体多维关键词检索
    """
    def get(self, request):
        keyword = request.query_params.get("keyword", "").strip()
        label_filter = request.query_params.get("type", "").strip()
        limit = int(request.query_params.get("limit", 20))

        if not keyword:
            return Response({"code": 400, "message": "keyword is required"}, status=status.HTTP_400_BAD_REQUEST)

        client = Neo4jClient()
        try:
            type_condition = f"AND n:{label_filter}" if label_filter else ""
            cypher = f"""
                MATCH (n)
                WHERE (n.name CONTAINS $kw OR (n.latin_name IS NOT NULL AND n.latin_name CONTAINS $kw))
                {type_condition}
                RETURN n.name AS name,
                       labels(n)[0] AS type,
                       n.latin_name AS latin_name,
                       n.english_name AS english_name
                LIMIT $limit
            """
            results = client.execute_query(cypher, {"kw": keyword, "limit": limit})
            return Response({"code": 200, "data": results})
        except Exception as e:
            return Response({"code": 500, "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            client.close()


class GraphSubgraphView(APIView):
    """
    获取实体局部知识子图（符合 ECharts Graph 图形渲染格式）
    """
    def get(self, request):
        name = request.query_params.get("name", "").strip()
        if not name:
            # 默认返回具有代表性的桃树/草莓局部网络
            name = "桃炭疽病"

        limit = int(request.query_params.get("limit", 60))
        client = Neo4jClient()

        category_map = {
            "Disease": 0,
            "Pest": 1,
            "Crop": 2,
            "Part": 3,
            "Symptom": 4,
            "Condition": 5,
            "Region": 6,
            "Temperature": 7
        }
        categories = [{"name": k} for k in category_map.keys()]

        try:
            cypher = """
                MATCH (center {name: $name})
                OPTIONAL MATCH (center)-[r]-(neighbor)
                WHERE NOT type(r) = 'CO_OCCURS_WITH' // 避免子图中展现过多密集共发生边
                RETURN center, labels(center)[0] AS center_label,
                       r, type(r) AS rel_type,
                       neighbor, labels(neighbor)[0] AS neighbor_label
                LIMIT $limit
            """
            rows = client.execute_query(cypher, {"name": name, "limit": limit})
            if not rows or not rows[0]["center"]:
                return Response({"code": 404, "message": f"未查找到实体: {name}"}, status=status.HTTP_404_NOT_FOUND)

            node_dict = {}
            links = []

            # 加入中心节点
            center_node = rows[0]["center"]
            center_label = rows[0]["center_label"] or "Disease"
            center_id = center_node.get("name")
            node_dict[center_id] = {
                "id": center_id,
                "name": center_id,
                "category": category_map.get(center_label, 0),
                "symbolSize": 55,
                "label": {"show": True, "fontSize": 14, "fontWeight": "bold"},
                "latin_name": center_node.get("latin_name", ""),
                "english_name": center_node.get("english_name", ""),
                "type": center_label
            }

            for row in rows:
                neighbor = row.get("neighbor")
                rel_type = row.get("rel_type")
                if neighbor and rel_type:
                    nb_id = neighbor.get("name") or neighbor.get("val") or str(neighbor)
                    nb_label = row.get("neighbor_label") or "Symptom"

                    if nb_id not in node_dict:
                        node_dict[nb_id] = {
                            "id": nb_id,
                            "name": nb_id,
                            "category": category_map.get(nb_label, 4),
                            "symbolSize": 36 if nb_label in ["Crop", "Part"] else 26,
                            "label": {"show": True},
                            "latin_name": neighbor.get("latin_name", ""),
                            "english_name": neighbor.get("english_name", ""),
                            "type": nb_label
                        }

                    links.append({
                        "source": center_id,
                        "target": nb_id,
                        "value": rel_type,
                        "lineStyle": {"curveness": 0.1}
                    })

            return Response({
                "code": 200,
                "data": {
                    "categories": categories,
                    "nodes": list(node_dict.values()),
                    "links": links
                }
            })
        except Exception as e:
            return Response({"code": 500, "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            client.close()


class GraphDiagnoseView(APIView):
    """
    智能辅助诊断推理接口
    输入: { crop: "桃树", part: "果实", symptoms: ["水渍状", "凹陷", "红褐色"], top_k: 5 }
    输出: 候选病害、置信度得分及诱发条件
    """
    def post(self, request):
        data = request.data or {}
        crop = data.get("crop", "").strip()
        part = data.get("part", "").strip() or None
        symptoms = data.get("symptoms", [])
        top_k = int(data.get("top_k", 5))

        if not crop:
            return Response({"code": 400, "message": "必须提供寄主作物名称 (crop)"}, status=status.HTTP_400_BAD_REQUEST)

        if isinstance(symptoms, str):
            symptoms = [s.strip() for s in symptoms.replace("，", ",").split(",") if s.strip()]

        try:
            engine = KGReasoningEngine()
            results = engine.diagnose(crop_name=crop, part_name=part, symptom_keywords=symptoms, top_k=top_k)
            return Response({
                "code": 200,
                "data": {
                    "query": {
                        "crop": crop,
                        "part": part,
                        "symptoms": symptoms
                    },
                    "candidates": results
                }
            })
        except Exception as e:
            return Response({"code": 500, "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
