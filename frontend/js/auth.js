
import Logger from '$qui/lib/logger.module.js'

import ConditionVariable from '$qui/base/condition-variable.js'
import {gettext}         from '$qui/base/i18n.js'
import * as Toast        from '$qui/messages/toast.js'
import * as Cookies      from '$qui/utils/cookies.js'
import * as StringUtils  from '$qui/utils/string.js'

import * as API                     from '$app/api.js'
import {StickyModalProgressMessage} from '$app/common/common.js'


const AUTH_USERNAME_COOKIE = 'qToggleServerUsername'
const AUTH_PASSWORD_COOKIE = 'qToggleServerPasswordHash'

const logger = Logger.get('qtoggle.auth')

export let whenInitialAccessLevelReady = new ConditionVariable()
export let whenFinalAccessLevelReady = new ConditionVariable()


/**
 * Call {@link QToggle.API.getAccess} after setting the given credentials.
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
 */
export function storeCredentials() {
    logger.debug('storing credentials')
    Cookies.set(AUTH_USERNAME_COOKIE, API.getUsername(), 3650)
    Cookies.set(AUTH_PASSWORD_COOKIE, API.getPasswordHash(), 3650)
}

/**
 * Clear any credentials stored in cookies.
 */
export function clearCredentials() {
    logger.debug('clearing credentials')

    Cookies.clear(AUTH_USERNAME_COOKIE)
    Cookies.clear(AUTH_PASSWORD_COOKIE)
}

/**
 * Calls GET /access to determine initial access using stored credentials.
 * @returns {Promise}
 */
function fetchInitialAccess() {
    let progressMessage = StickyModalProgressMessage.show()
    progressMessage.setMessage(gettext('Authenticating...'))

    logger.debug('fetching initial access')

    return API.getAccess().catch(function (error) {

        onAccessLevelChange(null, API.ACCESS_LEVEL_NONE)
        Toast.error(StringUtils.formatPercent(gettext('Authentication failed: %(error)s'), {error: error}))

    }).finally(function () {
        progressMessage.close()
    })
}

function onAccessLevelChange(oldLevel, newLevel) {
    if (oldLevel == null && !whenInitialAccessLevelReady.isFulfilled()) {
        whenInitialAccessLevelReady.fulfill(newLevel)
    }

    if ((oldLevel == null || oldLevel === API.ACCESS_LEVEL_NONE) &&
        (newLevel > API.ACCESS_LEVEL_NONE) &&
        !whenFinalAccessLevelReady.isFulfilled()) {

        whenFinalAccessLevelReady.fulfill(newLevel)
    }
}

export function init() {
    API.addAccessLevelChangeListener(onAccessLevelChange)

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
