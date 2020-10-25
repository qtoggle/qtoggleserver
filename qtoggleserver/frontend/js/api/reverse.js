/**
 * @namespace qtoggle.api.reverse
 */

import * as BaseAPI from './base.js'


/**
 * GET /reverse API function call.
 * @alias qtoggle.api.reverse.getReverse
 * @returns {Promise}
 */
export function getReverse() {
    return BaseAPI.apiCall({method: 'GET', path: '/reverse'})
}

/**
 * PUT /reverse API function call.
 * @alias qtoggle.api.reverse.patchReverse
 * @param {Boolean} enabled whether the reverse API call mechanism is enabled or not
 * @param {String} scheme the URL scheme
 * @param {String} host the host (IP address or hostname) of the client
 * @param {Number} port the TCP port
 * @param {String} path the location for the reverse request
 * @param {String} password the password
 * @param {String} deviceId the device ID
 * @param {Number} timeout the request timeout, in seconds
 * @returns {Promise}
 */
export function putReverse(enabled, scheme, host, port, path, password, deviceId, timeout) {
    let params = {
        enabled: enabled,
        scheme: scheme,
        host: host,
        port: port,
        path: path,
        password: password,
        device_id: deviceId,
        timeout: timeout
    }

    return BaseAPI.apiCall({method: 'PUT', path: '/reverse', data: params})
}
