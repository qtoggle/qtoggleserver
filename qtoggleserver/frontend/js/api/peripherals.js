/**
 * @namespace qtoggle.api.peripherals
 */

import * as BaseAPI from './base.js'


/**
 * GET /peripherals API function call.
 * @alias qtoggle.api.peripherals.getPeripherals
 * @returns {Promise}
 */
export function getPeripherals() {
    return BaseAPI.apiCall({method: 'GET', path: '/peripherals'})
}

/**
 * POST /peripherals API function call.
 * @alias qtoggle.api.peripherals.postPeripherals
 * @param {String} driver the driver to use
 * @param {Object} params peripheral parameters
 * @param {String} [name] an optional peripheral name
 * @returns {Promise}
 */
export function postPeripherals(driver, params, name = null) {
    let data = {driver, name, params}

    return BaseAPI.apiCall({method: 'POST', path: '/peripherals', data: data})
}

/**
 * PUT /peripherals API function call.
 * @alias qtoggle.api.peripherals.putPeripherals
 * @param {Object} peripherals the new peripherals
 * @returns {Promise}
 */
export function putPeripherals(peripherals) {
    return BaseAPI.apiCall({method: 'PUT', path: '/peripherals', data: peripherals})
}

/**
 * PATCH /peripherals/{id} API function call.
 * @alias qtoggle.api.peripherals.patchPeripheral
 * @param {String} id the peripheral identifier
 * @param {Object} data the new peripheral configuration
 * @returns {Promise}
 */
export function patchPeripheral(id, data) {
    return BaseAPI.apiCall({method: 'PATCH', path: `/peripherals/${id}`, data: data})
}

/**
 * DELETE /peripherals/{id} API function call.
 * @alias qtoggle.api.peripherals.deletePeripherals
 * @param {String} id the peripheral identifier
 * @returns {Promise}
 */
export function deletePeripheral(id) {
    return BaseAPI.apiCall({method: 'DELETE', path: `/peripherals/${id}`})
}
