/**
 * @namespace qtoggle.settings.clientsettings
 */

import Logger from '$qui/lib/logger.module.js'

import * as Theme        from '$qui/theme.js'
import * as Cookies      from '$qui/utils/cookies.js'
import * as PromiseUtils from '$qui/utils/promise.js'
import * as Window       from '$qui/window.js'


const STORAGE_KEY_PREFIX = 'client-settings'
const THEME_COOKIE_NAME = 'qToggleServerFrontendTheme'
const DEFAULT_THEME = 'dark'

const logger = Logger.get('qtoggle.settings.clientsettings')


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
 * @alias qtoggle.settings.clientsettings.setTheme
 * @param {String} theme
 */
export function setTheme(theme) {
    logger.debug(`setting ${theme} theme`)

    Cookies.set(THEME_COOKIE_NAME, theme)

    /* Theme change needs window reload */
    PromiseUtils.later(500).then(() => Window.reload())
}

/**
 * @alias qtoggle.settings.clientsettings.getTheme
 * @returns {String}
 */
export function getTheme() {
    return Cookies.get(THEME_COOKIE_NAME, DEFAULT_THEME)
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
 * @alias qtoggle.settings.clientsettings.setMobileScreenMode
 * @param {String} mode one of `"auto"`, `"always"` and `"never"`
 */
export function setMobileScreenMode(mode) {
    logger.debug(`setting mobile screen mode to ${mode}`)

    switch (mode) {
        case 'auto':
            Window.setSmallScreenThreshold(null)
            break

        case 'always':
            Window.setSmallScreenThreshold(1e6)
            break

        case 'never':
            Window.setSmallScreenThreshold(0)
            break
    }

    saveSetting('mobile-screen-mode', mode)
}

/**
 * @alias qtoggle.settings.clientsettings.getMobileScreenMode
 * @returns {String} one of `"auto"`, `"always"` and `"never"`
 */
export function getMobileScreenMode() {
    return loadSetting('mobile-screen-mode', 'auto')
}

/**
 * @alias qtoggle.settings.clientsettings.setScalingFactor
 * @param {Number} factor
 */
export function setScalingFactor(factor) {
    Window.setScalingFactor(factor)
    saveSetting('scaling-factor', factor)
}

/**
 * @alias qtoggle.settings.clientsettings.getScalingFactor
 * @returns {Number}
 */
export function getScalingFactor() {
    return loadSetting('scaling-factor', '1')
}

/**
 * @alias qtoggle.settings.clientsettings.loadAndApply
 */
export function loadAndApply() {
    logger.debug('loading and applying settings')

    setEffectsDisabled(isEffectsDisabled())
    setMobileScreenMode(getMobileScreenMode())
    setScalingFactor(getScalingFactor())
}
