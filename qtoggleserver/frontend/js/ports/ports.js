/**
 * @namespace qtoggle.ports
 */

import Logger from '$qui/lib/logger.module.js'

import Timer      from '$qui/base/timer.js'
import StockIcon  from '$qui/icons/stock-icon.js'
import * as Theme from '$qui/theme.js'

import * as Cache from '$app/cache.js'


/**
 * @alias qtoggle.ports.PORT_ICON
 * @type {qui.icons.Icon}
 */
export const PORT_ICON = new StockIcon({name: 'port', stockName: 'qtoggle'})

/**
 * @alias qtoggle.ports.PORT_WRITABLE_ICON
 * @type {qui.icons.Icon}
 */
export const PORT_WRITABLE_ICON = new StockIcon({name: 'port-writable', stockName: 'qtoggle'})

/**
 * @alias qtoggle.ports.DEVICE_ICON
 * @type {qui.icons.Icon}
 */
export const DEVICE_ICON = new StockIcon({name: 'device', stockName: 'qtoggle'})

/**
 * @alias qtoggle.ports.logger
 * @type {Logger}
 */
export const logger = Logger.get('qtoggle.ports')

let masterFakeDevice = null


/**
 * @alias qtoggle.ports.recentPortUpdateTimer
 * @type {qui.base.Timer}
 */
export const recentPortUpdateTimer = new Timer(
    /* defaultTimeout = */ 10000 /* milliseconds */,
    /* onTimeout = */ function () {
        logger.debug('recent port update timer expired')
    }
)


/**
 * @alias qtoggle.ports.makeDeviceIcon
 * @param {Object} device
 * @returns {qui.icons.Icon}
 */
export function makeDeviceIcon(device) {
    let decoration = null
    if (Cache.isMainDevice(device.name)) { /* Master */
        decoration = Theme.getVar('interactive-color')
    }
    else if (device.online) {
        decoration = Theme.getVar('green-color')
    }
    else if (device.enabled) {
        // TODO use isPermanentlyOffline
        if (!device.listen_enabled && !device.poll_interval) { /* Permanently offline */
            decoration = Theme.getVar('orange-color')
        }
        else {
            decoration = Theme.getVar('disabled-color')
        }
    }

    return DEVICE_ICON.alter({decoration: decoration})
}

/**
 * @alias qtoggle.ports.makePortIcon
 * @param {Object} port
 * @returns {qui.icons.Icon}
 */
export function makePortIcon(port) {
    let device = Cache.findPortSlaveDevice(port.id)

    let decoration = null
    if (port.enabled) {
        if (port.online !== false /* null or undefined also mean online */) {
            decoration = Theme.getVar('green-color')
        }
        // TODO use isPermanentlyOffline
        else if (device && !device.listen_enabled && !device.poll_interval) { /* Permanently offline */
            decoration = Theme.getVar('orange-color')
        }
        else {
            decoration = Theme.getVar('disabled-color')
        }
    }

    let icon

    if (port.writable) {
        icon = PORT_WRITABLE_ICON
    }
    else {
        icon = PORT_ICON
    }

    icon = icon.alter({decoration: decoration})

    return icon
}

/**
 * @alias qtoggle.ports.getMasterFakeDevice
 * @returns {Object}
 */
export function getMasterFakeDevice() {
    if (!masterFakeDevice) {
        let mainDevice = Cache.getMainDevice()

        masterFakeDevice = {
            name: mainDevice.name,
            online: true,
            attrs: mainDevice
        }
    }

    return masterFakeDevice
}

/**
 * @alias qtoggle.ports.clearMasterFakeDevice
 */
export function clearMasterFakeDevice() {
    masterFakeDevice = null
}

/**
 * @alias qtoggle.ports.setRecentPortUpdate
 * @returns {Boolean}
 */
export function isRecentPortUpdate() {
    return !!recentPortUpdateTimer
}
