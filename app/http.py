import falcon
import msgspec


async def read_body[T](req: falcon.asgi.Request, type_: type[T]) -> T:
    """Decode and validate the JSON request body in a single pass."""
    raw = await req.bounded_stream.read()
    try:
        return msgspec.json.decode(raw, type=type_)
    except msgspec.ValidationError as exc:
        raise falcon.HTTPUnprocessableEntity(description=str(exc)) from exc
    except msgspec.DecodeError as exc:
        raise falcon.HTTPBadRequest(description=str(exc)) from exc


def write_json(resp: falcon.asgi.Response, obj: object, status: str = falcon.HTTP_200) -> None:
    resp.status = status
    resp.content_type = falcon.MEDIA_JSON
    resp.data = msgspec.json.encode(obj)


def error_serializer(req: falcon.asgi.Request, resp: falcon.asgi.Response, exc: falcon.HTTPError):
    """Render every error as {"detail": "..."}."""
    resp.content_type = falcon.MEDIA_JSON
    resp.data = msgspec.json.encode({"detail": exc.description or exc.title})
