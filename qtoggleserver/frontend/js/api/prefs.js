/**
 * @namespace qtoggle.api.prefs
 */

import * as BaseAPI from './base.js'


/**
 * GET /prefs API function call.
 * @alias qtoggle.api.prefs.getPrefs
 * @returns {Promise}
 */
export function getPrefs() {
    return BaseAPI.apiCall({method: 'GET', path: '/frontend/prefs'})
}

/**
 * PUT /prefs API function call.
 * @alias qtoggle.api.prefs.putPrefs
 * @param {Object} prefs the new prefs object
 * @returns {Promise}
 */
export function putPrefs(prefs) {
    return BaseAPI.apiCall({method: 'PUT', path: '/frontend/prefs', data: prefs})
}
