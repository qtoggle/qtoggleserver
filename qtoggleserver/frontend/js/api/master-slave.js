/**
 * @namespace qtoggle.api.masterslave
 */

import * as BaseAPI          from './base.js'
import * as APIConstants     from './constants.js'
import * as NotificationsAPI from './notifications.js'


/**
 * GET /devices API function call.
 * @alias qtoggle.api.masterslave.getSlaveDevices
 * @returns {Promise}
 */
export function getSlaveDevices() {
    return BaseAPI.apiCall({method: 'GET', path: '/devices'})
}

/**
 * POST /devices API function call.
 * @alias qtoggle.api.masterslave.postSlaveDevices
 * @param {String} scheme the URL scheme
 * @param {String} host the host (IP address or hostname) of the device
 * @param {Number} port the TCP port
 * @param {String} path the location of the API on the device
 * @param {String} adminPassword the administrator password of the device
 * @param {Number} [pollInterval] polling interval, in seconds
 * @param {Boolean} [listenEnabled] whether to enable listening or not
 * @param {Number} [expectEventTimeout] optional timeout within which a corresponding event will be expected,
 * @returns {Promise}
 */
export function postSlaveDevices(
    scheme, host, port, path, adminPassword, pollInterval = null, listenEnabled = null, expectEventTimeout = null
) {
    let params = {
        scheme: scheme,
        host: host,
        port: port,
        path: path,
        admin_password: adminPassword
    }

    if (pollInterval != null) {
        params['poll_interval'] = pollInterval
    }
    if (listenEnabled != null) {
        params['listen_enabled'] = listenEnabled
    }

    let handle = NotificationsAPI.expectEvent('slave-device-add', {
        scheme: scheme,
        host: host,
        port: port,
        path: path
    }, expectEventTimeout)

    return BaseAPI.apiCall({
        method: 'POST',
        path: '/devices',
        data: params,
        expectedHandle: handle,
        timeout: APIConstants.LONG_SERVER_TIMEOUT
    })
}

/**
 * PATCH /devices/{name} API function call.
 * @alias qtoggle.api.masterslave.patchSlaveDevice
 * @param {String} name the device name
 * @param {Boolean} enabled whether the device is enabled or disabled
 * @param {?Number} pollInterval polling interval, in seconds
 * @param {Boolean} listenEnabled whether to enable listening or not
 * @param {Number} [expectEventTimeout] optional timeout within which a corresponding event will be expected,
 * @returns {Promise}
 */
export function patchSlaveDevice(name, enabled, pollInterval, listenEnabled, expectEventTimeout = null) {
    let params = {
        enabled: enabled,
        poll_interval: pollInterval,
        listen_enabled: listenEnabled
    }

    let handle = NotificationsAPI.expectEvent('slave-device-update', {
        name: name
    }, expectEventTimeout)

    return BaseAPI.apiCall({
        method: 'PATCH',
        path: `/devices/${name}`,
        data: params,
        expectedHandle: handle,
        timeout: APIConstants.LONG_SERVER_TIMEOUT
    })
}

/**
 * DELETE /devices/{name} API function call.
 * @alias qtoggle.api.masterslave.deleteSlaveDevice
 * @param {String} name the device name
 * @param {Number} [expectEventTimeout] optional timeout within which a corresponding event will be expected,
 * @returns {Promise}
 */
export function deleteSlaveDevice(name, expectEventTimeout = null) {
    let handle = NotificationsAPI.expectEvent('slave-device-remove', {
        name: name
    }, expectEventTimeout)

    return BaseAPI.apiCall({method: 'DELETE', path: `/devices/${name}`, expectedHandle: handle})
}

/**
 * GET /discovered API function call.
 * @alias qtoggle.api.masterslave.getDiscovered
 * @param {Number} [timeout] optional discover timeout
 * @returns {Promise}
 */
export function getDiscovered(timeout = null) {
    let query = {}
    if (timeout) {
        query['timeout'] = timeout
    }

    return BaseAPI.apiCall({method: 'GET', path: '/discovered', query, timeout: timeout * 1.5})
}

/**
 * DELETE /discovered API function call.
 * @alias qtoggle.api.masterslave.deleteDiscovered
 * @returns {Promise}
 */
export function deleteDiscovered() {
    return BaseAPI.apiCall({method: 'DELETE', path: '/discovered'})
}

/**
 * PATCH /discovered/{name} API function call.
 * @alias qtoggle.api.masterslave.patchDiscoveredDevice
 * @param {String} name the device name
 * @param {Object} attrs the device attributes to set
 * @returns {Promise}
 */
export function patchDiscoveredDevice(name, attrs) {
    return BaseAPI.apiCall({
        method: 'PATCH',
        path: `/discovered/${name}`,
        data: {attrs},
        timeout: APIConstants.LONG_SERVER_TIMEOUT
    })
}
