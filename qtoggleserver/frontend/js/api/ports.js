/**
 * @namespace qtoggle.api.ports
 */

import * as Cache from '$app/cache.js'

import * as BaseAPI          from './base.js'
import * as APIConstants     from './constants.js'
import * as NotificationsAPI from './notifications.js'


const ROUND_VALUE_TEMPLATE = 1e6

export const HISTORY_MAX_LIMIT = 10000 /* Max number of samples downloadable with a single request */


/**
 * GET /ports API function call.
 * @alias qtoggle.api.ports.getPorts
 * @returns {Promise}
 */
export function getPorts() {
    return BaseAPI.apiCall({method: 'GET', path: '/ports'})
}

/**
 * PATCH /ports/{id} API function call.
 * @alias qtoggle.api.ports.patchPort
 * @param {String} id the port identifier
 * @param {Object} attrs the port attributes to set
 * @param {Number} [expectEventTimeout] optional timeout within which a corresponding event will be expected,
 * @returns {Promise}
 */
export function patchPort(id, attrs, expectEventTimeout = null) {
    let slaveName = BaseAPI.getSlaveName()
    let handle = NotificationsAPI.expectEvent('port-update', {
        id: slaveName ? `${slaveName}.${id}` : id
    }, expectEventTimeout)

    return BaseAPI.apiCall({
        method: 'PATCH',
        path: `/ports/${id}`,
        data: attrs,
        expectedHandle: handle,
        timeout: APIConstants.LONG_SERVER_TIMEOUT
    })
}

/**
 * POST /ports API function call.
 * @alias qtoggle.api.ports.postPorts
 * @param {String} id the port identifier
 * @param {String} type the port type
 * @param {?Number} min a minimum port value
 * @param {?Number} max a maximum port value
 * @param {?Boolean} integer whether the port value must be a integer
 * @param {?Number} step a step for port value validation
 * @param {?Number[]|?String[]} choices valid choices for the port value
 * @param {Number} [expectEventTimeout] optional timeout within which a corresponding event will be expected,
 * @returns {Promise}
 */
export function postPorts(id, type, min, max, integer, step, choices, expectEventTimeout = null) {
    let slaveName = BaseAPI.getSlaveName()
    let handle = NotificationsAPI.expectEvent('port-add', {
        id: slaveName ? `${slaveName}.${id}` : id
    }, expectEventTimeout)

    let data = {
        id: id,
        type: type
    }

    if (min != null) {
        data.min = min
    }
    if (max != null) {
        data.max = max
    }
    if (integer != null) {
        data.integer = integer
    }
    if (step != null) {
        data.step = step
    }
    if (choices != null) {
        data.choices = choices
    }

    return BaseAPI.apiCall({method: 'POST', path: '/ports', data: data, expectedHandle: handle})
}

/**
 * DELETE /ports/{id} API function call.
 * @alias qtoggle.api.ports.deletePort
 * @param {String} id the port identifier
 * @param {Number} [expectEventTimeout] optional timeout within which a corresponding event will be expected,
 * @returns {Promise}
 */
export function deletePort(id, expectEventTimeout = null) {
    let slaveName = BaseAPI.getSlaveName()
    let handle = NotificationsAPI.expectEvent('port-remove', {
        id: slaveName ? `${slaveName}.${id}` : id
    }, expectEventTimeout)

    return BaseAPI.apiCall({method: 'DELETE', path: `/ports/${id}`, expectedHandle: handle})
}

/**
 * GET /ports/{id}/value API function call.
 * @alias qtoggle.api.ports.getPortValue
 * @param {String} id the port identifier
 * @returns {Promise}
 */
export function getPortValue(id) {
    return BaseAPI.apiCall({method: 'GET', path: `/ports/${id}/value`})
}

/**
 * PATCH /ports/{id}/value API function call.
 * @alias qtoggle.api.ports.patchPortValue
 * @param {String} id the port identifier
 * @param {Boolean|Number} value the new port value
 * @param {Number} [expectEventTimeout] optional timeout within which a corresponding event will be expected, in
 * milliseconds
 * @returns {Promise}
 */
export function patchPortValue(id, value, expectEventTimeout = null) {
    let port = Cache.getPort(id)
    let handle = null

    /* Round value to a decent number of decimals */
    if (port && port.type === 'number') {
        value = Math.round(value * ROUND_VALUE_TEMPLATE) / ROUND_VALUE_TEMPLATE
    }

    /* Expect a value-change event only if the currently known value differs from the new one */
    if (!port || port.value == null || port.value !== value) {
        let slaveName = BaseAPI.getSlaveName()
        handle = NotificationsAPI.expectEvent('value-change', {
            id: slaveName ? `${slaveName}.${id}` : id,
            value: value
        }, expectEventTimeout)
    }

    return BaseAPI.apiCall({
        method: 'PATCH',
        path: `/ports/${id}/value`,
        data: value,
        expectedHandle: handle,
        timeout: APIConstants.LONG_SERVER_TIMEOUT
    })
}

/**
 * PATCH /ports/{id}/sequence API function call.
 * @alias qtoggle.api.ports.patchPortSequence
 * @param {String} id the port identifier
 * @param {Boolean[]|Number[]} values the list of values in the sequence
 * @param {Number[]} delays the list of delays between values
 * @param {Number} repeat sequence repeat count
 * @returns {Promise}
 */
export function patchPortSequence(id, values, delays, repeat) {
    let data = {values: values, delays: delays, repeat: repeat}

    return BaseAPI.apiCall({method: 'PATCH', path: `/ports/${id}/sequence`, data: data})
}

/**
 * GET /ports/{id}/history API function call.
 * @alias qtoggle.api.ports.getPortHistory
 * @param {String} id the port identifier
 * @param {Number} from start of interval, as timestamp in milliseconds
 * @param {Number} [to] end of interval, as timestamp in milliseconds
 * @param {Number} [limit]
 * @returns {Promise}
 */
export function getPortHistory(id, from, to = null, limit = null) {
    let query = {from}
    if (to != null) {
        query['to'] = to
    }
    if (limit != null) {
        query['limit'] = limit
    }

    return BaseAPI.apiCall({
        method: 'GET',
        path: `/ports/${id}/history`,
        query: query,
        timeout: APIConstants.LONG_SERVER_TIMEOUT
    })
}

/**
 * DELETE /ports/{id}/history API function call.
 * @alias qtoggle.api.ports.deletePortHistory
 * @param {String} id the port identifier
 * @param {Number} from start of interval, as timestamp in milliseconds
 * @param {Number} to end of interval, as timestamp in milliseconds
 * @returns {Promise}
 */
export function deletePortValue(id, from, to) {
    let query = {from, to}

    return BaseAPI.apiCall({
        method: 'DELETE',
        path: `/ports/${id}/history`,
        query: query,
        timeout: APIConstants.LONG_SERVER_TIMEOUT
    })
}
