/**
 * @namespace qtoggle.settings
 */

import Logger from '$qui/lib/logger.module.js'

import Timer     from '$qui/base/timer.js'
import StockIcon from '$qui/icons/stock-icon.js'


const RECENT_SETTINGS_UPDATE_TIMEOUT = 10000 /* milliseconds */

/**
 * @alias qtoggle.settings.WRENCH_ICON
 * @type {qui.icons.Icon}
 */
export const WRENCH_ICON = new StockIcon({name: 'wrench'})

/**
 * @alias qtoggle.settings.logger
 * @type {Logger}
 */
export const logger = Logger.get('qtoggle.settings')


/**
 * @alias qtoggle.settings.recentSettingsUpdateTimer
 * @type {qui.base.Timer}
 */
export const recentSettingsUpdateTimer = new Timer(
    /* defaultTimeout = */ 10000 /* milliseconds */,
    /* onTimeout = */ function () {
        logger.debug('recent settings update timer expired')
    }
)
