/**
 * @namespace qtoggle.peripherals
 */

import Logger from '$qui/lib/logger.module.js'

import StockIcon  from '$qui/icons/stock-icon.js'


/**
 * @alias qtoggle.ports.PORT_ICON
 * @type {qui.icons.Icon}
 */
export const PERIPHERAL_ICON = new StockIcon({name: 'peripheral', stockName: 'qtoggle'})

/**
 * @alias qtoggle.peripherals.logger
 * @type {Logger}
 */
export const logger = Logger.get('qtoggle.peripherals')
