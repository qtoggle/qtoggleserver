
from qtoggleserver.core import api as core_api
from qtoggleserver.core import reverse as core_reverse
from qtoggleserver.core.api import schema as core_api_schema
from qtoggleserver.core.typing import GenericJSONDict


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def get_reverse(request: core_api.APIRequest) -> GenericJSONDict:
    return core_reverse.get().to_json()


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def patch_reverse(request: core_api.APIRequest, params: GenericJSONDict) -> None:
    core_api_schema.validate(params, core_api_schema.PATCH_REVERSE)

    try:
        core_reverse.setup(**params)

    except core_reverse.InvalidParamError as e:
        raise core_api.APIError(400, 'invalid-field', field=e.param) from e

    core_reverse.save()
