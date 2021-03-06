/**
 * @namespace qtoggle.api.devices
 */

import Logger from '$qui/lib/logger.module.js'

import * as BaseAPI          from './base.js'
import * as APIConstants     from './constants.js'
import * as NotificationsAPI from './notifications.js'


const logger = Logger.get('qtoggle.api.devices')


/**
 * @alias qtoggle.api.FIRMWARE_STATUS_IDLE
 * @type {String}
 */
export const FIRMWARE_STATUS_IDLE = 'idle'

/**
 * @alias qtoggle.api.FIRMWARE_STATUS_IDLE
 * @type {String}
 */
export const FIRMWARE_STATUS_CHECKING = 'checking'

/**
 * @alias qtoggle.api.FIRMWARE_STATUS_DOWNLOADING
 * @type {String}
 */
export const FIRMWARE_STATUS_DOWNLOADING = 'downloading'

/**
 * @alias qtoggle.api.FIRMWARE_STATUS_EXTRACTING
 * @type {String}
 */
export const FIRMWARE_STATUS_EXTRACTING = 'extracting'

/**
 * @alias qtoggle.api.FIRMWARE_STATUS_VALIDATING
 * @type {String}
 */
export const FIRMWARE_STATUS_VALIDATING = 'validating'

/**
 * @alias qtoggle.api.FIRMWARE_STATUS_FLASHING
 * @type {String}
 */
export const FIRMWARE_STATUS_FLASHING = 'flashing'

/**
 * @alias qtoggle.api.FIRMWARE_STATUS_RESTARTING
 * @type {String}
 */
export const FIRMWARE_STATUS_RESTARTING = 'restarting'

/**
 * @alias qtoggle.api.FIRMWARE_STATUS_ERROR
 * @type {String}
 */
export const FIRMWARE_STATUS_ERROR = 'error'


let firmwareUpdateInProgress = false


/**
 * GET /device API function call.
 * @alias qtoggle.api.devices.getDevice
 * @returns {Promise}
 */
export function getDevice() {
    return BaseAPI.apiCall({method: 'GET', path: '/device'})
}

/**
 * PATCH /device API function call.
 * @alias qtoggle.api.devices.patchDevice
 * @param {Object} attrs the device attributes to set
 * @param {Number} [expectEventTimeout] optional timeout within which a corresponding event will be expected,
 * @returns {Promise}
 */
export function patchDevice(attrs, expectEventTimeout = null) {
    let handle
    let slaveName = BaseAPI.getSlaveName()
    if (slaveName) {
        /* When renaming a slave, the slave-device-update will not trigger,
         * because the master will actually remove and re-add the slave */
        if (!('name' in attrs)) {
            handle = NotificationsAPI.expectEvent('slave-device-update', {
                name: slaveName
            }, expectEventTimeout)
        }
    }
    else {
        handle = NotificationsAPI.expectEvent('device-update', /* params = */ null, expectEventTimeout)
    }

    return BaseAPI.apiCall({
        method: 'PATCH', path: '/device', data: attrs,
        expectedHandle: handle, timeout: APIConstants.LONG_SERVER_TIMEOUT
    })
}

/**
 * POST /reset API function call.
 * @alias qtoggle.api.devices.postReset
 * @param {Boolean} [factory] set to `true` to reset to factory defaults
 * @returns {Promise}
 */
export function postReset(factory) {
    let data = {}
    if (factory) {
        data.factory = true
    }
    return BaseAPI.apiCall({method: 'POST', path: '/reset', data: data})
}

/**
 * GET /firmware API function call.
 * @alias qtoggle.api.devices.getFirmware
 * @param {Boolean} [override] set to `true` to forward request to offline and disabled slaves (defaults to `false`)
 * @returns {Promise}
 */
export function getFirmware(override = false) {
    let query = {}
    if (override) {
        query.override_offline = true
        query.override_disabled = true
    }

    return BaseAPI.apiCall({
        method: 'GET',
        path: '/firmware',
        query: query,
        handleErrors: !override,
        timeout: APIConstants.LONG_SERVER_TIMEOUT
    }).then(function (data) {

        if ((data.status === FIRMWARE_STATUS_IDLE || data.status === FIRMWARE_STATUS_ERROR) &&
            firmwareUpdateInProgress) {

            firmwareUpdateInProgress = false
            logger.debug('firmware update process ended')
        }

        return data

    })
}

/**
 * PATCH /firmware API function call.
 * @alias qtoggle.api.devices.patchFirmware
 * @param {?String} version the version to update the device to
 * @param {?String} url the URL of the new firmware
 * @param {Boolean} [override] set to `true` to forward request to offline and disabled slaves
 * @returns {Promise}
 */
export function patchFirmware(version, url, override = false) {
    let query = {}
    if (override) {
        query.override_offline = true
        query.override_disabled = true
    }

    let params = {}
    if (version) {
        params.version = version
    }
    if (url) {
        params.url = url
    }

    let forSlave = (BaseAPI.getSlaveName() != null)

    return BaseAPI.apiCall({
        method: 'PATCH',
        path: '/firmware',
        query: query,
        data: params,
        timeout: APIConstants.LONG_SERVER_TIMEOUT
    }).then(function (data) {

        if (!forSlave) {
            NotificationsAPI.setIgnoreListenErrors(true)
            firmwareUpdateInProgress = true
            logger.debug('firmware update process started')
        }

        return data

    })
}

/**
 * POST /introspect API function call.
 * @alias qtoggle.api.devices.postIntrospect
 * @param {String|String[]} imports a list of imports
 * @param {String} code the code to execute
 * @param {Boolean} [printResponse]
 * @returns {Promise}
 */
export function postIntrospect(imports, code, printResponse = true) {
    if (typeof imports === 'string') {
        imports = [imports]
    }

    return BaseAPI.apiCall({
        method: 'POST', path: '/introspect', data: {code, imports},
        timeout: APIConstants.LONG_SERVER_TIMEOUT
    }).then(function (response) {
        if (printResponse) {
            if (response.exception) {
                console.error(
                    '---- introspect exception ----\n' +
                    response.exception +
                    '\n------------------------------'
                )
            }
            else {
                console.info(
                    '---- introspect result ----\n' +
                    response.result +
                    '\n---------------------------'
                )
            }
        }
    })
}
