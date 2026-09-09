from http import HTTPStatus

from fastapi import HTTPException


class BaseHttpException(HTTPException):
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR

    def __init__(self, detail: str = ""):
        super().__init__(self.status_code, detail)


class NotFound(BaseHttpException):
    status_code = HTTPStatus.NOT_FOUND


class BadRequest(BaseHttpException):
    status_code = HTTPStatus.BAD_REQUEST


class UnprocessableEntity(BaseHttpException):
    status_code = HTTPStatus.UNPROCESSABLE_ENTITY


class ServerError(BaseHttpException):
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
