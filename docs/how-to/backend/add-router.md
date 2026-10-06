# Add a router

## Description

Add or change a FastAPI route. Use when you implement a new endpoint, change an endpoint, or add API behavior.

## Steps

1. Add the route to the router for the area in `rag/api/routers/`. Copy the shape of the closest existing route.
2. Add request and response models to the matching module in `rag/api/schema/`.
3. Take services from `rag/api/deps.py` aliases (`ConversationServiceDep`, `AuthenticatedUserDep`, ...).
4. If the route uses a service without an alias, add the getter and the alias to `rag/api/deps.py`.
5. Put business logic in the service. See [Add a service](add-service.md).
6. Add or update a test in `tests/unit/test_app.py`.
7. Add the frontend type line. See [Call a backend endpoint](../frontend/call-backend-endpoint.md).
8. Validate the change. See [Run validation](../run-validation.md).

## Rules

* Keep the router thin: call the service, shape the result.
* Return a Pydantic model. Use another response class only for a non-JSON body.
* Type a request field a user writes free text into as `UserText` (`rag/api/schema/text.py`), so it is normalized before its length is checked.
* Declare dependencies as `Annotated[T, Depends(...)]` aliases.
* Put a dependency that every route of a router shares on the `APIRouter(dependencies=[...])`.
* Put a dependency that only one router uses as a private function in that router module.
* On failure, raise an `AppError` subclass. Do not raise `fastapi.HTTPException`.
* Name a router and its schema module after its area, in the singular: `setting.py` serves `/api/settings`.
* If the route reads a user-owned resource, check ownership in the service and return 404 for another user's resource.
* If a streaming route reads a user-owned resource, also add a route-level ownership dependency. See `_require_owned_conversation` in `rag/api/routers/chat.py`.
* A new router is a new API area. Ask the user before you add one.
* If you add a router, include it in `create_app` in `rag/app.py`.
* Do not add a route to `_PUBLIC_ROUTES` in `tests/unit/test_app.py` without user approval.

Example: `rag/api/routers/setting.py`.
