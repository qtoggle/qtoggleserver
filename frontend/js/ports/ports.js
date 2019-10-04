
import Logger from '$qui/lib/logger.module.js'

import StockIcon  from '$qui/icons/stock-icon.js'
import * as Theme from '$qui/theme.js'

import * as Cache from '$app/cache.js'


export const PORT_ICON = new StockIcon({name: 'port', stockName: 'qtoggle'})
export const PORT_WRITABLE_ICON = new StockIcon({name: 'port-writable', stockName: 'qtoggle'})
export const DEVICE_ICON = new StockIcon({name: 'device', stockName: 'qtoggle'})

export const logger = Logger.get('qtoggle.ports')

let masterFakeDevice = null


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

export function clearMasterFakeDevice() {
    masterFakeDevice = null
}
