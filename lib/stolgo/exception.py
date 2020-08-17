class BadDataError(Exception):
    def __init__(self, message):
        super(BadDataError, self).__init__(message)