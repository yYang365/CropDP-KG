import json
from neo4j_client import Neo4jClient


def main():
    print("=" * 60)
    print("正在启动 Neo4j 连接与测试数据写入...")
    print("=" * 60)

    client = Neo4jClient()

    try:
        # 1. 验证连接
        print(f"连接目标: {client.uri}")
        print(f"用户: {client.user}")
        print(f"目标数据库: {client.database}")
        client.connect()
        print("✔ Neo4j 数据库连接成功！\n")

        # 2. 写入测试数据（病害危害作物三元组）
        cypher_write = """
        MERGE (d:Disease {name: $disease_name})
        ON CREATE SET 
            d.latin_name = $latin_name,
            d.english_name = $disease_eng,
            d.created_at = datetime()
        ON MATCH SET 
            d.updated_at = datetime()

        MERGE (c:Crop {name: $crop_name})
        ON CREATE SET 
            c.english_name = $crop_eng,
            c.created_at = datetime()

        MERGE (d)-[r:DAMAGE]->(c)
        SET 
            r.relation = $relation,
            r.is_test = true,
            r.updated_at = datetime()

        RETURN d.name AS disease, d.latin_name AS latin_name, type(r) AS relation_type, r.relation AS relation, c.name AS crop
        """

        params = {
            "disease_name": "草莓枯萎病",
            "latin_name": "Fusarium oxysporum f. sp. fragariae",
            "disease_eng": "Strawberry blight",
            "crop_name": "草莓",
            "crop_eng": "Strawberry",
            "relation": "危害",
        }

        print("正在写入测试数据（病害-危害-作物 三元组）...")
        write_result = client.execute_write(cypher_write, params)
        print("✔ 测试数据写入成功！写入结果：")
        print(json.dumps(write_result, ensure_ascii=False, indent=2))
        print()

        # 3. 验证查询刚写入的数据
        cypher_read = """
        MATCH (d:Disease {name: $disease_name})-[r:DAMAGE]->(c:Crop {name: $crop_name})
        RETURN d.name AS disease, d.latin_name AS latin_name, d.english_name AS english_name,
               type(r) AS rel_type, r.relation AS rel_name, r.is_test AS is_test,
               c.name AS crop, c.english_name AS crop_eng
        """
        print("正在执行 Cypher 检索验证...")
        read_result = client.execute_query(cypher_read, {"disease_name": "草莓枯萎病", "crop_name": "草莓"})
        print("✔ 查询验证成功！返回节点与关联信息：")
        print(json.dumps(read_result, ensure_ascii=False, indent=2))

        print("\n" + "=" * 60)
        print("全部流程测试完成：Python 成功连接 Neo4j 并完成数据存取！")
        print("=" * 60)

    except Exception as e:
        print(f"❌ 执行失败: {e}")
        raise
    finally:
        client.close()


if __name__ == "__main__":
    main()
