/**
 * @namespace qtoggle.api
 */

import * as BaseAPI          from './base.js'
import * as NotificationsAPI from './notifications.js'


/**
 * Initialize the API subsystem.
 * @alias qtoggle.api.init
 */
export function init() {
    NotificationsAPI.init()
    BaseAPI.init()
}
