from urllib.parse import quote_plus
from sqlalchemy import create_engine, Table, MetaData
from sqlalchemy.orm import sessionmaker, scoped_session


class MySQL:

    def __init__(self,
                 host: str,
                 port: int,
                 database: str,
                 user: str = "root",
                 passwd: str = "",
                 charset: str = "utf8",
                 pool_size: int = 32,
                 max_overflow: int = 64,
                 pool_recycle: int = 1800,
                 autocommit: bool = True,
                 autoflush: bool = True
                 ):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.passwd = passwd
        self.charset = charset
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_recycle = pool_recycle
        self.autocommit = autocommit
        self.autoflush = autoflush
        self.engine = None
        self.session = None
        self.metadata = None
        self.tables = {}

    def _create_engine(self):
        scheme = f"mysql+pymysql://{self.user}:{quote_plus(self.passwd)}@{self.host}:{self.port}/{self.database}?" \
                 f"charset={self.charset}"
        self.engine = create_engine(
            scheme,
            pool_recycle=self.pool_recycle,
            pool_size=self.pool_size,
            max_overflow=self.max_overflow
        )

    def _create_session(self):
        session_factory = sessionmaker(
            autocommit=self.autocommit,
            autoflush=self.autoflush,
            bind=self.engine
        )
        self.session = scoped_session(session_factory)

    def get_session(self):
        """
        获取mysql连接session对象
        """
        if self.session is None:
            self._create_engine()
            self._create_session()

        return self.session()

    def get_table(self, table):
        """
        获取mysql 数据表对象
        """
        if table not in self.tables:
            if self.engine is None:
                self._create_engine()
            if self.metadata is None:
                self.metadata = MetaData(self.engine)
            self.tables[table] = Table(table, self.metadata, autoload=True, autoload_with=self.engine)

        return self.tables[table]

    def close(self, session):
        """
        回收mysql连接
        """
        try:
            if self.session is not None:
                self.session.remove()
                self.session = None
            if self.engine is not None:
                self.engine.dispose()
                self.engine = None
            return True
        except Exception:  # pylint: disable=broad-except
            return False
