/**
 * @namespace qtoggle.settings.clientsettings
 */

import Logger from '$qui/lib/logger.module.js'

import * as Theme from '$qui/theme.js'


const STORAGE_KEY_PREFIX = 'client-settings'


/**
 * @alias qtoggle.settings.logger
 * @type {Logger}
 */
export const logger = Logger.get('qtoggle.settings.clientsettings')


function saveSetting(name, value) {
    window.localStorage.setItem(`${STORAGE_KEY_PREFIX}.${name}`, JSON.stringify(value))
}

function loadSetting(name, def = null) {
    let value = window.localStorage.getItem(`${STORAGE_KEY_PREFIX}.${name}`)
    if (value == null) {
        return def
    }

    return JSON.parse(value)
}


/**
 * @alias qtoggle.settings.clientsettings.setEffectsDisabled
 * @param {Boolean} disabled
 */
export function setEffectsDisabled(disabled) {
    logger.debug(`${disabled ? 'disabling' : 'enabling'} effects`)

    if (disabled) {
        Theme.disableEffects()
    }
    else {
        Theme.enableEffects()
    }

    saveSetting('effects-disabled', disabled)
}

/**
 * @alias qtoggle.settings.clientsettings.isEffectsDisabled
 * @returns {Boolean}
 */
export function isEffectsDisabled() {
    return loadSetting('effects-disabled', false)
}

/**
 * @alias qtoggle.settings.clientsettings.loadAndApply
 */
export function loadAndApply() {
    logger.debug('loading and applying settings')
    setEffectsDisabled(isEffectsDisabled())
}
