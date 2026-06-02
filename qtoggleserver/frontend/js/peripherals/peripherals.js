/**
 * @namespace qtoggle.peripherals
 */

import Logger from '$qui/lib/logger.module.js'

import StockIcon  from '$qui/icons/stock-icon.js'
import * as Theme from '$qui/theme.js'


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


/**
 * @alias qtoggle.peripherals.makePeripheralIcon
 * @param {Object} peripheral
 * @returns {qui.icons.Icon}
 */
export function makePeripheralIcon(peripheral) {
    let decoration = null
    if (peripheral.online) {
        decoration = Theme.getVar('green-color')
    }
    else {
        decoration = Theme.getVar('disabled-color')
    }

    return PERIPHERAL_ICON.alter({decoration: decoration})
}
