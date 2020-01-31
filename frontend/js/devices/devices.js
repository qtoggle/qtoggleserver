/**
 * @namespace qtoggle.devices
 */

import Logger from '$qui/lib/logger.module.js'

import {gettext}        from '$qui/base/i18n.js'
import StockIcon        from '$qui/icons/stock-icon.js'
import * as Theme       from '$qui/theme.js'
import * as StringUtils from '$qui/utils/string.js'


const RECENT_DEVICE_UPDATE_TIMEOUT = 10000 /* milliseconds */

/**
 * @alias qtoggle.devices.DEVICE_ICON
 * @type {qui.icons.Icon}
 */
export const DEVICE_ICON = new StockIcon({name: 'device', stockName: 'qtoggle'})

/**
 * @alias qtoggle.devices.POLL_CHOICES
 * @type {{label: string, value: number}[]}
 */
export const POLL_CHOICES = [
    {label: `(${gettext('disabled')})`, value: 0},
    {label: gettext('1 second'), value: 1},
    {label: StringUtils.formatPercent(gettext('%(count)d seconds'), {count: 5}), value: 5},
    {label: StringUtils.formatPercent(gettext('%(count)d seconds'), {count: 10}), value: 10},
    {label: StringUtils.formatPercent(gettext('%(count)d seconds'), {count: 30}), value: 30},
    {label: gettext('1 minute'), value: 60},
    {label: StringUtils.formatPercent(gettext('%(count)d minutes'), {count: 5}), value: 300},
    {label: StringUtils.formatPercent(gettext('%(count)d minutes'), {count: 10}), value: 600},
    {label: StringUtils.formatPercent(gettext('%(count)d minutes'), {count: 15}), value: 900},
    {label: StringUtils.formatPercent(gettext('%(count)d minutes'), {count: 30}), value: 1800},
    {label: gettext('1 hour'), value: 3600},
    {label: StringUtils.formatPercent(gettext('%(count)d hours'), {count: 4}), value: 14400},
    {label: StringUtils.formatPercent(gettext('%(count)d hours'), {count: 8}), value: 28800},
    {label: StringUtils.formatPercent(gettext('%(count)d hours'), {count: 12}), value: 43200},
    {label: StringUtils.formatPercent(gettext('1 day'), {count: 24}), value: 86400}
]

/**
 * @alias qtoggle.devices.logger
 * @type {Logger}
 */
export const logger = Logger.get('qtoggle.devices')

let currentDeviceName = null
let renamedDeviceName = null
let recentDeviceUpdateTimer = null


/**
 * @alias qtoggle.devices.makeDeviceIcon
 * @param {Object} device
 * @returns {qui.icons.Icon}
 */
export function makeDeviceIcon(device) {
    let decoration = null
    if (device.online) {
        decoration = Theme.getVar('green-color')
    }
    else if (device.enabled) {
        // TODO replace with device.isPermanentlyOffline
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
 * @alias qtoggle.devices.getCurrentDeviceName
 * @returns {String}
 */
export function getCurrentDeviceName() {
    return currentDeviceName
}

/**
 * @alias qtoggle.devices.setCurrentDeviceName
 * @param {String} name
 */
export function setCurrentDeviceName(name) {
    currentDeviceName = name
    logger.debug(`current device name is ${currentDeviceName}`)
}

/**
 * @alias qtoggle.devices.getRenamedDeviceName
 * @returns {String}
 */
export function getRenamedDeviceName() {
    return renamedDeviceName
}

/**
 * @alias qtoggle.devices.setRenamedDeviceName
 * @param {String} name
 */
export function setRenamedDeviceName(name) {
    renamedDeviceName = name
    if (renamedDeviceName) {
        logger.debug(`current device renamed to ${renamedDeviceName}`)
    }
}

/**
 * @alias qtoggle.devices.setRecentDeviceUpdate
 */
export function setRecentDeviceUpdate() {
    if (recentDeviceUpdateTimer) {
        clearTimeout(recentDeviceUpdateTimer)
    }

    logger.debug('recent device update timer started')

    recentDeviceUpdateTimer = setTimeout(function () {
        recentDeviceUpdateTimer = null
        logger.debug('recent device update timer expired')
    }, RECENT_DEVICE_UPDATE_TIMEOUT)
}

/**
 * @alias qtoggle.devices.setRecentDeviceUpdate
 * @returns {Boolean}
 */
export function isRecentDeviceUpdate() {
    return !!recentDeviceUpdateTimer
}
