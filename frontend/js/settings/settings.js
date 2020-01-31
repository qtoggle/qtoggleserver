/**
 * @namespace qtoggle.settings
 */

import Logger from '$qui/lib/logger.module.js'

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


let recentSettingsUpdateTimer = null


/**
 * @alias qtoggle.settings.setRecentSettingsUpdate
 */
export function setRecentSettingsUpdate() {
    if (recentSettingsUpdateTimer) {
        clearTimeout(recentSettingsUpdateTimer)
    }

    logger.debug('recent settings update timer started')

    recentSettingsUpdateTimer = setTimeout(function () {
        recentSettingsUpdateTimer = null
        logger.debug('recent settings update timer expired')
    }, RECENT_SETTINGS_UPDATE_TIMEOUT)
}

/**
 * @alias qtoggle.settings.setRecentSettingsUpdate
 * @returns {Boolean}
 */
export function isRecentSettingsUpdate() {
    return !!recentSettingsUpdateTimer
}
