/**
 * @namespace qtoggle.api.auth
 */

import Logger from '$qui/lib/logger.module.js'

import * as Crypto      from '$qui/utils/crypto.js'
import {asap}           from '$qui/utils/misc.js'
import * as ObjectUtils from '$qui/utils/object.js'

import * as BaseAPI from './base.js'


const logger = Logger.get('qtoggle.api.auth')

/**
 * @alias qtoggle.api.auth.ACCESS_LEVEL_ADMIN
 * @type {Number}
 */
export const ACCESS_LEVEL_ADMIN = 30

/**
 * @alias qtoggle.api.auth.ACCESS_LEVEL_NORMAL
 * @type {Number}
 */
export const ACCESS_LEVEL_NORMAL = 20

/**
 * @alias qtoggle.api.auth.ACCESS_LEVEL_VIEWONLY
 * @type {Number}
 */
export const ACCESS_LEVEL_VIEWONLY = 10

/**
 * @alias qtoggle.api.auth.ACCESS_LEVEL_NONE
 * @type {Number}
 */
export const ACCESS_LEVEL_NONE = 0

/**
 * @alias qtoggle.api.auth.ACCESS_LEVEL_MAPPING
 * @type {Object}
 */
export const ACCESS_LEVEL_MAPPING = {
    admin: ACCESS_LEVEL_ADMIN,
    normal: ACCESS_LEVEL_NORMAL,
    viewonly: ACCESS_LEVEL_VIEWONLY,
    none: ACCESS_LEVEL_NONE,
    unknown: null
}

/* Reverse mapping */
ObjectUtils.forEach(ACCESS_LEVEL_MAPPING, function (k, v) {
    ACCESS_LEVEL_MAPPING[v] = k
})

/**
 * Access level change callback.
 * @callback qtoggle.api.AccessLevelChangeCallback
 * @param {Number} oldLevel the old access level
 * @param {Number} newLevel the new access level
 */

let currentUsername = null
let currentPasswordHash = null
let currentAccessLevel = null
let accessLevelChangeListeners = []


/**
 * GET /access API function call.
 * @alias qtoggle.api.auth.getAccess
 * @returns {Promise}
 */
export function getAccess() {
    let promise = BaseAPI.apiCall({method: 'GET', path: '/access'})

    return promise.then(function (a) {
        let newAccessLevel = ACCESS_LEVEL_MAPPING[a.level] || ACCESS_LEVEL_NONE

        if (newAccessLevel !== currentAccessLevel) {
            /* Access level changed, notify listeners */

            logger.debug('access level changed from ' +
                         `${ACCESS_LEVEL_MAPPING[currentAccessLevel]} to ${ACCESS_LEVEL_MAPPING[newAccessLevel]}`)

            accessLevelChangeListeners.forEach(function (l) {
                let args = [currentAccessLevel, newAccessLevel].concat(l.args || [])

                asap(function () {
                    l.callback.apply(l.thisArg, args)
                })
            })
        }

        currentAccessLevel = newAccessLevel

        return currentAccessLevel
    })
}

/**
 * Immediately return the current access level.
 * @alias qtoggle.api.auth.getCurrentAccessLevel
 * @returns {?Number} the current access level
 */
export function getCurrentAccessLevel() {
    return currentAccessLevel
}

/**
 * Add a listener to be called whenever the access level changes.
 * @alias qtoggle.api.auth.addAccessLevelChangeListener
 * @param {qtoggle.api.auth.AccessLevelChangeCallback} callback
 * @param {*} [thisArg] the callback will be called on this object
 */
export function addAccessLevelChangeListener(callback, thisArg) {
    accessLevelChangeListeners.push({callback: callback, thisArg: thisArg, args: arguments})
}

/**
 * Remove a previously registered access level change listener.
 * @alias qtoggle.api.auth.removeAccessLevelChangeListener
 * @param {qtoggle.api.AccessLevelChangeCallback} callback
 */
export function removeAccessLevelChangeListener(callback) {
    let index = accessLevelChangeListeners.findIndex(function (l) {
        return l.callback === callback
    })

    if (index >= 0) {
        accessLevelChangeListeners.splice(index, 1)
    }
}

/**
 * Set the API username.
 * @alias qtoggle.api.auth.setUsername
 * @param {String} username the username
 */
export function setUsername(username) {
    currentUsername = username
}

/**
 * Retrieve current API username.
 * @alias qtoggle.api.auth.getUsername
 * @returns {String} the current username
 */
export function getUsername() {
    return currentUsername
}

/**
 * Set the API password.
 * @alias qtoggle.api.auth.setPassword
 * @param {String} password the password
 */
export function setPassword(password) {
    currentPasswordHash = new Crypto.SHA256(password).toString()
}

/**
 * Directly set the API password hash.
 * @alias qtoggle.api.auth.setPasswordHash
 * @param {String} hash the password hash
 */
export function setPasswordHash(hash) {
    currentPasswordHash = hash
}

/**
 * Retrieve current API password hash.
 * @alias qtoggle.api.auth.getPasswordHash
 * @returns {String} the current password hash
 */
export function getPasswordHash() {
    return currentPasswordHash
}

/**
 * Tell if a given access level is granted.
 * @alias qtoggle.api.auth.hasAccess
 * @param {Number} level the desired access level
 * @returns {Boolean}
 */
export function hasAccess(level) {
    return currentAccessLevel >= level
}
