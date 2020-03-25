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
 * PATCH /reverse API function call.
 * @alias qtoggle.api.reverse.patchReverse
 * @param {Boolean} enabled whether the reverse API call mechanism is enabled or not
 * @param {String} scheme the URL scheme
 * @param {String} host the host (IP address or hostname) of the client
 * @param {Number} port the TCP port
 * @param {String} path the location for the reverse request
 * @param {Number} timeout the request timeout, in seconds
 * @returns {Promise}
 */
export function patchReverse(enabled, scheme, host, port, path, timeout) {
    let params = {
        enabled: enabled,
        scheme: scheme,
        host: host,
        port: port,
        path: path,
        timeout: timeout
    }

    return BaseAPI.apiCall({method: 'PATCH', path: '/reverse', data: params})
}
