import os
import logging
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from neo4j import GraphDatabase, Driver, Session

# 加载 .env 环境变量
load_dotenv()

logger = logging.getLogger(__name__)


class Neo4jClient:
    """
    Neo4j 图数据库连接管理客户端
    支持从 .env 自动读取配置，并提供连接池与事务查询/写入接口
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
    ):
        self.uri = uri or os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "")
        self.database = database or os.getenv("NEO4J_DATABASE", "nongww")
        self._driver: Optional[Driver] = None

    def connect(self) -> Driver:
        """建立或获取数据库驱动连接"""
        if self._driver is None:
            self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            self._driver.verify_connectivity()
        return self._driver

    def close(self):
        """关闭驱动连接"""
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    def get_session(self) -> Session:
        """获取指定数据库的会话"""
        driver = self.connect()
        return driver.session(database=self.database)

    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """执行 Cypher 只读查询"""
        with self.get_session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    def execute_write(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """执行 Cypher 写入/更新事务"""
        with self.get_session() as session:
            def _write_tx(tx):
                result = tx.run(query, parameters or {})
                return [record.data() for record in result]

            return session.execute_write(_write_tx)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 单例或默认实例
client = Neo4jClient()
