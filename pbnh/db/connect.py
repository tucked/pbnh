class DBConnect:
    """create db connection string"""

    def __init__(
        self,
        dialect=None,
        driver=None,
        username=None,
        password=None,
        host=None,
        port=None,
        dbname=None,
    ):
        self._connect = dialect
        if driver:
            self._connect += "+" + driver
        self._connect += "://"
        if username:
            self._connect += username
            if password:
                self._connect += ":" + password
        if host:
            self._connect += "@"
            self._connect += host
            if port:
                self._connect += ":" + str(port)
        elif dialect == "postgresql" and username:
            self._connect += "@localhost"
        if dbname:
            self._connect += "/" + dbname

    def __repr__(self):
        return self._connect

    @property
    def connect(self):
        """Connection string read-only property"""
        return self._connect
