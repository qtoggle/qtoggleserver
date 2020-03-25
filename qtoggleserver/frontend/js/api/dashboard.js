/**
 * @namespace qtoggle.api.dashboard
 */

import * as BaseAPI from './base.js'


/**
 * GET /dashboard/panels API function call.
 * @alias qtoggle.api.dashboard.getDashboardPanels
 * @returns {Promise}
 */
export function getDashboardPanels() {
    return BaseAPI.apiCall({method: 'GET', path: '/frontend/dashboard/panels'})
}

/**
 * PUT /dashboard/panels API function call.
 * @alias qtoggle.api.dashboard.putDashboardPanels
 * @param {Object} panels the new panels
 * @returns {Promise}
 */
export function putDashboardPanels(panels) {
    return BaseAPI.apiCall({method: 'PUT', path: '/frontend/dashboard/panels', data: panels})
}
