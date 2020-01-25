/**
 * @namespace qtoggle.auth
 */

import Logger from '$qui/lib/logger.module.js'

import ConditionVariable from '$qui/base/condition-variable.js'
import {gettext}         from '$qui/base/i18n.js'
import * as Toast        from '$qui/messages/toast.js'
import * as Cookies      from '$qui/utils/cookies.js'
import * as StringUtils  from '$qui/utils/string.js'

import * as API                   from '$app/api.js'
import {getGlobalProgressMessage} from '$app/common/common.js'


const AUTH_USERNAME_COOKIE = 'qToggleServerUsername'
const AUTH_PASSWORD_COOKIE = 'qToggleServerPasswordHash'

const logger = Logger.get('qtoggle.auth')

/**
 * @alias qtoggle.auth.whenInitialAccessLevelReady
 * @type {qui.base.ConditionVariable}
 */
export let whenInitialAccessLevelReady = new ConditionVariable()

/**
 * @alias qtoggle.auth.whenFinalAccessLevelReady
 * @type {qui.base.ConditionVariable}
 */
export let whenFinalAccessLevelReady = new ConditionVariable()

/**
 * Call {@link qtoggle.api.getAccess} after setting the given credentials. This will trigger the login mechanism by
 * resolving/rejecting access level promises.
 * @alias qtoggle.auth.login
 * @param {String} username
 * @param {String} password
 * @returns {Promise}
 */
export function login(username, password) {
    logger.debug(`logging in with username = "${username}"`)

    API.setUsername(username)
    API.setPassword(password)

    return API.getAccess().then(function (level) {

        if (level <= API.ACCESS_LEVEL_NONE) {
            logger.debug(`login failed for username = "${username}"`)
        }

        return level

    })
}

/**
 * Remember current credentials using cookies.
 * @alias qtoggle.auth.storeCredentials
 */
export function storeCredentials() {
    logger.debug('storing credentials')
    Cookies.set(AUTH_USERNAME_COOKIE, API.getUsername(), 3650)
    Cookies.set(AUTH_PASSWORD_COOKIE, API.getPasswordHash(), 3650)
}

/**
 * Clear any credentials stored in cookies.
 * @alias qtoggle.auth.clearCredentials
 */
export function clearCredentials() {
    logger.debug('clearing credentials')

    Cookies.clear(AUTH_USERNAME_COOKIE)
    Cookies.clear(AUTH_PASSWORD_COOKIE)
}

/**
 * Call GET /access to determine initial access level using stored credentials.
 * @private
 * @returns {Promise}
 */
function fetchInitialAccess() {
    let progressMessage = getGlobalProgressMessage().show()
    progressMessage.setMessage(gettext('Authenticating...'))

    logger.debug('fetching initial access')

    return API.getAccess().catch(function (error) {

        handleAccessLevelChange(null, API.ACCESS_LEVEL_NONE)
        Toast.error(StringUtils.formatPercent(gettext('Authentication failed: %(error)s'), {error: error}))

    }).finally(function () {
        progressMessage.hide()
    })
}

function handleAccessLevelChange(oldLevel, newLevel) {
    if (oldLevel == null && !whenInitialAccessLevelReady.isFulfilled()) {
        whenInitialAccessLevelReady.fulfill(newLevel)
    }

    if ((oldLevel == null || oldLevel === API.ACCESS_LEVEL_NONE) &&
        (newLevel > API.ACCESS_LEVEL_NONE) &&
        !whenFinalAccessLevelReady.isFulfilled()) {

        whenFinalAccessLevelReady.fulfill(newLevel)
    }
}

/**
 * Initialize the authentication subsystem.
 * @alias qtoggle.auth.init
 */
export function init() {
    API.addAccessLevelChangeListener(handleAccessLevelChange)

    /* Fetch initial access level */
    let username = Cookies.get(AUTH_USERNAME_COOKIE)
    let passwordHash = Cookies.get(AUTH_PASSWORD_COOKIE)
    if (username && passwordHash) {
        logger.debug('restoring credentials')

        API.setUsername(username)
        API.setPasswordHash(passwordHash)

        fetchInitialAccess()
    }
    else {
        logger.debug('no stored credentials')
        whenInitialAccessLevelReady.fulfill(API.ACCESS_LEVEL_NONE)
    }

    /* Handle final access level */
    whenFinalAccessLevelReady.then(function (level) {
        logger.debug(`final access level is ${API.ACCESS_LEVEL_MAPPING[level]}`)
    })
}
