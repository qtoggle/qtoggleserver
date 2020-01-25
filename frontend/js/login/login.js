/**
 * @namespace qtoggle.login
 */

import Logger from '$qui/lib/logger.module.js'

import StockIcon from '$qui/icons/stock-icon.js'


/**
 * @alias qtoggle.login.KEY_ICON
 * @type {qui.icons.Icon}
 */
export const KEY_ICON = new StockIcon({name: 'key'})

/**
 * @alias qtoggle.login.logger
 * @type {Logger}
 */
export const logger = Logger.get('qtoggle.login')
