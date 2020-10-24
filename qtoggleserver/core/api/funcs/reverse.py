
from qtoggleserver.core import api as core_api
from qtoggleserver.core import reverse as core_reverse
from qtoggleserver.core.api import schema as core_api_schema
from qtoggleserver.core.typing import GenericJSONDict


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def get_reverse(request: core_api.APIRequest) -> GenericJSONDict:
    return core_reverse.get().to_json()


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def put_reverse(request: core_api.APIRequest, params: GenericJSONDict) -> None:
    core_api_schema.validate(params, core_api_schema.PATCH_REVERSE)

    # Also ensure that needed fields are not empty when mechanism is enabled
    if params['enabled']:
        if not params['host']:
            raise core_api.APIError(400, 'invalid-field', field='host')
        if not params['path']:
            raise core_api.APIError(400, 'invalid-field', field='path')

    if 'password' not in params and 'password_hash' not in params:
        raise core_api.APIError(400, 'missing-field', field='password')

    try:
        core_reverse.setup(**params)

    except core_reverse.InvalidParamError as e:
        raise core_api.APIError(400, 'invalid-field', field=e.param) from e

    core_reverse.save()
